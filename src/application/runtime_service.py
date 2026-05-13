"""Application-level runtime lifecycle orchestration."""

from __future__ import annotations

import asyncio

from ..capabilities.schemas import SkillDownloadSummary
from ..adapters.agentscope.runtime import (
    AgentScopeInitializationError,
    AgentScopeRuntime,
    AgentScopeRuntimeProfile,
)
from ..config.schemas import RuntimeInitializeRequest
from ..core.interfaces import RuntimeSpec
from ..sessions.backend import validate_session_id
from ..tools import ToolRegistryError
from .skill_install_service import (
    ManagedSkillKey,
    ManagedSkillState,
    cleanup_removed_managed_skills,
    prepare_remote_skills,
)


class SessionRuntimeError(RuntimeError):
    """Base error for runtime profile operations."""


class SessionRuntimeConflictError(SessionRuntimeError):
    """Raised when a runtime id conflicts with active pod state."""


class SessionRuntimeNotFoundError(SessionRuntimeError):
    """Raised when the requested runtime profile does not exist."""


class SessionRuntimeValidationError(SessionRuntimeError):
    """Raised when a supplied runtime identifier is invalid."""


class RuntimeInitializationError(SessionRuntimeError):
    """Raised when runtime initialization cannot complete successfully."""


_active_runtime: AgentScopeRuntimeProfile | None = None
_active_managed_skills: dict[ManagedSkillKey, ManagedSkillState] = {}
_runtime_lock = asyncio.Lock()
_runtime_adapter = AgentScopeRuntime()


def runtime_spec_from_initialize_request(request: RuntimeInitializeRequest) -> RuntimeSpec:
    """Convert API initialization DTO into the framework-neutral runtime spec."""
    return RuntimeSpec(
        runtime_id=request.runtime_id,
        agent_config=request.agent_config,
        memory_compression=request.memory_compression,
        system_prompt=request.system_prompt,
        tools=request.tools,
        skills=request.skills,
        skill_downloads=request.skill_downloads,
        skills_download_url=request.skills_download_url,
        mcp_servers=request.mcp_servers,
    )


def get_active_session_runtime() -> AgentScopeRuntimeProfile | None:
    """Return the currently active runtime profile if any."""
    return _active_runtime


def get_session_runtime(session_id: str | None) -> AgentScopeRuntimeProfile | None:
    """Return no runtime for legacy session-id lookups."""
    _ = session_id
    return None


def get_runtime_profile(runtime_id: str | None) -> AgentScopeRuntimeProfile | None:
    """Return the active runtime profile if its runtime_id matches."""
    if runtime_id and _active_runtime and _active_runtime.runtime_id == runtime_id:
        return _active_runtime
    return None


async def initialize_runtime_from_request(
    request: RuntimeInitializeRequest,
) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Create and register the single active pod runtime profile."""
    return await initialize_runtime(runtime_spec_from_initialize_request(request))


async def initialize_runtime(spec: RuntimeSpec) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Create and register the single active pod runtime profile."""
    global _active_runtime

    if not validate_session_id(spec.runtime_id):
        raise SessionRuntimeValidationError("Invalid runtime_id format.")

    async with _runtime_lock:
        if _active_runtime is not None:
            return await _reload_runtime_locked(spec)

        runtime = await _initialize_runtime_locked(spec)
        _active_runtime = runtime
        return _active_runtime, True


async def reload_runtime(spec: RuntimeSpec) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Replace the active runtime with a newly initialized profile."""
    global _active_runtime

    if not validate_session_id(spec.runtime_id):
        raise SessionRuntimeValidationError("Invalid runtime_id format.")

    async with _runtime_lock:
        runtime, previous, remove_after_swap = await _reload_runtime_locked(spec, include_previous=True)

    if previous is not None:
        await previous.close()
    cleanup_removed_managed_skills(remove_after_swap)

    return runtime, True


async def shutdown_session_runtime(session_id: str) -> None:
    """Close and clear the active runtime for legacy session-route callers."""
    await shutdown_runtime_profile(session_id)


async def shutdown_runtime_profile(runtime_id: str) -> None:
    """Close and clear the active runtime for the given runtime id."""
    global _active_runtime, _active_managed_skills

    async with _runtime_lock:
        if _active_runtime is None or _active_runtime.runtime_id != runtime_id:
            raise SessionRuntimeNotFoundError(
                f"No active runtime found for '{runtime_id}'.",
            )
        runtime = _active_runtime
        managed_skills = list(_active_managed_skills.values())
        _active_runtime = None
        _active_managed_skills = {}

    await runtime.close()
    cleanup_removed_managed_skills(managed_skills)


async def close_all_session_runtimes() -> None:
    """Close any active runtime profile during application shutdown."""
    global _active_runtime, _active_managed_skills

    async with _runtime_lock:
        runtime = _active_runtime
        managed_skills = list(_active_managed_skills.values())
        _active_runtime = None
        _active_managed_skills = {}

    if runtime is not None:
        await runtime.close()
    cleanup_removed_managed_skills(managed_skills)


async def _initialize_runtime_locked(spec: RuntimeSpec) -> AgentScopeRuntimeProfile:
    global _active_managed_skills

    prepared_spec, download_summaries, managed_state, _ = _prepare_runtime_spec(
        spec,
        previous_managed_skills={},
    )
    try:
        runtime = await _runtime_adapter.initialize(prepared_spec)
    except ToolRegistryError as exc:
        raise SessionRuntimeValidationError(str(exc)) from exc
    except AgentScopeInitializationError as exc:
        raise RuntimeInitializationError(str(exc)) from exc

    runtime.skill_downloads = download_summaries
    _active_managed_skills = managed_state
    return runtime


async def _reload_runtime_locked(
    spec: RuntimeSpec,
    *,
    include_previous: bool = False,
):
    global _active_runtime, _active_managed_skills

    previous = _active_runtime
    prepared_spec, download_summaries, managed_state, remove_after_swap = _prepare_runtime_spec(
        spec,
        previous_managed_skills=_active_managed_skills,
    )
    try:
        runtime = await _runtime_adapter.reload(prepared_spec)
    except ToolRegistryError as exc:
        raise SessionRuntimeValidationError(str(exc)) from exc
    except AgentScopeInitializationError as exc:
        raise RuntimeInitializationError(str(exc)) from exc

    runtime.skill_downloads = download_summaries
    _active_runtime = runtime
    _active_managed_skills = managed_state

    if include_previous:
        return runtime, previous, remove_after_swap

    if previous is not None:
        await previous.close()
    cleanup_removed_managed_skills(remove_after_swap)
    return runtime, True


def _prepare_runtime_spec(
    spec: RuntimeSpec,
    *,
    previous_managed_skills: dict[ManagedSkillKey, ManagedSkillState],
) -> tuple[RuntimeSpec, list[SkillDownloadSummary], dict[ManagedSkillKey, ManagedSkillState], list[ManagedSkillState]]:
    sync_result = prepare_remote_skills(
        requested=spec.skill_downloads,
        skills_download_url=spec.skills_download_url,
        previous_state=previous_managed_skills,
    )
    prepared_spec = RuntimeSpec(
        runtime_id=spec.runtime_id,
        agent_config=spec.agent_config,
        memory_compression=spec.memory_compression,
        system_prompt=spec.system_prompt,
        tools=spec.tools,
        skills=[*spec.skills, *sync_result.skills],
        skill_downloads=spec.skill_downloads,
        skills_download_url=spec.skills_download_url,
        mcp_servers=spec.mcp_servers,
    )
    return (
        prepared_spec,
        sync_result.summaries,
        sync_result.state,
        sync_result.remove_after_runtime_swap,
    )
