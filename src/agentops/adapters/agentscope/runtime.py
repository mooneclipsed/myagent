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
    AgentModelConfig,
    MemoryCompressionConfig,
    ModelConfig,
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
    install_studio_message_forwarding,
    log_tracing_state,
    query_tracing_enabled,
    register_studio_run,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentScopeRuntimeProfile:
    """In-memory profile for one AgentScope runtime."""

    toolkit: Toolkit
    tenant_id: str | None = None
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

    default_project = "agentops"
    default_run_id = "agentops-runtime"

    async def initialize(self, request: RuntimeInitializeRequest) -> AgentScopeRuntimeProfile:
        resolved_config = resolve_agent_model_config(request.requested_model_config)
        project = build_trace_project(request.tenant_id)
        run_id = build_trace_run_id()
        settings = get_settings()
        studio_url = settings.studio_url
        if settings.studio_enabled and studio_url:
            tracing_url = studio_url.rstrip("/") + "/v1/traces"
            agentscope.init(
                project=project,
                tracing_url=tracing_url,
                run_id=run_id,
                name=run_id,
            )
            install_studio_message_forwarding(studio_url)
            logger.info("AgentScope Studio tracing connected: %s", studio_url)
            log_tracing_state("initialize")

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
            toolkit=session_toolkit,
            tenant_id=request.tenant_id,
            system_prompt=request.system_prompt,
            memory_compression=request.memory_compression,
            skill_registry=skill_registry,
            mcp_clients=mcp_clients,
            resolved_config=resolved_config,
            tool_summaries=tool_summaries,
            skill_summaries=skill_registry.list_skill_summaries(),
            mcp_servers=summaries,
        )
        _print_toolkit_loaded("Initialize", session_toolkit)
        return profile

    async def stream_chat(
        self,
        *,
        profile: AgentScopeRuntimeProfile | None,
        messages: list[Msg],
        session_id: str | None = None,
        model_config: ModelConfig | None = None,
    ):
        """Stream a chat response using an initialized runtime profile."""
        if profile is not None:
            async for msg, last in self._stream_profile_chat(
                profile=profile,
                messages=messages,
                session_id=session_id,
                model_config=model_config,
            ):
                yield msg, last
            return

        raise ValueError("Runtime has not been initialized. Call /runtimes/init first.")

    async def _stream_profile_chat(
        self,
        *,
        profile: AgentScopeRuntimeProfile,
        messages: list[Msg],
        session_id: str | None,
        model_config: ModelConfig | None,
    ):
        if model_config:
            raise ValueError(
                "Initialized runtimes do not accept model_config on /chat. Re-initialize the runtime instead.",
            )
        memory = await load_session_memory(session_id)
        _print_toolkit_loaded(
            "Chat",
            profile.toolkit,
            session_id=session_id,
        )
        agent = agent_factory.build_react_agent(
            resolved_config=profile.resolved_config,
            memory=memory,
            toolkit=profile.toolkit,
            system_prompt=profile.system_prompt,
            memory_compression=profile.memory_compression,
        )
        trace_project = build_trace_project(profile.tenant_id)
        trace_run_id = build_trace_session_run_id(
            session_id,
            profile.tenant_id,
        )
        trace_label = trace_run_id
        if query_tracing_enabled():
            log_tracing_state(f"query-start:{trace_label}")
        try:
            if session_id:
                register_studio_run(
                    project=trace_project,
                    run_id=trace_run_id,
                    name=session_id,
                )
                with bind_agentscope_session_context(
                    trace_run_id,
                    project=trace_project,
                    name=session_id,
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


class AgentScopeInitializationError(RuntimeError):
    """Raised when AgentScope runtime initialization fails."""


def _print_toolkit_loaded(
    phase: str,
    toolkit: Toolkit,
    *,
    session_id: str | None = None,
) -> None:
    loaded_skills = sorted(toolkit.skills.keys())
    loaded_tools = sorted(toolkit.tools.keys())
    context = f"session_id={session_id}" if session_id else "no-session"
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


def build_trace_project(tenant_id: str | None) -> str:
    """Build the AgentScope Studio project name for a tenant scope."""
    if tenant_id:
        return f"agentops-{tenant_id}"
    return AgentScopeRuntime.default_project


def build_trace_run_id() -> str:
    """Build the fallback AgentScope Studio run id before a chat session exists."""
    return AgentScopeRuntime.default_run_id


def build_trace_session_run_id(
    session_id: str | None,
    tenant_id: str | None,
) -> str:
    """Build a Studio-global run id for one chat session."""
    if not session_id:
        return build_trace_run_id()
    if tenant_id:
        return f"{tenant_id}:{session_id}"
    return session_id
