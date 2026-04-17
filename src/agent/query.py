"""Streaming query handlers for runtime-hosted /process and direct /chat."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from opentelemetry import trace as ot_trace

from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.pipeline import stream_printing_messages

from src.agent.session import get_session_backend, validate_session_id
from src.agent.session_runtime import (
    bind_agentscope_run_context,
    build_react_agent,
    get_session_runtime,
    log_tracing_state,
)
from src.core.config import AgentConfig, resolve_effective_config
from src.main import app
from src.tools import toolkit

logger = logging.getLogger(__name__)


@dataclass
class QueryExecutionContext:
    session_id: str | None
    agent: Any
    use_session_run_context: bool = False
    tracing_enabled: bool = False


async def _build_query_execution_context(request: Any) -> QueryExecutionContext:
    session_id = None
    runtime = None

    if request and hasattr(request, "session_id") and request.session_id:
        raw_session_id = request.session_id
        if validate_session_id(raw_session_id):
            session_id = raw_session_id
            runtime = get_session_runtime(session_id)

    if runtime is not None:
        if request and hasattr(request, "agent_config") and request.agent_config:
            raise ValueError(
                "Bootstrapped sessions do not accept agent_config on /process. Re-bootstrap the session instead.",
            )
        return QueryExecutionContext(
            session_id=session_id,
            agent=runtime.agent,
            use_session_run_context=True,
            tracing_enabled=bool(runtime.resolved_config),
        )

    agent_config = None
    if request and hasattr(request, "agent_config") and request.agent_config:
        agent_config = AgentConfig(**request.agent_config)
    config = resolve_effective_config(agent_config)

    memory = InMemoryMemory()
    if session_id:
        await get_session_backend().load_session_state(
            session_id=session_id,
            memory=memory,
        )

    agent = build_react_agent(
        resolved_config=config,
        memory=memory,
        toolkit=toolkit,
    )
    return QueryExecutionContext(session_id=session_id, agent=agent)


async def _stream_agent_messages(msgs, request: Any):
    execution = await _build_query_execution_context(request)
    log_tracing_state(f"query-start:{execution.session_id or 'no-session'}")

    try:
        if execution.use_session_run_context and execution.session_id:
            with bind_agentscope_run_context(
                execution.session_id,
                trace_enabled=execution.tracing_enabled,
            ):
                async for msg, last in stream_printing_messages(
                    agents=[execution.agent],
                    coroutine_task=execution.agent(msgs),
                ):
                    yield msg, last
        else:
            async for msg, last in stream_printing_messages(
                agents=[execution.agent],
                coroutine_task=execution.agent(msgs),
            ):
                yield msg, last
    finally:
        try:
            provider = ot_trace.get_tracer_provider()
            force_flush = getattr(provider, "force_flush", None)
            if callable(force_flush):
                flushed = force_flush()
                logger.info(
                    "Tracing force_flush [%s]: %r",
                    execution.session_id or "no-session",
                    flushed,
                )
            log_tracing_state(f"query-end:{execution.session_id or 'no-session'}")
        except Exception as exc:  # pragma: no cover - diagnostics only
            logger.warning("Tracing flush failed for %s: %s", execution.session_id, exc)

        if execution.session_id:
            try:
                await get_session_backend().save_session_state(
                    session_id=execution.session_id,
                    memory=execution.agent.memory,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to save session state for %s: %s",
                    execution.session_id,
                    exc,
                )


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


@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    """Handle runtime-hosted /process queries with optional session persistence."""
    async for item in _stream_agent_messages(msgs, request):
        yield item


@app.post("/chat")
async def chat_via_agentscope(request: Request):
    """Handle direct AgentScope chat requests while preserving an SSE contract."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid JSON body") from exc

    input_items = body.get("input")
    if not isinstance(input_items, list) or not input_items:
        return StreamingResponse(
            iter([
                _sse_data({"status": "failed", "error": {"message": "input must be a non-empty list"}}),
            ]),
            media_type="text/event-stream",
        )

    class RequestShim:
        def __init__(self, payload: dict[str, Any]):
            self.session_id = payload.get("session_id")
            self.agent_config = payload.get("agent_config")

    msgs = []
    for item in input_items:
        role = item.get("role", "user")
        content = item.get("content", [])
        if isinstance(content, list) and len(content) == 1 and content[0].get("type") == "text":
            msgs.append(Msg(role, content[0].get("text", ""), role))
        else:
            msgs.append(Msg(role, content, role))

    request_shim = RequestShim(body)

    async def event_stream():
        if request_shim.session_id:
            session_id = request_shim.session_id if validate_session_id(request_shim.session_id) else None
        else:
            session_id = None
        yield _sse_data({"status": "created", **({"session_id": session_id} if session_id else {})})
        yield _sse_data({"status": "in_progress", **({"session_id": session_id} if session_id else {})})
        try:
            async for msg, last in _stream_agent_messages(msgs, request_shim):
                yield _sse_data(_msg_to_payload(msg, last, session_id))
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
