"""AgentScope runtime adapter and framework-specific resource lifecycle."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import agentscope
from agentscope.memory import InMemoryMemory
from agentscope.mcp import HttpStatefulClient, StatefulClientBase, StdIOStatefulClient
from agentscope.message import Msg
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import Toolkit
from opentelemetry import trace as ot_trace

from ...capabilities.schemas import (
    HttpMCPServerConfig,
    MCPServerConfig,
    MCPServerSummary,
    SkillDownloadSummary,
    SkillSummary,
    StdioMCPServerConfig,
    ToolSummary,
)
from ...config.schemas import (
    MemoryCompressionConfig,
    resolve_effective_config,
)
from ...config.settings import get_settings
from ...core.interfaces import ChatEvent, ChatMessage, ChatRequest, RuntimeSpec
from ...runtime.skill_runtime import (
    SkillRuntimeRegistry,
    register_configured_skills,
)
from ...sessions.backend import get_session_backend
from ...tools.native_tools import register_native_tools
from ...tools import ToolRegistryError, register_configured_tools
from . import agent_factory

logger = logging.getLogger(__name__)


class _AgentScopeThinkingWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.msg == "Unsupported block type %s in the message, skipped."
            and record.args == ("thinking",)
        )


def _suppress_agentscope_thinking_warnings() -> None:
    target_logger = logging.getLogger("as")
    if not any(isinstance(item, _AgentScopeThinkingWarningFilter) for item in target_logger.filters):
        target_logger.addFilter(_AgentScopeThinkingWarningFilter())


_suppress_agentscope_thinking_warnings()


@dataclass
class AgentScopeRuntimeProfile:
    """In-memory profile for one AgentScope runtime."""

    runtime_id: str
    toolkit: Toolkit
    system_prompt: str | None = None
    memory_compression: MemoryCompressionConfig | None = None
    skill_registry: SkillRuntimeRegistry = field(default_factory=SkillRuntimeRegistry)
    mcp_clients: list[StatefulClientBase] = field(default_factory=list)
    resolved_config: dict = field(default_factory=dict)
    tool_summaries: list[ToolSummary] = field(default_factory=list)
    skill_summaries: list[SkillSummary] = field(default_factory=list)
    skill_downloads: list[SkillDownloadSummary] = field(default_factory=list)
    mcp_servers: list[MCPServerSummary] = field(default_factory=list)

    async def close(self) -> None:
        """Close bootstrapped MCP clients in LIFO order."""
        await close_mcp_clients(self.mcp_clients)
        self.mcp_clients.clear()


class AgentScopeRuntime:
    """AgentRuntime implementation backed by AgentScope."""

    def __init__(self) -> None:
        self._profile: AgentScopeRuntimeProfile | None = None

    async def initialize(self, spec: RuntimeSpec) -> AgentScopeRuntimeProfile:
        resolved_config = resolve_effective_config(spec.agent_config)
        settings = get_settings()
        studio_url = settings.STUDIO_URL
        if settings.STUDIO_ENABLED and studio_url:
            tracing_url = studio_url.rstrip("/") + "/v1/traces"
            agentscope.init(
                project="agentops",
                studio_url=studio_url,
                tracing_url=tracing_url,
                run_id=spec.runtime_id,
            )
            logger.info("AgentScope Studio connected: %s (run_id=%s)", studio_url, spec.runtime_id)
            log_tracing_state(f"bootstrap:{spec.runtime_id}")

        session_toolkit = Toolkit()
        try:
            tool_summaries = register_configured_tools(session_toolkit, spec.tools)
        except ToolRegistryError:
            raise

        register_native_tools(session_toolkit)
        skill_registry = register_configured_skills(
            toolkit=session_toolkit,
            skill_configs=spec.skills,
        )
        mcp_clients: list[StatefulClientBase] = []
        summaries: list[MCPServerSummary] = []
        current_summary: MCPServerSummary | None = None

        try:
            for mcp_server in spec.mcp_servers:
                current_summary = summarize_mcp_server(mcp_server)
                client = create_mcp_client(mcp_server)
                await client.connect()
                await session_toolkit.register_mcp_client(
                    client,
                    group_name="basic",
                    namesake_strategy="raise",
                )
                mcp_clients.append(client)
                summaries.append(current_summary)
        except Exception as exc:
            await close_mcp_clients(mcp_clients)
            detail = format_bootstrap_error(current_summary)
            raise AgentScopeBootstrapError(detail) from exc

        profile = AgentScopeRuntimeProfile(
            runtime_id=spec.runtime_id,
            toolkit=session_toolkit,
            system_prompt=spec.system_prompt,
            memory_compression=spec.memory_compression,
            skill_registry=skill_registry,
            mcp_clients=mcp_clients,
            resolved_config=resolved_config,
            tool_summaries=tool_summaries,
            skill_summaries=skill_registry.list_skill_summaries(),
            mcp_servers=summaries,
        )
        _print_toolkit_loaded("Bootstrap", session_toolkit, runtime_id=spec.runtime_id)
        self._profile = profile
        return profile

    async def chat(self, request: ChatRequest):
        async for msg, last, _agent in self.stream_with_profile(
            profile=self._profile,
            request=request,
            default_toolkit=Toolkit(),
        ):
            yield agentscope_msg_to_chat_event(msg, last)

    async def reload(self, spec: RuntimeSpec) -> AgentScopeRuntimeProfile:
        return await self.initialize(spec)

    async def shutdown(self, runtime_id: str) -> None:
        _ = runtime_id
        if self._profile is not None:
            await self._profile.close()
            self._profile = None

    async def stream_with_profile(
        self,
        *,
        profile: AgentScopeRuntimeProfile | None,
        request: ChatRequest,
        default_toolkit: Toolkit,
    ):
        """Stream a chat response using a bootstrapped profile or request-scoped config."""
        if profile is not None:
            if request.agent_config:
                raise ValueError(
                    "Bootstrapped runtimes do not accept agent_config on /chat. Re-bootstrap the runtime instead.",
                )
            memory = InMemoryMemory()
            if request.session_id:
                await get_session_backend().load_session_state(
                    session_id=request.session_id,
                    memory=memory,
                )
            _print_toolkit_loaded(
                "Chat",
                profile.toolkit,
                runtime_id=profile.runtime_id,
                session_id=request.session_id,
            )
            agent = agent_factory.build_react_agent(
                resolved_config=profile.resolved_config,
                memory=memory,
                toolkit=profile.toolkit,
                system_prompt=profile.system_prompt,
                memory_compression=profile.memory_compression,
            )
            trace_label = request.session_id or request.runtime_id or "no-session"
            log_tracing_state(f"query-start:{trace_label}")
            try:
                if request.session_id:
                    with bind_agentscope_run_context(
                        request.session_id,
                        trace_enabled=bool(profile.resolved_config),
                    ):
                        async for msg, last in _stream_agent_messages(agent, request.messages):
                            yield msg, last, agent
                else:
                    async for msg, last in _stream_agent_messages(agent, request.messages):
                        yield msg, last, agent
            finally:
                _flush_tracing(trace_label)
                if request.session_id:
                    await _save_session_state(request.session_id, agent)
            return

        resolved_config = resolve_effective_config(request.agent_config)
        memory = InMemoryMemory()
        if request.session_id:
            await get_session_backend().load_session_state(
                session_id=request.session_id,
                memory=memory,
            )

        _print_toolkit_loaded(
            "Chat",
            default_toolkit,
            runtime_id=request.runtime_id,
            session_id=request.session_id,
        )
        agent = agent_factory.build_react_agent(
            resolved_config=resolved_config,
            memory=memory,
            toolkit=default_toolkit,
        )
        trace_label = request.session_id or request.runtime_id or "no-session"
        log_tracing_state(f"query-start:{trace_label}")
        try:
            async for msg, last in _stream_agent_messages(agent, request.messages):
                yield msg, last, agent
        finally:
            _flush_tracing(trace_label)
            if request.session_id:
                await _save_session_state(request.session_id, agent)


class AgentScopeBootstrapError(RuntimeError):
    """Raised when AgentScope runtime initialization fails."""


def _print_toolkit_loaded(
    phase: str,
    toolkit: Toolkit,
    *,
    runtime_id: str | None,
    session_id: str | None = None,
) -> None:
    loaded_skills = sorted(toolkit.skills.keys())
    loaded_tools = sorted(toolkit.tools.keys())
    context = f"runtime_id={runtime_id or 'none'}"
    if session_id:
        context = f"{context} session_id={session_id}"
    message = f"{phase} toolkit loaded: {context} skills={loaded_skills} tools={loaded_tools}"
    print(message)
    logger.info(message)


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


@contextmanager
def bind_agentscope_run_context(
    session_id: str,
    project: str = "agentops",
    trace_enabled: bool | None = None,
) -> Iterator[None]:
    """Bind AgentScope ContextVar-backed run metadata for a single request."""
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


def summarize_mcp_server(mcp_server: MCPServerConfig) -> MCPServerSummary:
    """Build a normalized summary for the configured MCP server."""
    if isinstance(mcp_server, StdioMCPServerConfig):
        return MCPServerSummary(name=mcp_server.name, type="stdio")
    return MCPServerSummary(
        name=mcp_server.name,
        type="http",
        transport=mcp_server.transport,
    )


def create_mcp_client(mcp_server: MCPServerConfig) -> StatefulClientBase:
    """Instantiate the appropriate stateful MCP client for the server config."""
    if isinstance(mcp_server, StdioMCPServerConfig):
        return StdIOStatefulClient(
            name=mcp_server.name,
            command=mcp_server.command,
            args=mcp_server.args,
            env=mcp_server.env,
            cwd=mcp_server.cwd,
        )

    if isinstance(mcp_server, HttpMCPServerConfig):
        return HttpStatefulClient(
            name=mcp_server.name,
            transport=mcp_server.transport,
            url=mcp_server.url,
            headers=mcp_server.headers,
            timeout=mcp_server.timeout,
            sse_read_timeout=mcp_server.sse_read_timeout,
        )

    raise AgentScopeBootstrapError("Unsupported MCP server configuration.")


def format_bootstrap_error(summary: MCPServerSummary | None) -> str:
    """Return a redacted bootstrap error message."""
    if summary is None:
        return "Failed to initialize one or more MCP servers."
    if summary.transport:
        return (
            f"Failed to initialize MCP server '{summary.name}' "
            f"({summary.type}/{summary.transport})."
        )
    return f"Failed to initialize MCP server '{summary.name}' ({summary.type})."


async def close_mcp_clients(mcp_clients: list[StatefulClientBase]) -> None:
    """Close MCP clients in reverse order, ignoring cleanup errors."""
    for client in reversed(mcp_clients):
        try:
            await client.close(ignore_errors=True)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Error closing bootstrap MCP client %s: %s", client.name, exc)


def chat_messages_to_agentscope(messages: list[ChatMessage]) -> list[Msg]:
    """Convert framework-neutral messages into AgentScope messages."""
    converted = []
    for item in messages:
        name = item.name or item.role
        converted.append(Msg(item.role, item.content, name))
    return converted


def agentscope_msg_to_chat_event(msg: Msg, last: bool) -> ChatEvent:
    """Convert an AgentScope message into a framework-neutral chat event."""
    text = None
    if msg.content:
        first = msg.content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
    return ChatEvent(
        role=msg.role,
        name=msg.name,
        content=msg.content,
        last=last,
        text=text,
    )


async def _stream_agent_messages(agent, messages: list[ChatMessage]):
    msgs = chat_messages_to_agentscope(messages)
    stream_messages = stream_printing_messages
    coroutine_task = agent(msgs)
    async for msg, last in stream_messages(
        agents=[agent],
        coroutine_task=coroutine_task,
    ):
        yield msg, last


def _flush_tracing(trace_label: str) -> None:
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


async def _save_session_state(session_id: str, agent) -> None:
    try:
        await get_session_backend().save_session_state(
            session_id=session_id,
            memory=agent.memory,
        )
    except Exception as exc:
        logger.warning(
            "Failed to save session state for %s: %s",
            session_id,
            exc,
        )
