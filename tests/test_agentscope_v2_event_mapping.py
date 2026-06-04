"""Tests for mapping AgentScope v2 events to platform events."""

from agentscope.event import ReplyEndEvent, ReplyStartEvent, TextBlockDeltaEvent

from agentops.frameworks.agentscope_v2.event_mapping import PlatformEventMapper
from agentops.orchestration.models import RuntimeProfile


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_id="runtime-1",
        tenant_id="tenant-1",
        framework="agentscope",
        agent_spec={
            "model_config": {
                "model_name": "gpt-4o-mini",
                "api_key": "secret",
                "base_url": "http://localhost:9999/v1",
            },
            "system_prompt": "prompt",
            "prompt_hash": "sha256:test",
        },
        workspace={"root": "/tmp", "runtime_path": "/tmp/runtime-1"},
        storage={"type": "framework_memory"},
        trace={"enabled": False},
        status="ready",
    )


def test_maps_reply_start_to_before_turn() -> None:
    mapper = PlatformEventMapper(profile=_profile(), session_id="session-1", request_id="request-1")

    event = mapper.map_event(ReplyStartEvent(session_id="session-1", reply_id="reply-1", name="agent"))

    assert event.event == "before_turn"
    assert event.sequence == 1
    assert event.runtime_id == "runtime-1"
    assert event.tenant_id == "tenant-1"
    assert event.session_id == "session-1"
    assert event.request_id == "request-1"
    assert event.effective_model.model_name == "gpt-4o-mini"
    assert event.effective_model.base_url_host == "localhost:9999"
    assert event.prompt_hash == "sha256:test"
    assert event.payload == {
        "framework_event": "reply_start",
        "reply_id": "reply-1",
        "agent_name": "agent",
    }


def test_maps_text_delta_to_after_turn_streaming_payload() -> None:
    mapper = PlatformEventMapper(profile=_profile(), session_id="session-1")

    event = mapper.map_event(TextBlockDeltaEvent(reply_id="reply-1", block_id="block-1", delta="hello"))

    assert event.event == "after_turn"
    assert event.sequence == 1
    assert event.payload == {
        "status": "streaming",
        "framework_event": "text_block_delta",
        "reply_id": "reply-1",
        "block_id": "block-1",
        "delta": "hello",
    }


def test_maps_reply_end_to_after_turn_completed_payload() -> None:
    mapper = PlatformEventMapper(profile=_profile(), session_id="session-1")

    mapper.map_event(ReplyStartEvent(session_id="session-1", reply_id="reply-1", name="agent"))
    event = mapper.map_event(ReplyEndEvent(session_id="session-1", reply_id="reply-1"))

    assert event.event == "after_turn"
    assert event.sequence == 2
    assert event.payload == {
        "status": "completed",
        "framework_event": "reply_end",
        "reply_id": "reply-1",
    }


def test_ignores_unsupported_events() -> None:
    mapper = PlatformEventMapper(profile=_profile(), session_id="session-1")

    assert mapper.map_event(object()) is None
    assert mapper.sequence == 0
