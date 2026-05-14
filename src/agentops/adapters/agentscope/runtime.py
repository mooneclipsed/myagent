"""AgentScope runtime adapter and framework-specific resource lifecycle."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import agentscope
from agentscope.mcp import StatefulClientBase
from agentscope.message import Msg
from agentscope.pipeline import stream_printing_messages
from agentscope.tool import Toolkit

from ...capabilities.models import (
    MCPServerSummary,
    SkillDownloadSummary,
    SkillSummary,
    ToolSummary,
)
from ...config.runtime_models import (
    AgentConfig,
    AgentModelConfig,
    MemoryCompressionConfig,
    RuntimeInitializeRequest,
    resolve_agent_model_config,
)
from ...config.settings import get_settings
from ...runtime.skill_runtime import (
    SkillRuntimeRegistry,
    register_configured_skills,
)
from ...tools.native_tools import register_native_tools
from ...tools import ToolRegistryError, register_configured_tools
from . import agent_factory
from .mcp_runtime import (
    MCPClientInitializationError,
    MCPClientManager,
    close_mcp_clients,
)
from .session_memory import load_session_memory, save_session_memory
from .tracing import (
    bind_agentscope_session_context,
    flush_tracing,
    log_tracing_state,
    query_tracing_enabled,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentScopeRuntimeProfile:
    """In-memory profile for one AgentScope runtime."""

    runtime_id: str
    toolkit: Toolkit
    system_prompt: str | None = None
    memory_compression: MemoryCompressionConfig | None = None
    skill_registry: SkillRuntimeRegistry = field(default_factory=SkillRuntimeRegistry)
    mcp_clients: list[StatefulClientBase] = field(default_factory=list)
    resolved_config: AgentModelConfig | None = None
    tool_summaries: list[ToolSummary] = field(default_factory=list)
    skill_summaries: list[SkillSummary] = field(default_factory=list)
    skill_downloads: list[SkillDownloadSummary] = field(default_factory=list)
    mcp_servers: list[MCPServerSummary] = field(default_factory=list)

    async def close(self) -> None:
        """Close initialized MCP clients in LIFO order."""
        await close_mcp_clients(self.mcp_clients)
        self.mcp_clients.clear()


class AgentScopeRuntime:
    """AgentScope runtime adapter for initialization and chat streaming."""

    def __init__(self) -> None:
        self._profile: AgentScopeRuntimeProfile | None = None

    async def initialize(self, request: RuntimeInitializeRequest) -> AgentScopeRuntimeProfile:
        resolved_config = resolve_agent_model_config(request.agent_config)
        settings = get_settings()
        studio_url = settings.studio_url
        if settings.studio_enabled and studio_url:
            tracing_url = studio_url.rstrip("/") + "/v1/traces"
            agentscope.init(
                project="agentops",
                studio_url=studio_url,
                tracing_url=tracing_url,
                run_id=request.runtime_id,
            )
            logger.info("AgentScope Studio connected: %s (run_id=%s)", studio_url, request.runtime_id)
            log_tracing_state(f"initialize:{request.runtime_id}")

        session_toolkit = Toolkit()
        try:
            tool_summaries = register_configured_tools(session_toolkit, request.tools)
        except ToolRegistryError:
            raise

        register_native_tools(session_toolkit)
        skill_registry = register_configured_skills(
            toolkit=session_toolkit,
            skill_configs=request.skills,
        )
        try:
            mcp_clients, summaries = await MCPClientManager().connect_all(
                session_toolkit,
                request.mcp_servers,
            )
        except MCPClientInitializationError as exc:
            raise AgentScopeInitializationError(str(exc)) from exc

        profile = AgentScopeRuntimeProfile(
            runtime_id=request.runtime_id,
            toolkit=session_toolkit,
            system_prompt=request.system_prompt,
            memory_compression=request.memory_compression,
            skill_registry=skill_registry,
            mcp_clients=mcp_clients,
            resolved_config=resolved_config,
            tool_summaries=tool_summaries,
            skill_summaries=skill_registry.list_skill_summaries(),
            mcp_servers=summaries,
        )
        _print_toolkit_loaded("Initialize", session_toolkit, runtime_id=request.runtime_id)
        self._profile = profile
        return profile

    async def stream_chat(
        self,
        *,
        profile: AgentScopeRuntimeProfile | None,
        messages: list[Msg],
        runtime_id: str | None = None,
        session_id: str | None = None,
        agent_config: AgentConfig | None = None,
        default_toolkit: Toolkit,
    ):
        """Stream a chat response using an initialized profile or request-scoped config."""
        if profile is not None:
            async for msg, last in self._stream_profile_chat(
                profile=profile,
                messages=messages,
                runtime_id=runtime_id,
                session_id=session_id,
                agent_config=agent_config,
            ):
                yield msg, last
            return

        async for msg, last in self._stream_request_chat(
            messages=messages,
            runtime_id=runtime_id,
            session_id=session_id,
            agent_config=agent_config,
            default_toolkit=default_toolkit,
        ):
            yield msg, last

    async def _stream_profile_chat(
        self,
        *,
        profile: AgentScopeRuntimeProfile,
        messages: list[Msg],
        runtime_id: str | None,
        session_id: str | None,
        agent_config: AgentConfig | None,
    ):
        if agent_config:
            raise ValueError(
                "Initialized runtimes do not accept agent_config on /chat. Re-initialize the runtime instead.",
            )
        memory = await load_session_memory(session_id)
        _print_toolkit_loaded(
            "Chat",
            profile.toolkit,
            runtime_id=profile.runtime_id,
            session_id=session_id,
        )
        agent = agent_factory.build_react_agent(
            resolved_config=profile.resolved_config,
            memory=memory,
            toolkit=profile.toolkit,
            system_prompt=profile.system_prompt,
            memory_compression=profile.memory_compression,
        )
        trace_label = session_id or runtime_id or "no-session"
        if query_tracing_enabled():
            log_tracing_state(f"query-start:{trace_label}")
        try:
            if session_id:
                with bind_agentscope_session_context(
                    session_id,
                    trace_enabled=profile.resolved_config is not None,
                ):
                    async for msg, last in _run_agent_stream(agent, messages):
                        yield msg, last
            else:
                async for msg, last in _run_agent_stream(agent, messages):
                    yield msg, last
        finally:
            if query_tracing_enabled():
                flush_tracing(trace_label)
            await save_session_memory(session_id, agent)

    async def _stream_request_chat(
        self,
        *,
        messages: list[Msg],
        runtime_id: str | None,
        session_id: str | None,
        agent_config: AgentConfig | None,
        default_toolkit: Toolkit,
    ):
        resolved_config = resolve_agent_model_config(agent_config)
        memory = await load_session_memory(session_id)

        _print_toolkit_loaded(
            "Chat",
            default_toolkit,
            runtime_id=runtime_id,
            session_id=session_id,
        )
        agent = agent_factory.build_react_agent(
            resolved_config=resolved_config,
            memory=memory,
            toolkit=default_toolkit,
        )
        trace_label = session_id or runtime_id or "no-session"
        if query_tracing_enabled():
            log_tracing_state(f"query-start:{trace_label}")
        try:
            async for msg, last in _run_agent_stream(agent, messages):
                yield msg, last
        finally:
            if query_tracing_enabled():
                flush_tracing(trace_label)
            await save_session_memory(session_id, agent)


class AgentScopeInitializationError(RuntimeError):
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


async def _run_agent_stream(agent, messages: list[Msg]):
    coroutine_task = agent(messages)
    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=coroutine_task,
    ):
        yield msg, last
