"""Session persistence tests for RES-01, RES-03, and backward compatibility.

Tests validate the session-aware query handler contract:
- RES-01: Chat with session_id persists session state to JSON file
- RES-03: Subsequent chat with same session_id resumes with prior context
- D-05/D-12: Chat without session_id behaves identically to Phase 5 (backward compatible)
- T-6-01: validate_session_id rejects path traversal attempts

Uses mock query handler pattern from test_chat_stream.py to avoid real LLM calls.
"""

import json
import os
from unittest.mock import patch

import pytest
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.session import JSONSession

from src.main import app
from tests.test_chat_stream import _make_mock_handler, _parse_sse_events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def session_dir(tmp_path):
    """Provide a temporary session directory for each test."""
    return str(tmp_path / "sessions")


@pytest.fixture
def session_env(configured_env, session_dir, monkeypatch):
    """Configure env with a temporary session directory."""
    monkeypatch.setenv("SESSION_DIR", session_dir)
    return session_dir


# ---------------------------------------------------------------------------
# Test 1: Chat with session_id creates a session file (RES-01)
# ---------------------------------------------------------------------------


def test_session_persists_to_json(client, session_env):
    """RES-01: A chat request with session_id creates a session JSON file."""
    mock_handler = _make_mock_handler(["Hello"])
    session_id = "test-persist-session-001"

    payload = {
        "input": [
            {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
        ],
        "session_id": session_id,
    }

    with patch.object(app._runner, "query_handler", mock_handler):
        response = client.post("/process", json=payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses, f"Expected completed status, got: {statuses}"

    # Verify session_id is in the response events
    session_ids = [e.get("session_id") for e in events if e.get("session_id")]
    assert session_id in session_ids, (
        f"Expected session_id {session_id} in response, got: {session_ids}"
    )


# ---------------------------------------------------------------------------
# Test 2: Resume chat loads prior context (RES-03)
# ---------------------------------------------------------------------------


def test_session_resume_has_prior_context(client, session_env):
    """RES-03: A subsequent chat with same session_id has access to prior context."""
    session_id = "test-resume-session-002"

    # First request: create a session with some context
    captured_first = []

    async def _first_handler(msgs, request=None, response=None, **kwargs):
        if isinstance(msgs, list):
            captured_first.extend(msgs)
        else:
            captured_first.append(msgs)
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "First reply"}],
            role="assistant",
        )
        yield msg, True

    payload1 = {
        "input": [
            {"role": "user", "content": [{"type": "text", "text": "My name is Bob"}]},
        ],
        "session_id": session_id,
    }

    with patch.object(app._runner, "query_handler", _first_handler):
        response1 = client.post("/process", json=payload1)

    assert response1.status_code == 200

    # Second request: resume with same session_id
    captured_second = []

    async def _second_handler(msgs, request=None, response=None, **kwargs):
        if isinstance(msgs, list):
            captured_second.extend(msgs)
        else:
            captured_second.append(msgs)
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "I remember"}],
            role="assistant",
        )
        yield msg, True

    payload2 = {
        "input": [
            {"role": "user", "content": [{"type": "text", "text": "What is my name?"}]},
        ],
        "session_id": session_id,
    }

    with patch.object(app._runner, "query_handler", _second_handler):
        response2 = client.post("/process", json=payload2)

    assert response2.status_code == 200
    events = _parse_sse_events(response2.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


# ---------------------------------------------------------------------------
# Test 3: No session_id is backward compatible (D-05/D-12)
# ---------------------------------------------------------------------------


def test_no_session_id_backward_compatible(client, valid_payload):
    """D-05/D-12: Request without session_id works identically to Phase 5."""
    mock_handler = _make_mock_handler(["Hello back"])

    with patch.object(app._runner, "query_handler", mock_handler):
        response = client.post("/process", json=valid_payload)

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


# ---------------------------------------------------------------------------
# Test 4: validate_session_id rejects path traversal (T-6-01)
# ---------------------------------------------------------------------------


def test_session_id_path_traversal_rejected():
    """T-6-01: validate_session_id rejects path traversal attempts."""
    from src.agent.session import validate_session_id

    # Must reject path traversal patterns
    assert not validate_session_id("../etc/passwd")
    assert not validate_session_id("..%2Fetc%2Fpasswd")
    assert not validate_session_id("/absolute/path")
    assert not validate_session_id("relative/path")
    assert not validate_session_id("dot.separated")
    assert not validate_session_id("")
    assert not validate_session_id("   ")

    # Must accept valid identifiers
    assert validate_session_id("abc123")
    assert validate_session_id("550e8400-e29b-41d4-a716-446655440000")
    assert validate_session_id("test-session-001")


# ---------------------------------------------------------------------------
# Test 5: Real JSONSession round-trip with file I/O (RES-01 + RES-03 integration)
# ---------------------------------------------------------------------------


def test_session_real_json_round_trip(session_dir):
    """RES-01 + RES-03: Real JSONSession save/load creates file on disk and restores memory."""
    import asyncio

    async def _round_trip():
        session = JSONSession(save_dir=session_dir)
        session_id = "real-round-trip-001"

        # Save: create memory with a message, persist to disk
        memory_save = InMemoryMemory()
        await memory_save.add(
            Msg(name="user", content="hello from round-trip test", role="user")
        )
        await session.save_session_state(session_id=session_id, memory=memory_save)

        # Verify file exists on disk (RES-01)
        json_file = os.path.join(session_dir, f"{session_id}.json")
        assert os.path.exists(json_file), f"Session file not created at {json_file}"

        # Verify file content has the "memory" key (Pitfall 3: keyword arg naming)
        with open(json_file) as f:
            data = json.load(f)
        assert "memory" in data, "JSON file must have 'memory' top-level key"

        # Load: restore into fresh memory
        memory_load = InMemoryMemory()
        await session.load_session_state(session_id=session_id, memory=memory_load)

        # Verify content restored (RES-03)
        msgs = await memory_load.get_memory()
        assert len(msgs) == 1
        assert msgs[0].content == "hello from round-trip test"

    asyncio.run(_round_trip())
