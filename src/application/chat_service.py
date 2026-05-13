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


def _normalize_process_message(item: Any) -> ChatMessage:
    if isinstance(item, ChatMessage):
        return item
    if isinstance(item, Msg):
        return ChatMessage(role=item.role, content=item.content, name=item.name)
    role = getattr(item, "role", "user")
    content = getattr(item, "content", item)
    name = getattr(item, "name", role)
    return ChatMessage(role=role, content=content, name=name)


async def _stream_process_messages(msgs, request: Any):
    session_id = None
    if request and hasattr(request, "session_id") and request.session_id and validate_session_id(request.session_id):
        session_id = request.session_id
    lock = await _get_session_lock(session_id) if session_id else None

    if lock is None:
        async for item in _stream_process_messages_locked(msgs, request):
            yield item
    else:
        async with lock:
            async for item in _stream_process_messages_locked(msgs, request):
                yield item


async def _stream_process_messages_locked(msgs, request: Any):
    session_id, runtime_id, runtime, agent_config = _extract_request_context(request)
    chat_request = RuntimeChatRequest(
        messages=[_normalize_process_message(item) for item in msgs],
        runtime_id=runtime_id,
        session_id=session_id,
        agent_config=AgentConfig(**agent_config) if agent_config else None,
    )
    async for msg, last, _agent in _runtime_adapter.stream_with_profile(
        profile=runtime,
        request=chat_request,
        default_toolkit=toolkit,
    ):
        yield msg, last


def _sse_data(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _replace_first_text_block(content: Any, text: str) -> Any:
    if not isinstance(content, list):
        return content

    replaced = False
    blocks = []
    for block in content:
        if not replaced and isinstance(block, dict) and block.get("type") == "text":
            blocks.append({**block, "text": text})
            replaced = True
        else:
            blocks.append(block)
    return blocks


def _chat_event_to_payload(
    event,
    session_id: str | None,
    *,
    text: str | None = None,
) -> dict[str, Any]:
    event_text = event.text if text is None else text
    content = event.content
    if event.text is not None and text is not None:
        content = _replace_first_text_block(event.content, text)

    payload: dict[str, Any] = {
        "object": "message",
        "role": event.role,
        "name": event.name,
        "content": content,
        "status": "completed" if event.last else "in_progress",
    }
    if event_text is not None:
        payload["delta"] = {"text": event_text}
        payload["text"] = event_text
    if session_id:
        payload["session_id"] = session_id
    return payload


def _compute_text_delta(current_text: str | None, previous_text: str) -> tuple[str | None, str]:
    if current_text is None:
        return None, previous_text
    if previous_text and current_text.startswith(previous_text):
        return current_text[len(previous_text):], current_text
    return current_text, previous_text + current_text


async def process_query(self, msgs, request=None, **kwargs):
    """Handle runtime-hosted /process queries with optional session persistence."""
    async for item in _stream_process_messages(msgs, request):
        yield item


def register_query_handlers(app: AgentApp) -> None:
    app.query(framework="agentscope")(process_query)


async def chat_via_agentscope(request: ChatRequest):
    """Handle direct chat requests while preserving an SSE contract."""
    messages = []
    for item in request.input:
        role = item.role
        content = item.content
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
    previous_text_by_sender: dict[tuple[str, str | None], str] = {}
    async for msg, last, _agent in _runtime_adapter.stream_with_profile(
        profile=runtime,
        request=chat_request,
        default_toolkit=toolkit,
    ):
        event = agentscope_msg_to_chat_event(msg, last)
        previous_text = previous_text_by_sender.get((event.role, event.name), "")
        text, previous_text = _compute_text_delta(event.text, previous_text)
        previous_text_by_sender[(event.role, event.name)] = previous_text
        yield _sse_data(_chat_event_to_payload(event, session_id, text=text))
