"""SSE streaming contract tests for the /process endpoint.

Validates the full SSE lifecycle: created -> in_progress -> content deltas ->
message completed -> response completed. Uses a mocked query handler to avoid
real LLM API calls.
"""

import json
from unittest.mock import patch

import pytest
from agentscope.message import Msg


def _make_mock_handler(text_chunks):
    """Build an async generator that replaces the chat_query handler.

    Each entry in text_chunks is a string. The last entry gets last=True.
    Msg.content is set to [{"type": "text", "text": <chunk>}] so the
    agentscope stream adapter can parse it correctly.
    """

    async def _handler(msgs, request=None, response=None, **kwargs):
        for i, text in enumerate(text_chunks):
            is_last = i == len(text_chunks) - 1
            msg = Msg(
                name="agentops",
                content=[{"type": "text", "text": text}],
                role="assistant",
            )
            yield msg, is_last

    return _handler


def _make_failing_handler():
    """Build an async generator that yields one chunk then raises."""

    async def _handler(msgs, request=None, response=None, **kwargs):
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "Starting..."}],
            role="assistant",
        )
        yield msg, False
        raise RuntimeError("Simulated model failure")

    return _handler


def _parse_sse_events(response_text):
    """Parse SSE text into a list of decoded JSON event dicts.

    Skips empty lines and any non-JSON data lines.
    """
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        data_str = line[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            events.append(json.loads(data_str))
        except json.JSONDecodeError:
            pass
    return events


# ---------------------------------------------------------------------------
# Test 1: POST /process returns SSE stream with correct content type
# ---------------------------------------------------------------------------


def test_process_returns_sse_stream(client, valid_payload):
    mock_handler = _make_mock_handler(["Hello"])
    from src.main import app

    with patch.object(app._runner, "query_handler", mock_handler):
        response = client.post("/process", json=valid_payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    assert "text/event-stream" in response.headers.get("content-type", ""), (
        f"Expected text/event-stream, got {response.headers.get('content-type')}"
    )
    assert "data:" in response.text, "Response body should contain SSE data lines"


# ---------------------------------------------------------------------------
# Test 2: SSE stream contains full lifecycle events
# ---------------------------------------------------------------------------


def test_stream_lifecycle_events(client, valid_payload):
    mock_handler = _make_mock_handler(["Hello", " World!"])
    from src.main import app

    with patch.object(app._runner, "query_handler", mock_handler):
        response = client.post("/process", json=valid_payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert len(events) > 0, "SSE stream should contain at least one event"

    statuses = [e.get("status") for e in events if "status" in e]

    # The lifecycle must include created or in_progress at the start
    early_statuses = {"created", "in_progress"}
    assert early_statuses.intersection(statuses), (
        f"SSE lifecycle should start with created/in_progress, got statuses: {statuses}"
    )

    # The lifecycle must end with completed
    assert "completed" in statuses, (
        f"SSE lifecycle should include completed status, got statuses: {statuses}"
    )


# ---------------------------------------------------------------------------
# Test 3: Invalid input returns HTTP error or SSE error event
# ---------------------------------------------------------------------------


def test_invalid_input_returns_http_error(client):
    # Non-JSON body triggers FastAPI 422 before reaching the handler.
    response = client.post("/process", content="not json", headers={"content-type": "text/plain"})
    assert response.status_code == 422, (
        f"Expected 422 for non-JSON body, got {response.status_code}"
    )
    assert "text/event-stream" not in response.headers.get("content-type", ""), (
        "Invalid content-type should not return SSE stream"
    )

    # Empty JSON body {} -- agentscope-runtime wraps the validation error as
    # an SSE event (the framework catches AgentRequest validation failures
    # inside the runner). Confirm it returns an error, not a completed stream.
    response2 = client.post("/process", json={})
    if "text/event-stream" in response2.headers.get("content-type", ""):
        events = _parse_sse_events(response2.text)
        has_error = any(
            e.get("status") == "failed" or e.get("error") is not None
            for e in events
        )
        assert has_error, (
            "Empty body should produce an error in the SSE stream"
        )
    else:
        assert response2.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: Repeated requests both complete full SSE lifecycle
# ---------------------------------------------------------------------------


def test_repeated_requests_stable(client, valid_payload):
    mock_handler = _make_mock_handler(["Hello"])
    from src.main import app

    for i in range(2):
        with patch.object(app._runner, "query_handler", mock_handler):
            response = client.post("/process", json=valid_payload)

        assert response.status_code == 200, (
            f"Request {i+1}: expected 200, got {response.status_code}"
        )

        events = _parse_sse_events(response.text)
        statuses = [e.get("status") for e in events if "status" in e]
        assert "completed" in statuses, (
            f"Request {i+1}: SSE lifecycle should include completed, got {statuses}"
        )


# ---------------------------------------------------------------------------
# Test 5: Runtime failure during streaming emits SSE error event
# ---------------------------------------------------------------------------


def test_runtime_failure_emits_sse_error(client, valid_payload):
    failing_handler = _make_failing_handler()
    from src.main import app

    with patch.object(app._runner, "query_handler", failing_handler):
        response = client.post("/process", json=valid_payload)

    # The framework catches the error and yields it as an SSE event
    # with status "failed" or an "error" field.
    assert response.status_code == 200, (
        f"SSE stream should still start with 200, got {response.status_code}"
    )
    events = _parse_sse_events(response.text)
    statuses = [e.get("status") for e in events if "status" in e]

    # The stream should contain either a "failed" status or an error object
    has_error = (
        "failed" in statuses
        or any(e.get("error") is not None for e in events)
    )
    assert has_error, (
        f"Runtime failure should produce an error in the SSE stream, "
        f"got statuses: {statuses}"
    )
