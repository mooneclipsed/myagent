"""Application-level runtime lifecycle orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..capabilities.models import (
    MCPServerConfig,
    SkillConfig,
    SkillDownloadConfig,
    SkillDownloadSummary,
    ToolConfig,
)
from ..adapters.agentscope.runtime import (
    AgentScopeInitializationError,
    AgentScopeRuntime,
    AgentScopeRuntimeProfile,
)
from ..config.runtime_models import MemoryCompressionConfig, ModelConfig, RuntimeInitializeRequest
from ..tools import ToolRegistryError
from .skill_install_service import (
    ManagedSkillKey,
    ManagedSkillState,
    cleanup_managed_skills,
    prepare_remote_skills,
)


class SessionRuntimeError(RuntimeError):
    """Base error for runtime profile operations."""


class SessionRuntimeValidationError(SessionRuntimeError):
    """Raised when a runtime request is invalid."""


class RuntimeInitializationError(SessionRuntimeError):
    """Raised when runtime initialization cannot complete successfully."""


@dataclass(frozen=True)
class PreparedRuntimeSkills:
    """Runtime skill inputs after remote skill preparation."""

    skills: list[SkillConfig]
    download_summaries: list[SkillDownloadSummary]
    managed_skills: dict[ManagedSkillKey, ManagedSkillState]


_active_runtime: AgentScopeRuntimeProfile | None = None
_active_managed_skills: dict[ManagedSkillKey, ManagedSkillState] = {}
_runtime_lock = asyncio.Lock()
_runtime_adapter = AgentScopeRuntime()


def get_active_runtime_profile() -> AgentScopeRuntimeProfile | None:
    """Return the active runtime profile for this process."""
    return _active_runtime


async def initialize_runtime(request: RuntimeInitializeRequest) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Create and publish the single active runtime profile."""

    async with _runtime_lock:
        previous_runtime, previous_managed_skills = _detach_active_runtime()

        await _cleanup_previous_runtime(previous_runtime, previous_managed_skills)

        prepared_skills = _prepare_runtime_skills(
            existing_skills=request.skills,
            requested_downloads=request.skill_downloads,
            skills_download_url=request.skills_download_url,
        )

        runtime = await _create_runtime_profile(
            requested_model_config=request.requested_model_config,
            memory_compression=request.memory_compression,
            system_prompt=request.system_prompt,
            tools=request.tools,
            mcp_servers=request.mcp_servers,
            prepared_skills=prepared_skills,
        )

        _publish_active_runtime(runtime, prepared_skills.managed_skills)
        return runtime, True


def _detach_active_runtime() -> tuple[AgentScopeRuntimeProfile | None, list[ManagedSkillState]]:
    """Remove and return the currently published runtime state."""
    global _active_runtime, _active_managed_skills

    runtime = _active_runtime
    managed_skills = list(_active_managed_skills.values())
    _active_runtime = None
    _active_managed_skills = {}
    return runtime, managed_skills


async def _cleanup_previous_runtime(
    runtime: AgentScopeRuntimeProfile | None,
    managed_skills: list[ManagedSkillState],
) -> None:
    """Close previous runtime resources and delete managed skill directories."""
    if runtime is not None:
        await runtime.close()
    cleanup_managed_skills(managed_skills)


def _publish_active_runtime(
    runtime: AgentScopeRuntimeProfile,
    managed_skills: dict[ManagedSkillKey, ManagedSkillState],
) -> None:
    """Publish the newly created runtime state."""
    global _active_runtime, _active_managed_skills

    _active_runtime = runtime
    _active_managed_skills = managed_skills


async def close_all_session_runtimes() -> None:
    """Close any active runtime profile during application shutdown."""
    async with _runtime_lock:
        runtime, managed_skills = _detach_active_runtime()

    await _cleanup_previous_runtime(runtime, managed_skills)


async def _create_runtime_profile(
    *,
    requested_model_config: ModelConfig | None,
    memory_compression: MemoryCompressionConfig | None,
    system_prompt: str | None,
    tools: list[ToolConfig],
    mcp_servers: list[MCPServerConfig],
    prepared_skills: PreparedRuntimeSkills,
) -> AgentScopeRuntimeProfile:
    try:
        _raise_for_failed_skill_downloads(prepared_skills.download_summaries)
    except RuntimeInitializationError:
        cleanup_managed_skills(list(prepared_skills.managed_skills.values()))
        raise

    runtime_request = RuntimeInitializeRequest(
        model_config=requested_model_config,
        memory_compression=memory_compression,
        system_prompt=system_prompt,
        tools=tools,
        skills=prepared_skills.skills,
        mcp_servers=mcp_servers,
    )
    try:
        runtime = await _runtime_adapter.initialize(runtime_request)
    except ToolRegistryError as exc:
        cleanup_managed_skills(list(prepared_skills.managed_skills.values()))
        raise SessionRuntimeValidationError(str(exc)) from exc
    except AgentScopeInitializationError as exc:
        cleanup_managed_skills(list(prepared_skills.managed_skills.values()))
        raise RuntimeInitializationError(str(exc)) from exc
    except Exception as exc:
        cleanup_managed_skills(list(prepared_skills.managed_skills.values()))
        raise RuntimeInitializationError(str(exc)) from exc

    runtime.skill_downloads = prepared_skills.download_summaries
    return runtime


def _prepare_runtime_skills(
    *,
    existing_skills: list[SkillConfig],
    requested_downloads: list[SkillDownloadConfig],
    skills_download_url: str | None,
) -> PreparedRuntimeSkills:
    sync_result = prepare_remote_skills(
        requested=requested_downloads,
        skills_download_url=skills_download_url,
    )
    return PreparedRuntimeSkills(
        skills=[*existing_skills, *sync_result.skills],
        download_summaries=sync_result.summaries,
        managed_skills=sync_result.managed_skills,
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
