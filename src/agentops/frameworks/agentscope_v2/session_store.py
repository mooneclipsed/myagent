"""AgentScope v2 session state persistence boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agentscope.app.storage import SessionConfig, StorageBase
from agentscope.state import AgentState


class AgentScopeSessionStore(Protocol):
    """Persistence boundary for AgentScope v2 session state."""

    async def load_state(self, *, runtime_id: str, session_id: str, workspace_id: str) -> AgentState | None:
        """Load session state if it exists."""

    async def save_state(
        self,
        *,
        runtime_id: str,
        session_id: str,
        workspace_id: str,
        state: AgentState,
    ) -> None:
        """Persist session state."""


@dataclass
class InMemoryAgentScopeSessionStore:
    """In-memory AgentScope state store for local execution and tests."""

    _states: dict[tuple[str, str], AgentState] | None = None

    def __post_init__(self) -> None:
        """Initialize the in-memory state map."""
        if self._states is None:
            self._states = {}

    async def load_state(self, *, runtime_id: str, session_id: str, workspace_id: str) -> AgentState | None:
        """Load session state from memory."""
        return self._states.get((runtime_id, session_id))

    async def save_state(
        self,
        *,
        runtime_id: str,
        session_id: str,
        workspace_id: str,
        state: AgentState,
    ) -> None:
        """Save session state in memory."""
        self._states[(runtime_id, session_id)] = state


@dataclass
class AgentScopeAppSessionStore:
    """AgentScope app storage-backed session store."""

    storage: StorageBase
    user_id: str = "default"

    async def load_state(self, *, runtime_id: str, session_id: str, workspace_id: str) -> AgentState | None:
        """Load AgentScope session state from app storage."""
        record = await self.storage.get_session(
            user_id=self.user_id,
            agent_id=runtime_id,
            session_id=session_id,
        )
        if record is None:
            return None
        return record.state

    async def save_state(
        self,
        *,
        runtime_id: str,
        session_id: str,
        workspace_id: str,
        state: AgentState,
    ) -> None:
        """Save AgentScope session state to app storage."""
        existing = await self.storage.get_session(
            user_id=self.user_id,
            agent_id=runtime_id,
            session_id=session_id,
        )
        if existing is None:
            await self.storage.upsert_session(
                user_id=self.user_id,
                agent_id=runtime_id,
                session_id=session_id,
                config=SessionConfig(workspace_id=workspace_id),
                state=state,
            )
            return

        await self.storage.update_session_state(
            user_id=self.user_id,
            agent_id=runtime_id,
            session_id=session_id,
            state=state,
        )
