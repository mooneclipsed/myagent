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
    global _active_runtime, _active_managed_skills

    if not validate_session_id(spec.runtime_id):
        raise SessionRuntimeValidationError("Invalid runtime_id format.")

    async with _runtime_lock:
        previous_runtime = _active_runtime
        previous_managed_skills = list(_active_managed_skills.values())
        _active_runtime = None
        _active_managed_skills = {}

        if previous_runtime is not None:
            await previous_runtime.close()
        cleanup_removed_managed_skills(previous_managed_skills)

        runtime = await _initialize_runtime_locked(spec)
        _active_runtime = runtime
        return _active_runtime, True


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

    prepared_spec, download_summaries, managed_state = _prepare_runtime_spec(spec)
    try:
        _raise_for_failed_skill_downloads(download_summaries)
    except RuntimeInitializationError:
        cleanup_removed_managed_skills(list(managed_state.values()))
        raise

    try:
        runtime = await _runtime_adapter.initialize(prepared_spec)
    except ToolRegistryError as exc:
        cleanup_removed_managed_skills(list(managed_state.values()))
        raise SessionRuntimeValidationError(str(exc)) from exc
    except AgentScopeInitializationError as exc:
        cleanup_removed_managed_skills(list(managed_state.values()))
        raise RuntimeInitializationError(str(exc)) from exc
    except Exception as exc:
        cleanup_removed_managed_skills(list(managed_state.values()))
        raise RuntimeInitializationError(str(exc)) from exc

    runtime.skill_downloads = download_summaries
    _active_managed_skills = managed_state
    return runtime


def _prepare_runtime_spec(
    spec: RuntimeSpec,
) -> tuple[RuntimeSpec, list[SkillDownloadSummary], dict[ManagedSkillKey, ManagedSkillState]]:
    sync_result = prepare_remote_skills(
        requested=spec.skill_downloads,
        skills_download_url=spec.skills_download_url,
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
    )


def _raise_for_failed_skill_downloads(summaries: list[SkillDownloadSummary]) -> None:
    failed = [summary for summary in summaries if summary.status == "failed"]
    if not failed:
        return

    details = [
        f"skill_id={summary.skill_id} version_id={summary.version_id}: {summary.error or 'download failed'}"
        for summary in failed
    ]
    raise RuntimeInitializationError("Remote skill download failed: " + "; ".join(details))
