"""Session-scoped runtime registry for bootstrapped agents, skills, and MCP clients."""

from __future__ import annotations

import asyncio
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import agentscope
from opentelemetry import trace as ot_trace
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.mcp import HttpStatefulClient, StatefulClientBase, StdIOStatefulClient
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

from src.agent.session import generate_session_id, get_session_backend, validate_session_id
from src.agent.skill_runtime import (
    SkillRuntimeRegistry,
    register_configured_skills,
    register_local_runtime_tools,
)
from src.core.config import (
    HttpMCPServerConfig,
    MCPServerConfig,
    MCPServerSummary,
    SessionBootstrapRequest,
    SkillSummary,
    StdioMCPServerConfig,
    ToolSummary,
    resolve_effective_config,
)
from src.core.settings import get_settings
from src.tools import ToolRegistryError, register_configured_tools

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


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


class SessionRuntimeError(RuntimeError):
    """Base error for session runtime operations."""


class SessionRuntimeConflictError(SessionRuntimeError):
    """Raised when another active session already owns the runtime."""


class SessionRuntimeNotFoundError(SessionRuntimeError):
    """Raised when the requested session runtime does not exist."""


class SessionRuntimeValidationError(SessionRuntimeError):
    """Raised when a supplied session identifier is invalid."""


class SessionBootstrapError(SessionRuntimeError):
    """Raised when session bootstrap cannot complete successfully."""


@dataclass
class SessionRuntime:
    """In-memory runtime for the currently active bootstrapped session."""

    session_id: str
    toolkit: Toolkit
    agent: ReActAgent
    memory: InMemoryMemory
    skill_registry: SkillRuntimeRegistry = field(default_factory=SkillRuntimeRegistry)
    mcp_clients: list[StatefulClientBase] = field(default_factory=list)
    resolved_config: dict = field(default_factory=dict)
    tool_summaries: list[ToolSummary] = field(default_factory=list)
    skill_summaries: list[SkillSummary] = field(default_factory=list)
    mcp_servers: list[MCPServerSummary] = field(default_factory=list)

    async def close(self) -> None:
        """Close bootstrapped MCP clients in LIFO order."""
        for client in reversed(self.mcp_clients):
            try:
                await client.close(ignore_errors=True)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Error closing session MCP client %s: %s", client.name, exc)
        self.mcp_clients.clear()


_active_runtime: SessionRuntime | None = None
_runtime_lock = asyncio.Lock()


def build_react_agent(
    resolved_config: dict,
    memory: InMemoryMemory,
    toolkit: Toolkit,
    system_prompt: str | None = None,
) -> ReActAgent:
    """Create a ReActAgent bound to the given memory and toolkit."""
    effective_system_prompt = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    settings = get_settings()
    formatter = OpenAIChatFormatter()
    logger.info(
        "Building ReActAgent: model=%s base_url=%s system_prompt_len=%d console_output=%s formatter=%s",
        resolved_config["model_name"],
        resolved_config["base_url"],
        len(effective_system_prompt),
        settings.AGENT_CONSOLE_OUTPUT_ENABLED,
        type(formatter).__name__,
    )
    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=resolved_config["model_name"],
            api_key=resolved_config["api_key"],
            client_kwargs={"base_url": resolved_config["base_url"]},
            stream=True,
        ),
        sys_prompt=effective_system_prompt,
        formatter=formatter,
        memory=memory,
        toolkit=toolkit,
    )
    agent.set_console_output_enabled(
        enabled=settings.AGENT_CONSOLE_OUTPUT_ENABLED,
    )
    return agent


def get_active_session_runtime() -> SessionRuntime | None:
    """Return the currently active bootstrapped session runtime if any."""
    return _active_runtime


def get_session_runtime(session_id: str | None) -> SessionRuntime | None:
    """Return the active runtime if its session_id matches."""
    if session_id and _active_runtime and _active_runtime.session_id == session_id:
        return _active_runtime
    return None


async def bootstrap_session_runtime(
    request: SessionBootstrapRequest,
) -> tuple[SessionRuntime, bool]:
    """Create and register the single active session runtime."""
    global _active_runtime

    session_id = request.session_id or generate_session_id()
    if not validate_session_id(session_id):
        raise SessionRuntimeValidationError("Invalid session_id format.")

    async with _runtime_lock:
        if _active_runtime is not None:
            if _active_runtime.session_id == session_id:
                return _active_runtime, False
            raise SessionRuntimeConflictError(
                f"Active session '{_active_runtime.session_id}' already owns this pod runtime.",
            )

        resolved_config = resolve_effective_config(request.agent_config)

        studio_url = get_settings().STUDIO_URL
        if studio_url:
            tracing_url = studio_url.rstrip("/") + "/v1/traces"
            agentscope.init(
                project="agentops",
                studio_url=studio_url,
                tracing_url=tracing_url,
                run_id=session_id,
            )
            logger.info("AgentScope Studio connected: %s (run_id=%s)", studio_url, session_id)
            log_tracing_state(f"bootstrap:{session_id}")

        memory = InMemoryMemory()
        await get_session_backend().load_session_state(
            session_id=session_id,
            memory=memory,
        )
        session_toolkit = Toolkit()
        try:
            tool_summaries = register_configured_tools(session_toolkit, request.tools)
        except ToolRegistryError as exc:
            raise SessionRuntimeValidationError(str(exc)) from exc
        register_local_runtime_tools(session_toolkit)
        skill_registry = register_configured_skills(
            toolkit=session_toolkit,
            skill_configs=request.skills,
        )
        mcp_clients: list[StatefulClientBase] = []
        summaries: list[MCPServerSummary] = []
        current_summary: MCPServerSummary | None = None

        try:
            for mcp_server in request.mcp_servers:
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

            agent = build_react_agent(
                resolved_config=resolved_config,
                memory=memory,
                toolkit=session_toolkit,
                system_prompt=request.system_prompt,
            )
        except Exception as exc:
            await close_mcp_clients(mcp_clients)
            detail = format_bootstrap_error(current_summary)
            raise SessionBootstrapError(detail) from exc

        _active_runtime = SessionRuntime(
            session_id=session_id,
            toolkit=session_toolkit,
            agent=agent,
            memory=memory,
            skill_registry=skill_registry,
            mcp_clients=mcp_clients,
            resolved_config=resolved_config,
            tool_summaries=tool_summaries,
            skill_summaries=skill_registry.list_skill_summaries(),
            mcp_servers=summaries,
        )
        return _active_runtime, True


async def shutdown_session_runtime(session_id: str) -> None:
    """Close and clear the active runtime for the given session id."""
    global _active_runtime

    async with _runtime_lock:
        if _active_runtime is None or _active_runtime.session_id != session_id:
            raise SessionRuntimeNotFoundError(
                f"No active session runtime found for '{session_id}'.",
            )
        runtime = _active_runtime
        _active_runtime = None

    await runtime.close()


async def close_all_session_runtimes() -> None:
    """Close any active session runtime during application shutdown."""
    global _active_runtime

    async with _runtime_lock:
        runtime = _active_runtime
        _active_runtime = None

    if runtime is not None:
        await runtime.close()


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

    raise SessionBootstrapError("Unsupported MCP server configuration.")


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
