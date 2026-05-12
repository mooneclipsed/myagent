"""Application-level runtime lifecycle orchestration."""

from __future__ import annotations

import asyncio

from ..adapters.agentscope.runtime import (
    AgentScopeBootstrapError,
    AgentScopeRuntime,
    AgentScopeRuntimeProfile,
)
from ..config.schemas import SessionBootstrapRequest
from ..core.interfaces import RuntimeSpec
from ..sessions.backend import validate_session_id
from ..tools import ToolRegistryError


class SessionRuntimeError(RuntimeError):
    """Base error for runtime profile operations."""


class SessionRuntimeConflictError(SessionRuntimeError):
    """Raised when a runtime id is already bootstrapped in this pod."""


class SessionRuntimeNotFoundError(SessionRuntimeError):
    """Raised when the requested runtime profile does not exist."""


class SessionRuntimeValidationError(SessionRuntimeError):
    """Raised when a supplied runtime identifier is invalid."""


class SessionBootstrapError(SessionRuntimeError):
    """Raised when session bootstrap cannot complete successfully."""


_active_runtime: AgentScopeRuntimeProfile | None = None
_runtime_lock = asyncio.Lock()
_runtime_adapter = AgentScopeRuntime()


def runtime_spec_from_bootstrap_request(request: SessionBootstrapRequest) -> RuntimeSpec:
    """Convert API bootstrap DTO into the framework-neutral runtime spec."""
    return RuntimeSpec(
        runtime_id=request.runtime_id,
        agent_config=request.agent_config,
        memory_compression=request.memory_compression,
        system_prompt=request.system_prompt,
        tools=request.tools,
        skills=request.skills,
        mcp_servers=request.mcp_servers,
    )


def get_active_session_runtime() -> AgentScopeRuntimeProfile | None:
    """Return the currently active bootstrapped runtime profile if any."""
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


async def bootstrap_session_runtime(
    request: SessionBootstrapRequest,
) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Create and register the single active pod runtime profile."""
    return await initialize_runtime(runtime_spec_from_bootstrap_request(request))


async def initialize_runtime(spec: RuntimeSpec) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Create and register the single active pod runtime profile."""
    global _active_runtime

    if not validate_session_id(spec.runtime_id):
        raise SessionRuntimeValidationError("Invalid runtime_id format.")

    async with _runtime_lock:
        if _active_runtime is not None:
            raise SessionRuntimeConflictError(
                f"Active runtime '{_active_runtime.runtime_id}' already owns this pod.",
            )

        try:
            runtime = await _runtime_adapter.initialize(spec)
        except ToolRegistryError as exc:
            raise SessionRuntimeValidationError(str(exc)) from exc
        except AgentScopeBootstrapError as exc:
            raise SessionBootstrapError(str(exc)) from exc

        _active_runtime = runtime
        return _active_runtime, True


async def reload_runtime(spec: RuntimeSpec) -> tuple[AgentScopeRuntimeProfile, bool]:
    """Replace the active runtime with a newly initialized profile."""
    global _active_runtime

    if not validate_session_id(spec.runtime_id):
        raise SessionRuntimeValidationError("Invalid runtime_id format.")

    async with _runtime_lock:
        previous = _active_runtime
        try:
            runtime = await _runtime_adapter.reload(spec)
        except ToolRegistryError as exc:
            raise SessionRuntimeValidationError(str(exc)) from exc
        except AgentScopeBootstrapError as exc:
            raise SessionBootstrapError(str(exc)) from exc
        _active_runtime = runtime

    if previous is not None:
        await previous.close()

    return runtime, True


async def shutdown_session_runtime(session_id: str) -> None:
    """Close and clear the active runtime for legacy session-route callers."""
    await shutdown_runtime_profile(session_id)


async def shutdown_runtime_profile(runtime_id: str) -> None:
    """Close and clear the active runtime for the given runtime id."""
    global _active_runtime

    async with _runtime_lock:
        if _active_runtime is None or _active_runtime.runtime_id != runtime_id:
            raise SessionRuntimeNotFoundError(
                f"No active runtime found for '{runtime_id}'.",
            )
        runtime = _active_runtime
        _active_runtime = None

    await runtime.close()


async def close_all_session_runtimes() -> None:
    """Close any active runtime profile during application shutdown."""
    global _active_runtime

    async with _runtime_lock:
        runtime = _active_runtime
        _active_runtime = None

    if runtime is not None:
        await runtime.close()
