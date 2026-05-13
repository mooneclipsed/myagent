"""SSE streaming contract tests for the /chat endpoint.

Validates the full SSE lifecycle: created -> in_progress -> content deltas ->
message completed -> response completed. Uses a mocked runtime stream to avoid
real LLM API calls.
"""

import json
from unittest.mock import patch

import pytest
from agentscope.message import Msg


def _make_mock_runtime_stream(text_chunks, *, captured_requests=None):
    """Build an async generator that replaces the chat runtime stream."""

    async def _stream(*args, **kwargs):
        if captured_requests is not None:
            captured_requests.append(kwargs.get("request"))
        for i, text in enumerate(text_chunks):
            is_last = i == len(text_chunks) - 1
            msg = Msg(
                name="agentops",
                content=[{"type": "text", "text": text}],
                role="assistant",
            )
            yield msg, is_last, None

    return _stream


def _make_failing_runtime_stream():
    """Build an async generator that yields one chunk then raises."""

    async def _stream(*args, **kwargs):
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "Starting..."}],
            role="assistant",
        )
        yield msg, False, None
        raise RuntimeError("Simulated model failure")

    return _stream


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
# Test 1: POST /chat returns SSE stream with correct content type
# ---------------------------------------------------------------------------


def test_chat_returns_sse_stream(client, valid_payload):
    mock_stream = _make_mock_runtime_stream(["Hello"])

    with patch("src.application.chat_service._runtime_adapter.stream_with_profile", mock_stream):
        response = client.post("/chat", json=valid_payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    assert "text/event-stream" in response.headers.get("content-type", ""), (
        f"Expected text/event-stream, got {response.headers.get('content-type')}"
    )
    assert "data:" in response.text, "Response body should contain SSE data lines"


def test_chat_accepts_string_content(client):
    mock_stream = _make_mock_runtime_stream(["Hello"])

    payload = {
        "input": [
            {
                "role": "user",
                "content": "Hello, reply with one word.",
            }
        ]
    }
    with patch("src.application.chat_service._runtime_adapter.stream_with_profile", mock_stream):
        response = client.post("/chat", json=payload)

    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.parametrize("role", ["system", "tool"])
def test_chat_rejects_invalid_role(client, role):
    payload = {
        "input": [
            {
                "role": role,
                "content": "Hello",
            }
        ]
    }
    response = client.post("/chat", json=payload)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 2: SSE stream contains full lifecycle events
# ---------------------------------------------------------------------------


def test_stream_lifecycle_events(client, valid_payload):
    mock_stream = _make_mock_runtime_stream(["Hello", " World!"])

    with patch("src.application.chat_service._runtime_adapter.stream_with_profile", mock_stream):
        response = client.post("/chat", json=valid_payload)

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
    response = client.post("/chat", content="not json", headers={"content-type": "text/plain"})
    assert response.status_code == 422, (
        f"Expected 422 for non-JSON body, got {response.status_code}"
    )
    assert "text/event-stream" not in response.headers.get("content-type", ""), (
        "Invalid content-type should not return SSE stream"
    )

    response2 = client.post("/chat", json={})
    assert response2.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: Repeated requests both complete full SSE lifecycle
# ---------------------------------------------------------------------------


def test_repeated_requests_stable(client, valid_payload):
    mock_stream = _make_mock_runtime_stream(["Hello"])

    for i in range(2):
        with patch("src.application.chat_service._runtime_adapter.stream_with_profile", mock_stream):
            response = client.post("/chat", json=valid_payload)

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
    failing_stream = _make_failing_runtime_stream()

    with patch("src.application.chat_service._runtime_adapter.stream_with_profile", failing_stream):
        response = client.post("/chat", json=valid_payload)

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
