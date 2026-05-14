"""AgentScope tracing helpers."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import agentscope
from opentelemetry import trace as ot_trace

from ...config.settings import get_settings

logger = logging.getLogger(__name__)


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


@contextmanager
def bind_agentscope_session_context(
    session_id: str,
    project: str = "agentops",
    trace_enabled: bool | None = None,
) -> Iterator[None]:
    """Bind the current session to AgentScope's run context during one agent call."""
    run_token = agentscope._config._run_id.set(session_id)
    project_token = agentscope._config._project.set(project)
    trace_token = None
    if trace_enabled is not None:
        trace_token = agentscope._config._trace_enabled.set(trace_enabled)
    try:
        yield
    finally:
        if trace_token is not None:
            agentscope._config._trace_enabled.reset(trace_token)
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
