"""Integration-style tests for skill bootstrap and process flow."""

from unittest.mock import patch

from agentscope.message import Msg

from tests.test_chat_stream import _parse_sse_events


async def _mock_stream(*args, **kwargs):
    coroutine_task = kwargs["coroutine_task"]
    coroutine_task.close()
    msg = Msg(
        name="agentops",
        content=[{"type": "text", "text": "skill activation ok"}],
        role="assistant",
    )
    yield msg, True


def test_bootstrap_returns_skill_summary_and_chat_completes(client, valid_payload):
    bootstrap_payload = {
        "runtime_id": "skill-chat-runtime-001",
        "skills": [
            {
                "skill_dir": "skills/example_skill",
            }
        ],
        "mcp_servers": [],
    }

    bootstrap_response = client.post("/runtimes/init", json=bootstrap_payload)
    assert bootstrap_response.status_code == 200, bootstrap_response.text
    body = bootstrap_response.json()
    assert body["skills"] == [
            {
                "name": "example-skill",
                "structured_tools": [],
            }
        ]

    with patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream):
        chat_payload = {
            **valid_payload,
            "session_id": "skill-chat-001",
        }
        chat_response = client.post("/chat", json=chat_payload)

    assert chat_response.status_code == 200
    events = _parse_sse_events(chat_response.text)
    statuses = [event.get("status") for event in events if "status" in event]
    assert "completed" in statuses
