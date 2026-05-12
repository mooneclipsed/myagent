"""Streaming query handlers and shared HTTP chat helpers."""

import asyncio
import json
from typing import Any, Literal

from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

from agentscope_runtime.engine import AgentApp
from agentscope.message import Msg

from ..adapters.agentscope.runtime import AgentScopeRuntime, agentscope_msg_to_chat_event
from ..config.schemas import AgentConfig
from ..core.interfaces import ChatMessage, ChatRequest as RuntimeChatRequest
from .runtime_service import (
    get_runtime_profile,
)
from ..sessions.backend import validate_session_id
from ..tools import toolkit


_session_locks: dict[str, asyncio.Lock] = {}
_session_locks_guard = asyncio.Lock()
_runtime_adapter = AgentScopeRuntime()


ContentBlock = dict[str, Any]


class ChatInput(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str | list[ContentBlock] = Field(default_factory=list)


class ChatRequest(BaseModel):
    runtime_id: str | None = None
    session_id: str | None = None
    agent_config: dict[str, Any] | None = None
    input: list[ChatInput] = Field(min_length=1)


async def _get_session_lock(session_id: str) -> asyncio.Lock:
    async with _session_locks_guard:
        lock = _session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _session_locks[session_id] = lock
        return lock


def _extract_request_context(request: Any) -> tuple[str | None, str | None, Any, Any]:
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


def _coerce_chat_message(item: Any) -> ChatMessage:
    if isinstance(item, ChatMessage):
        return item
    if isinstance(item, Msg):
        return ChatMessage(role=item.role, content=item.content, name=item.name)
    role = getattr(item, "role", "user")
    content = getattr(item, "content", item)
    name = getattr(item, "name", role)
    return ChatMessage(role=role, content=content, name=name)


async def _stream_agent_messages(msgs, request: Any):
    session_id = None
    if request and hasattr(request, "session_id") and request.session_id and validate_session_id(request.session_id):
        session_id = request.session_id
    lock = await _get_session_lock(session_id) if session_id else None

    if lock is None:
        async for item in _stream_agent_messages_locked(msgs, request):
            yield item
    else:
        async with lock:
            async for item in _stream_agent_messages_locked(msgs, request):
                yield item


async def _stream_agent_messages_locked(msgs, request: Any):
    session_id, runtime_id, runtime, agent_config = _extract_request_context(request)
    config = AgentConfig(**agent_config) if agent_config else None
    chat_request = RuntimeChatRequest(
        messages=[_coerce_chat_message(item) for item in msgs],
        runtime_id=runtime_id,
        session_id=session_id,
        agent_config=config,
    )
    async for msg, last, _agent in _runtime_adapter.stream_with_profile(
        profile=runtime,
        request=chat_request,
        default_toolkit=toolkit,
    ):
        yield msg, last


def _sse_data(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _msg_to_payload(msg: Msg, last: bool, session_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "object": "message",
        "role": msg.role,
        "name": msg.name,
        "content": msg.content,
        "status": "completed" if last else "in_progress",
    }
    if msg.content:
        first = msg.content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            payload["delta"] = {"text": first.get("text", "")}
            payload["text"] = first.get("text", "")
    if session_id:
        payload["session_id"] = session_id
    return payload


def _chat_event_to_payload(event, session_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "object": "message",
        "role": event.role,
        "name": event.name,
        "content": event.content,
        "status": "completed" if event.last else "in_progress",
    }
    if event.text is not None:
        payload["delta"] = {"text": event.text}
        payload["text"] = event.text
    if session_id:
        payload["session_id"] = session_id
    return payload


async def chat_query(self, msgs, request=None, **kwargs):
    """Handle runtime-hosted /process queries with optional session persistence."""
    async for item in _stream_agent_messages(msgs, request):
        yield item


def register_query_handlers(app: AgentApp) -> None:
    app.query(framework="agentscope")(chat_query)


async def chat_via_agentscope(request: ChatRequest):
    """Handle direct chat requests while preserving an SSE contract."""
    messages = []
    for item in request.input:
        role = item.role
        content = item.content
        if isinstance(content, list) and len(content) == 1 and content[0].get("type") == "text":
            messages.append(ChatMessage(role=role, content=content[0].get("text", ""), name=role))
        else:
            messages.append(ChatMessage(role=role, content=content, name=role))

    async def event_stream():
        if request.session_id:
            session_id = request.session_id if validate_session_id(request.session_id) else None
        else:
            session_id = None
        yield _sse_data({"status": "created", **({"session_id": session_id} if session_id else {})})
        yield _sse_data({"status": "in_progress", **({"session_id": session_id} if session_id else {})})
        try:
            lock = await _get_session_lock(session_id) if session_id else None
            if lock is None:
                async for event in _stream_chat_request(messages, request, session_id):
                    yield event
            else:
                async with lock:
                    async for event in _stream_chat_request(messages, request, session_id):
                        yield event
            yield _sse_data({"status": "completed", **({"session_id": session_id} if session_id else {})})
        except Exception as exc:
            yield _sse_data(
                {
                    "status": "failed",
                    "error": {"message": str(exc)},
                    **({"session_id": session_id} if session_id else {}),
                }
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _stream_chat_request(
    messages: list[ChatMessage],
    request: ChatRequest,
    session_id: str | None,
):
    _session_id, runtime_id, runtime, agent_config = _extract_request_context(request)
    chat_request = RuntimeChatRequest(
        messages=messages,
        runtime_id=runtime_id,
        session_id=session_id,
        agent_config=AgentConfig(**agent_config) if agent_config else None,
    )
    async for msg, last, _agent in _runtime_adapter.stream_with_profile(
        profile=runtime,
        request=chat_request,
        default_toolkit=toolkit,
    ):
        event = agentscope_msg_to_chat_event(msg, last)
        yield _sse_data(_chat_event_to_payload(event, session_id))
