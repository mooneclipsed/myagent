"""Framework-neutral runtime manager."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol

from agentops.api.schemas import RuntimeInitRequest
from agentops.frameworks.registry import resolve_framework
from agentops.orchestration.models import (
    AgentSpec,
    CapabilitySummary,
    RuntimeInitResult,
    RuntimeProfile,
    StorageRef,
    TraceRef,
    WorkspaceRef,
)
from agentops.orchestration.observability import hash_system_prompt
from agentops.orchestration.workspace import (
    create_runtime_workspace,
    get_workspace_root,
    promote_runtime_workspace,
    remove_runtime_workspace,
)

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class RuntimeManagerError(RuntimeError):
    """Base error for runtime manager operations."""


class RuntimeBuilder(Protocol):
    """Build framework resources for a runtime init request."""

    async def build(self, request: RuntimeInitRequest, workspace_path: Path) -> dict[str, Any]:
        """Build framework resources for a runtime."""

    async def close(self, profile: RuntimeProfile) -> None:
        """Close framework resources for a runtime profile."""


class NoopRuntimeBuilder:
    """Runtime builder used before concrete framework adapters are implemented."""

    async def build(self, request: RuntimeInitRequest, workspace_path: Path) -> dict[str, Any]:
        """Validate the build hook without creating framework resources."""
        return {}

    async def close(self, profile: RuntimeProfile) -> None:
        """Close no-op framework resources."""
        return None


class RuntimeManager:
    """Manage the single active runtime profile in this process."""

    def __init__(
        self,
        *,
        workspace_root: Path | str | None = None,
        builder: RuntimeBuilder | None = None,
    ) -> None:
        """Create a runtime manager."""
        self._workspace_root = Path(workspace_root) if workspace_root is not None else get_workspace_root()
        self._builder = builder or NoopRuntimeBuilder()
        self._lock = asyncio.Lock()
        self._active_profile: RuntimeProfile | None = None

    def get_active_profile(self) -> RuntimeProfile | None:
        """Return the current active runtime profile."""
        return self._active_profile

    async def initialize(self, request: RuntimeInitRequest) -> RuntimeInitResult:
        """Initialize a runtime and publish it only after all setup succeeds."""
        descriptor = resolve_framework(request.framework)
        staging_runtime_id = f".{request.runtime_id}.staging"

        async with self._lock:
            staging_path = create_runtime_workspace(staging_runtime_id, root=self._workspace_root)
            try:
                framework_metadata = await self._builder.build(request, staging_path)
                workspace_path = promote_runtime_workspace(
                    staging_runtime_id,
                    request.runtime_id,
                    root=self._workspace_root,
                )
            except Exception as exc:
                remove_runtime_workspace(staging_runtime_id, root=self._workspace_root)
                raise RuntimeManagerError(str(exc)) from exc

            profile = self._build_profile(request, descriptor.name, workspace_path, framework_metadata)
            previous_profile = self._active_profile
            self._active_profile = profile

        if previous_profile is not None:
            await self._builder.close(previous_profile)
        if previous_profile is not None and previous_profile.runtime_id != profile.runtime_id:
            remove_runtime_workspace(previous_profile.runtime_id, root=self._workspace_root)

        return _init_result_from_profile(profile)

    async def close_active_runtime(self) -> None:
        """Close and remove the active runtime profile."""
        async with self._lock:
            profile = self._active_profile
            self._active_profile = None

        if profile is not None:
            await self._cleanup_profile(profile)

    async def _cleanup_profile(self, profile: RuntimeProfile) -> None:
        """Close framework resources and remove workspace contents."""
        await self._builder.close(profile)
        remove_runtime_workspace(profile.runtime_id, root=self._workspace_root)

    def _build_profile(
        self,
        request: RuntimeInitRequest,
        framework: str,
        workspace_path: Path,
        framework_metadata: dict[str, Any],
    ) -> RuntimeProfile:
        """Build a public-safe runtime profile from an init request."""
        system_prompt = request.system_prompt or DEFAULT_SYSTEM_PROMPT
        model_config = request.model_config_ or {}
        agent_spec = AgentSpec(
            model_config=model_config,
            system_prompt=system_prompt,
            prompt_hash=hash_system_prompt(system_prompt),
            metadata=framework_metadata,
        )
        return RuntimeProfile(
            runtime_id=request.runtime_id,
            tenant_id=request.tenant_id,
            framework=framework,
            agent_spec=agent_spec,
            capabilities=[
                CapabilitySummary(type=capability.type, name=capability.name)
                for capability in request.capabilities
                if capability.enabled
            ],
            workspace=WorkspaceRef(
                root=str(self._workspace_root),
                runtime_path=str(workspace_path),
            ),
            storage=StorageRef(type="framework_memory"),
            trace=TraceRef(enabled=False),
            status="ready",
        )


def _init_result_from_profile(profile: RuntimeProfile) -> RuntimeInitResult:
    """Build the public init response from a runtime profile."""
    return RuntimeInitResult(
        runtime_id=profile.runtime_id,
        framework=profile.framework,
        status=profile.status,
        capabilities=profile.capabilities,
        workspace=profile.workspace,
        storage=profile.storage,
        tracing=profile.trace,
    )
