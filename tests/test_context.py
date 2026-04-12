"""Multi-turn context continuity tests for CAP-04.

Validates that the full message history reaches the agent when the client
sends a multi-turn messages array. No production code changes needed --
agentscope-runtime natively handles list[Msg] input via ReActAgent.reply().
"""

import json
from unittest.mock import patch

import pytest
from agentscope.message import Msg

from src.main import app
from tests.test_chat_stream import _make_mock_handler, _parse_sse_events


# ---------------------------------------------------------------------------
# Test 1: Multi-turn request passes full history to the agent
# ---------------------------------------------------------------------------


def test_multi_turn_passes_full_history(client, multi_turn_payload):
    captured_msgs = []

    async def _capturing_handler(msgs, request=None, response=None, **kwargs):
        if isinstance(msgs, list):
            captured_msgs.extend(msgs)
        else:
            captured_msgs.append(msgs)
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "I remember"}],
            role="assistant",
        )
        yield msg, True

    with patch.object(app._runner, "query_handler", _capturing_handler):
        response = client.post("/process", json=multi_turn_payload)

    assert response.status_code == 200
    assert len(captured_msgs) == 3
    assert captured_msgs[0].role == "user"
    assert captured_msgs[0].content[0]["text"] == "My name is Alice."
    assert captured_msgs[1].role == "assistant"
    assert captured_msgs[1].content[0]["text"] == "Hello Alice!"
    assert captured_msgs[2].role == "user"
    assert captured_msgs[2].content[0]["text"] == "What is my name?"


# ---------------------------------------------------------------------------
# Test 2: Single-turn request is backward compatible with Phase 4
# ---------------------------------------------------------------------------


def test_single_turn_backward_compatible(client, valid_payload):
    mock_handler = _make_mock_handler(["Hello back"])

    with patch.object(app._runner, "query_handler", mock_handler):
        response = client.post("/process", json=valid_payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


# ---------------------------------------------------------------------------
# Test 3: Multi-turn SSE lifecycle completes successfully
# ---------------------------------------------------------------------------


def test_multi_turn_sse_lifecycle(client, multi_turn_payload):
    mock_handler = _make_mock_handler(["I remember your name."])

    with patch.object(app._runner, "query_handler", mock_handler):
        response = client.post("/process", json=multi_turn_payload)

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

    captured_msgs = []

    async def _capturing_handler(msgs, request=None, response=None, **kwargs):
        if isinstance(msgs, list):
            captured_msgs.extend(msgs)
        else:
            captured_msgs.append(msgs)
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "Third answer"}],
            role="assistant",
        )
        yield msg, True

    with patch.object(app._runner, "query_handler", _capturing_handler):
        response = client.post("/process", json=payload)

    assert response.status_code == 200
    assert len(captured_msgs) == 5
    assert captured_msgs[1].role == "assistant"
    assert captured_msgs[1].content[0]["text"] == "First answer"
    assert captured_msgs[3].role == "assistant"
    assert captured_msgs[3].content[0]["text"] == "Second answer"
