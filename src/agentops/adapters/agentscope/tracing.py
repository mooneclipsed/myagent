"""AgentScope tracing helpers."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime
from functools import partial
from typing import Iterator

import agentscope
import requests
import shortuuid
from agentscope.agent import AgentBase, UserAgent
from opentelemetry import trace as ot_trace

from ...config.settings import get_settings

logger = logging.getLogger(__name__)
_registered_studio_runs: set[tuple[str, str]] = set()


class _AgentScopeThinkingWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.msg == "Unsupported block type %s in the message, skipped."
            and record.args == ("thinking",)
        )


def suppress_agentscope_thinking_warnings() -> None:
    """Suppress noisy AgentScope thinking block warnings."""
    target_logger = logging.getLogger("as")
    if not any(isinstance(item, _AgentScopeThinkingWarningFilter) for item in target_logger.filters):
        target_logger.addFilter(_AgentScopeThinkingWarningFilter())


def log_tracing_state(context: str) -> None:
    """Log the current OpenTelemetry provider and configured span processors."""
    try:
        provider = ot_trace.get_tracer_provider()
        active_processor = getattr(provider, "_active_span_processor", None)
        span_processors = getattr(active_processor, "_span_processors", None)
        logger.info(
            "Tracing state [%s]: provider=%s active_processor=%s processor_count=%s",
            context,
            type(provider).__name__,
            type(active_processor).__name__ if active_processor else None,
            len(span_processors) if span_processors is not None else None,
        )
        if span_processors:
            for index, processor in enumerate(span_processors):
                exporter = getattr(processor, "span_exporter", None) or getattr(processor, "_exporter", None)
                logger.info(
                    "Tracing processor [%s:%s]: processor=%s exporter=%s endpoint=%r headers=%r timeout=%r exporter_repr=%r",
                    context,
                    index,
                    type(processor).__name__,
                    type(exporter).__name__ if exporter else None,
                    getattr(exporter, "_endpoint", None) if exporter else None,
                    getattr(exporter, "_headers", None) if exporter else None,
                    getattr(exporter, "_timeout", None) if exporter else None,
                    exporter,
                )
    except Exception as exc:  # pragma: no cover - diagnostics only
        logger.warning("Failed to inspect tracing state [%s]: %s", context, exc)


def query_tracing_enabled() -> bool:
    """Return whether query tracing should emit diagnostic state."""
    return get_settings().studio_enabled


def install_studio_message_forwarding(studio_url: str) -> None:
    """Install Studio message forwarding with the current AgentScope run context."""
    AgentBase.register_class_hook(
        "pre_print",
        "as_studio_forward_message_pre_print_hook",
        partial(
            forward_message_to_studio,
            studio_url=studio_url.rstrip("/"),
        ),
    )


def forward_message_to_studio(
    agent: AgentBase,
    kwargs: dict,
    studio_url: str,
) -> None:
    """Forward an AgentScope printed message to the current Studio session run."""
    message = kwargs["msg"]
    reply_id = getattr(agent, "_reply_id", None) or shortuuid.uuid()
    reply_role = "user" if isinstance(agent, UserAgent) else "assistant"
    payload = {
        "runId": agentscope._config.run_id,
        "replyId": reply_id,
        "replyName": getattr(agent, "name", message.name),
        "replyRole": reply_role,
        "msg": message.to_dict(),
    }
    try:
        response = requests.post(
            url=f"{studio_url}/trpc/pushMessage",
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning(
            "Failed to forward Studio message run_id=%s reply_id=%s: %s",
            agentscope._config.run_id,
            reply_id,
            exc,
        )


def register_studio_run(project: str, run_id: str, name: str) -> None:
    """Register one Studio run for the current chat session if Studio is configured."""
    settings = get_settings()
    studio_url = settings.studio_url
    if not settings.studio_enabled or not studio_url:
        return

    cache_key = (project, run_id)
    if cache_key in _registered_studio_runs:
        return

    payload = {
        "id": run_id,
        "project": project,
        "name": name,
        "timestamp": _studio_timestamp(),
        "pid": os.getpid(),
        "status": "running",
        "run_dir": "",
    }
    try:
        response = requests.post(
            url=f"{studio_url.rstrip('/')}/trpc/registerRun",
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        _registered_studio_runs.add(cache_key)
    except Exception as exc:
        logger.warning(
            "Failed to register Studio run project=%s run_id=%s: %s",
            project,
            run_id,
            exc,
        )


def _studio_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


@contextmanager
def bind_agentscope_session_context(
    session_id: str,
    project: str = "agentops",
    name: str | None = None,
    trace_enabled: bool | None = None,
) -> Iterator[None]:
    """Bind the current session to AgentScope's run context during one agent call."""
    run_token = agentscope._config._run_id.set(session_id)
    project_token = agentscope._config._project.set(project)
    name_token = agentscope._config._name.set(name)
    trace_token = None
    if trace_enabled is not None:
        trace_token = agentscope._config._trace_enabled.set(trace_enabled)
    try:
        yield
    finally:
        if trace_token is not None:
            agentscope._config._trace_enabled.reset(trace_token)
        agentscope._config._name.reset(name_token)
        agentscope._config._project.reset(project_token)
        agentscope._config._run_id.reset(run_token)


def flush_tracing(trace_label: str) -> None:
    """Flush tracing providers and log final tracing state."""
    try:
        provider = ot_trace.get_tracer_provider()
        force_flush = getattr(provider, "force_flush", None)
        if callable(force_flush):
            flushed = force_flush()
            logger.info(
                "Tracing force_flush [%s]: %r",
                trace_label,
                flushed,
            )
        log_tracing_state(f"query-end:{trace_label}")
    except Exception as exc:  # pragma: no cover - diagnostics only
        logger.warning("Tracing flush failed for %s: %s", trace_label, exc)


suppress_agentscope_thinking_warnings()
