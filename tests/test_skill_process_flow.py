"""Integration-style tests for skill bootstrap and process flow."""

from unittest.mock import patch

from agentscope.message import Msg

from src.main import app
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


def test_bootstrap_returns_skill_summary_and_process_completes(client, valid_payload):
    bootstrap_payload = {
        "session_id": "skill-process-001",
        "skills": [
            {
                "skill_dir": "skills/example_skill",
                "activation_mode": "lazy",
                "expose_structured_tools": True,
            }
        ],
        "mcp_servers": [],
    }

    bootstrap_response = client.post("/sessions/bootstrap", json=bootstrap_payload)
    assert bootstrap_response.status_code == 200, bootstrap_response.text
    body = bootstrap_response.json()
    assert body["skills"] == [
        {
            "name": "example-skill",
            "activation_mode": "lazy",
            "structured_tools": [
                "run_platform_report",
                "summarize_platform_callable",
            ],
        }
    ]

    with patch("src.agent.query.stream_printing_messages", _mock_stream):
        process_payload = {
            **valid_payload,
            "session_id": "skill-process-001",
        }
        process_response = client.post("/process", json=process_payload)

    assert process_response.status_code == 200
    events = _parse_sse_events(process_response.text)
    statuses = [event.get("status") for event in events if "status" in event]
    assert "completed" in statuses
