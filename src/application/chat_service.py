"""Streaming query handler for the AgentScope runtime chat endpoint."""

import asyncio
from typing import Any

from agentscope_runtime.engine import AgentApp

from ..adapters.agentscope.runtime import AgentScopeRuntime
from ..config.schemas import AgentConfig
from .runtime_service import (
    get_runtime_profile,
)
from ..sessions.backend import validate_session_id
from ..tools import toolkit


_session_locks: dict[str, asyncio.Lock] = {}
_session_locks_guard = asyncio.Lock()
_runtime_adapter = AgentScopeRuntime()


async def _get_session_lock(session_id: str) -> asyncio.Lock:
    async with _session_locks_guard:
        lock = _session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _session_locks[session_id] = lock
        return lock


def _resolve_chat_context(request: Any) -> tuple[str | None, str | None, Any, Any]:
    session_id = None
    runtime_id = None
    runtime = None

    if request and hasattr(request, "session_id") and request.session_id:
        raw_session_id = request.session_id
        if validate_session_id(raw_session_id):
            session_id = raw_session_id
        elif request and hasattr(request, "runtime_id") and request.runtime_id:
            raise ValueError("Invalid session_id format.")

    if request and hasattr(request, "runtime_id") and request.runtime_id:
        raw_runtime_id = request.runtime_id
        if not validate_session_id(raw_runtime_id):
            raise ValueError("Invalid runtime_id format.")
        runtime_id = raw_runtime_id
        runtime = get_runtime_profile(runtime_id)
        if runtime is None:
            raise ValueError(f"No active runtime found for '{runtime_id}'.")

    agent_config = getattr(request, "agent_config", None) if request else None
    return session_id, runtime_id, runtime, agent_config


def _resolve_chat_execution(msgs, request: Any):
    session_id, runtime_id, runtime, agent_config = _resolve_chat_context(request)
    return (
        msgs,
        runtime_id,
        session_id,
        AgentConfig(**agent_config) if agent_config else None,
        runtime,
    )


async def chat_service(self, msgs, request=None, **kwargs):
    """Handle runtime-hosted chat queries with optional session persistence."""
    messages, runtime_id, session_id, agent_config, runtime = _resolve_chat_execution(msgs, request)

    lock = await _get_session_lock(session_id) if session_id else None
    if lock is None:
        async for msg, last in _runtime_adapter.stream_chat(
            profile=runtime,
            messages=messages,
            runtime_id=runtime_id,
            session_id=session_id,
            agent_config=agent_config,
            default_toolkit=toolkit,
        ):
            yield msg, last
        return

    async with lock:
        async for msg, last in _runtime_adapter.stream_chat(
            profile=runtime,
            messages=messages,
            runtime_id=runtime_id,
            session_id=session_id,
            agent_config=agent_config,
            default_toolkit=toolkit,
        ):
            yield msg, last


def register_chat_query(app: AgentApp) -> None:
    app.query(framework="agentscope")(chat_service)
