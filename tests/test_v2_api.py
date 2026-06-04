"""Tests for refactor-v2 HTTP routes."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from agentscope.event import ReplyEndEvent, ReplyStartEvent

from agentops.api.v2 import V2RuntimeApiService, register_v2_routes
from agentops.frameworks.agentscope_v2.event_mapping import PlatformEventMapper


class FakeExecutor:
    """Fake v2 executor that emits platform events."""

    def __init__(self, *, profile, resources) -> None:
        """Create a fake executor."""
        self.profile = profile
        self.resources = resources

    async def platform_event_stream(self, *, session_id: str, input: str, request_id: str | None = None):
        """Stream a deterministic platform event sequence."""
        mapper = PlatformEventMapper(profile=self.profile, session_id=session_id, request_id=request_id)
        start = mapper.map_event(ReplyStartEvent(session_id=session_id, reply_id=input, name="agent"))
        end = mapper.map_event(ReplyEndEvent(session_id=session_id, reply_id=input))
        yield start
        yield end


def _client() -> TestClient:
    app = FastAPI()
    register_v2_routes(app, service=V2RuntimeApiService(executor_factory=FakeExecutor))
    return TestClient(app)


def _parse_sse_events(response_text: str) -> list[dict]:
    events = []
    for line in response_text.splitlines():
        if not line.startswith("data:"):
            continue
        events.append(json.loads(line.removeprefix("data:").strip()))
    return events


def test_v2_runtime_init_returns_public_runtime_result() -> None:
    client = _client()

    response = client.post(
        "/v2/runtimes/init",
        json={
            "runtime_id": "runtime-1",
            "framework": "agentscope",
            "model_config": {"model_name": "fake", "api_key": "secret"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["runtime_id"] == "runtime-1"
    assert body["framework"] == "agentscope"
    assert body["status"] == "ready"
    assert "secret" not in response.text


def test_v2_runtime_init_rejects_unknown_framework() -> None:
    client = _client()

    response = client.post("/v2/runtimes/init", json={"runtime_id": "runtime-1", "framework": "missing"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Framework 'missing' does not exist."


def test_v2_chat_streams_platform_events() -> None:
    client = _client()
    init_response = client.post("/v2/runtimes/init", json={"runtime_id": "runtime-1"})
    assert init_response.status_code == 200, init_response.text

    response = client.post(
        "/v2/chat",
        json={
            "runtime_id": "runtime-1",
            "session_id": "session-1",
            "input": "hello",
            "execution_config": {"request_id": "request-1"},
        },
    )

    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers["content-type"]
    events = _parse_sse_events(response.text)
    assert [event["event"] for event in events] == ["before_turn", "after_turn"]
    assert [event["sequence"] for event in events] == [1, 2]
    assert events[0]["request_id"] == "request-1"
    assert events[0]["payload"]["framework_event"] == "reply_start"
    assert events[1]["payload"]["status"] == "completed"


def test_v2_chat_requires_initialized_runtime() -> None:
    client = _client()

    response = client.post(
        "/v2/chat",
        json={"runtime_id": "runtime-1", "session_id": "session-1", "input": "hello"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Runtime has not been initialized."
