"""Streaming query handler for the AgentScope runtime chat endpoint."""

import asyncio
from typing import Any

from ..adapters.agentscope.runtime import AgentScopeRuntime, AgentScopeRuntimeProfile
from ..config.runtime_models import ModelConfig
from .runtime_service import (
    get_active_runtime_profile,
)
from ..sessions.backend import validate_session_id


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


def _resolve_chat_context(request: Any) -> tuple[str | None, AgentScopeRuntimeProfile, Any]:
    session_id = None

    if request and hasattr(request, "session_id") and request.session_id:
        raw_session_id = request.session_id
        if validate_session_id(raw_session_id):
            session_id = raw_session_id
        else:
            raise ValueError("Invalid session_id format.")

    runtime = get_active_runtime_profile()
    if runtime is None:
        raise ValueError("Runtime has not been initialized. Call /runtimes/init first.")
    model_config = _get_request_model_config(request)
    return session_id, runtime, model_config


def _get_request_model_config(request: Any) -> Any:
    if request is None:
        return None
    extra_fields = getattr(request, "__pydantic_extra__", None)
    if isinstance(extra_fields, dict) and "model_config" in extra_fields:
        return extra_fields["model_config"]
    if isinstance(request, dict):
        return request.get("model_config")
    try:
        instance_fields = vars(request)
    except TypeError:
        return None
    if "model_config" in instance_fields:
        return instance_fields["model_config"]
    return None


def _build_chat_stream_args(
    msgs: Any,
    request: Any,
) -> tuple[Any, str | None, ModelConfig | None, AgentScopeRuntimeProfile]:
    session_id, runtime, model_config = _resolve_chat_context(request)
    return (
        msgs,
        session_id,
        ModelConfig(**model_config) if model_config else None,
        runtime,
    )


async def chat_service(self, msgs, request=None, **kwargs):
    """Handle runtime-hosted chat queries with optional session persistence."""
    messages, session_id, model_config, runtime = _build_chat_stream_args(msgs, request)

    lock = await _get_session_lock(session_id) if session_id else None
    if lock is None:
        async for msg, last in _runtime_adapter.stream_chat(
            profile=runtime,
            messages=messages,
            session_id=session_id,
            model_config=model_config,
        ):
            yield msg, last
        return

    async with lock:
        async for msg, last in _runtime_adapter.stream_chat(
            profile=runtime,
            messages=messages,
            session_id=session_id,
            model_config=model_config,
        ):
            yield msg, last
