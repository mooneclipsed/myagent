"""Tests for AgentScope v2 session persistence boundary."""

import asyncio
from dataclasses import dataclass

from agentscope.message import UserMsg
from agentscope.state import AgentState

from agentops.frameworks.agentscope_v2.session_store import (
    AgentScopeAppSessionStore,
    InMemoryAgentScopeSessionStore,
)


@dataclass
class FakeSessionRecord:
    """Fake AgentScope session record."""

    state: AgentState


class FakeStorage:
    """Fake AgentScope app storage."""

    def __init__(self) -> None:
        """Create fake storage."""
        self.records: dict[tuple[str, str, str], FakeSessionRecord] = {}
        self.upsert_calls = []
        self.update_calls = []

    async def get_session(self, *, user_id: str, agent_id: str, session_id: str):
        """Return a fake session record."""
        return self.records.get((user_id, agent_id, session_id))

    async def upsert_session(self, **kwargs):
        """Create a fake session record."""
        key = (kwargs["user_id"], kwargs["agent_id"], kwargs["session_id"])
        self.upsert_calls.append(kwargs)
        self.records[key] = FakeSessionRecord(kwargs["state"])

    async def update_session_state(self, **kwargs) -> None:
        """Update a fake session record."""
        key = (kwargs["user_id"], kwargs["agent_id"], kwargs["session_id"])
        self.update_calls.append(kwargs)
        self.records[key] = FakeSessionRecord(kwargs["state"])


def test_in_memory_session_store_round_trips_state() -> None:
    store = InMemoryAgentScopeSessionStore()
    state = AgentState(session_id="session-1")
    state.context.append(UserMsg(name="user", content="hello"))

    asyncio.run(store.save_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
        state=state,
    ))

    loaded = asyncio.run(store.load_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
    ))

    assert loaded is state


def test_app_session_store_upserts_missing_session() -> None:
    storage = FakeStorage()
    store = AgentScopeAppSessionStore(storage=storage, user_id="tenant-1")
    state = AgentState(session_id="session-1")

    asyncio.run(store.save_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
        state=state,
    ))

    assert len(storage.upsert_calls) == 1
    assert storage.upsert_calls[0]["config"].workspace_id == "/tmp/runtime-1"
    assert asyncio.run(store.load_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
    )) is state


def test_app_session_store_updates_existing_session() -> None:
    storage = FakeStorage()
    store = AgentScopeAppSessionStore(storage=storage)
    existing = AgentState(session_id="session-1")
    updated = AgentState(session_id="session-1")

    asyncio.run(store.save_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
        state=existing,
    ))
    asyncio.run(store.save_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
        state=updated,
    ))

    assert len(storage.upsert_calls) == 1
    assert len(storage.update_calls) == 1
    assert asyncio.run(store.load_state(
        runtime_id="runtime-1",
        session_id="session-1",
        workspace_id="/tmp/runtime-1",
    )) is updated
