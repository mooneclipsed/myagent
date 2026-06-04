"""Tests for AgentScope v2 session execution helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path

from agentscope.event import ReplyEndEvent, ReplyStartEvent, TextBlockDeltaEvent
from agentscope.message import AssistantMsg, Msg
from agentscope.state import AgentState
from agentscope.tool import Toolkit

from agentops.frameworks.agentscope_v2.execution import AgentScopeSessionExecutor
from agentops.frameworks.agentscope_v2.runtime import AgentScopeRuntimeResources
from agentops.orchestration.models import RuntimeProfile


class FakeAgent:
    """Fake AgentScope agent for session execution tests."""

    def __init__(self, state: AgentState) -> None:
        """Create a fake agent bound to state."""
        self.state = state
        self.inputs: list[Msg] = []

    async def reply(self, input_msg: Msg) -> Msg:
        """Record input and append it to state like AgentScope does."""
        self.inputs.append(input_msg)
        self.state.context.append(input_msg)
        message = AssistantMsg(name="agent", content=f"echo:{input_msg.get_text_content()}")
        self.state.context.append(message)
        return message

    async def reply_stream(self, input_msg: Msg):
        """Yield minimal AgentScope events."""
        self.inputs.append(input_msg)
        yield ReplyStartEvent(session_id=self.state.session_id, reply_id="reply-1", name="agent")
        yield TextBlockDeltaEvent(reply_id="reply-1", block_id="block-1", delta="hello")
        yield ReplyEndEvent(session_id=self.state.session_id, reply_id="reply-1")


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_id="runtime-1",
        framework="agentscope",
        agent_spec={
            "model_config": {"model_name": "fake", "api_key": "secret"},
            "system_prompt": "prompt",
            "prompt_hash": "sha256:test",
        },
        workspace={"root": "/tmp", "runtime_path": "/tmp/runtime-1"},
        storage={"type": "framework_memory"},
        trace={"enabled": False},
        status="ready",
    )


def _resources(tmp_path: Path) -> AgentScopeRuntimeResources:
    return AgentScopeRuntimeResources(toolkit=Toolkit(), mcp_clients=[], workspace_path=tmp_path)


def test_executor_reuses_agent_state_by_session_id(tmp_path: Path) -> None:
    created_agents: list[FakeAgent] = []

    def factory(profile, resources, state):
        agent = FakeAgent(state)
        created_agents.append(agent)
        return agent

    executor = AgentScopeSessionExecutor(
        profile=_profile(),
        resources=_resources(tmp_path),
        agent_factory=factory,
    )

    first = asyncio.run(executor.reply(session_id="session-1", input="hello"))
    second = asyncio.run(executor.reply(session_id="session-1", input="again"))

    state = executor.get_state("session-1")
    assert first.get_text_content() == "echo:hello"
    assert second.get_text_content() == "echo:again"
    assert state.session_id == "session-1"
    assert len(state.context) == 4
    assert created_agents[0].state is created_agents[1].state


def test_executor_separates_states_by_session_id(tmp_path: Path) -> None:
    executor = AgentScopeSessionExecutor(
        profile=_profile(),
        resources=_resources(tmp_path),
        agent_factory=lambda profile, resources, state: FakeAgent(state),
    )

    asyncio.run(executor.reply(session_id="session-1", input="one"))
    asyncio.run(executor.reply(session_id="session-2", input="two"))

    assert executor.get_state("session-1") is not executor.get_state("session-2")
    assert executor.get_state("session-1").context[0].get_text_content() == "one"
    assert executor.get_state("session-2").context[0].get_text_content() == "two"


def test_executor_streams_agentscope_events(tmp_path: Path) -> None:
    executor = AgentScopeSessionExecutor(
        profile=_profile(),
        resources=_resources(tmp_path),
        agent_factory=lambda profile, resources, state: FakeAgent(state),
    )

    async def collect_events():
        return [event async for event in executor.reply_stream(session_id="session-1", input="hello")]

    events = asyncio.run(collect_events())

    assert [event.__class__.__name__ for event in events] == [
        "ReplyStartEvent",
        "TextBlockDeltaEvent",
        "ReplyEndEvent",
    ]
    assert events[0].session_id == "session-1"
