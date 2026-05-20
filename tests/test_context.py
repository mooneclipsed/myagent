"""Multi-turn context continuity tests for CAP-04.

Validates that the full message history reaches the agent when the client
sends a multi-turn messages array. No production code changes needed --
agentscope-runtime natively handles list[Msg] input via ReActAgent.reply().
"""

from unittest.mock import patch


from tests.test_chat_stream import _make_mock_runtime_stream, _parse_sse_events


def _bootstrap_runtime(client):
    response = client.post("/runtimes/init", json={})
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Test 1: Multi-turn request passes full history to the agent
# ---------------------------------------------------------------------------


def test_multi_turn_passes_full_history(client, multi_turn_payload):
    captured_calls = []
    mock_stream = _make_mock_runtime_stream(["I remember"], captured_calls=captured_calls)
    _bootstrap_runtime(client)

    with patch("agentops.application.chat_service._runtime_adapter.stream_chat", mock_stream):
        response = client.post("/chat", json=multi_turn_payload)

    assert response.status_code == 200
    captured_msgs = captured_calls[0]["messages"]
    assert len(captured_msgs) == 3
    assert captured_msgs[0].role == "user"
    assert captured_msgs[0].content == [{"type": "text", "text": "My name is Alice."}]
    assert captured_msgs[1].role == "assistant"
    assert captured_msgs[1].content == [{"type": "text", "text": "Hello Alice!"}]
    assert captured_msgs[2].role == "user"
    assert captured_msgs[2].content == [{"type": "text", "text": "What is my name?"}]


# ---------------------------------------------------------------------------
# Test 2: Single-turn request is backward compatible with Phase 4
# ---------------------------------------------------------------------------


def test_single_turn_backward_compatible(client, valid_payload):
    mock_stream = _make_mock_runtime_stream(["Hello back"])
    _bootstrap_runtime(client)

    with patch("agentops.application.chat_service._runtime_adapter.stream_chat", mock_stream):
        response = client.post("/chat", json=valid_payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


# ---------------------------------------------------------------------------
# Test 3: Multi-turn SSE lifecycle completes successfully
# ---------------------------------------------------------------------------


def test_multi_turn_sse_lifecycle(client, multi_turn_payload):
    mock_stream = _make_mock_runtime_stream(["I remember your name."])
    _bootstrap_runtime(client)

    with patch("agentops.application.chat_service._runtime_adapter.stream_chat", mock_stream):
        response = client.post("/chat", json=multi_turn_payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    events = _parse_sse_events(response.text)
    assert len(events) > 0
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


# ---------------------------------------------------------------------------
# Test 4: Prior assistant messages are included in context
# ---------------------------------------------------------------------------


def test_prior_assistant_messages_in_context(client):
    payload = {
        "input": [
            {"role": "user", "content": [{"type": "text", "text": "First question"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "First answer"}]},
            {"role": "user", "content": [{"type": "text", "text": "Second question"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Second answer"}]},
            {"role": "user", "content": [{"type": "text", "text": "Third question"}]},
        ]
    }

    captured_calls = []
    mock_stream = _make_mock_runtime_stream(["Third answer"], captured_calls=captured_calls)
    _bootstrap_runtime(client)

    with patch("agentops.application.chat_service._runtime_adapter.stream_chat", mock_stream):
        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    captured_msgs = captured_calls[0]["messages"]
    assert len(captured_msgs) == 5
    assert captured_msgs[1].role == "assistant"
    assert captured_msgs[1].content == [{"type": "text", "text": "First answer"}]
    assert captured_msgs[3].role == "assistant"
    assert captured_msgs[3].content == [{"type": "text", "text": "Second answer"}]
