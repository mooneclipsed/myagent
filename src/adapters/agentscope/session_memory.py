"""AgentScope session memory persistence helpers."""

from __future__ import annotations

import logging

from agentscope.memory import InMemoryMemory

from ...sessions.backend import get_session_backend

logger = logging.getLogger(__name__)


async def load_session_memory(session_id: str | None) -> InMemoryMemory:
    """Create memory and load persisted session state when a session id is present."""
    memory = InMemoryMemory()
    if session_id:
        await get_session_backend().load_session_state(
            session_id=session_id,
            memory=memory,
        )
    return memory


async def save_session_memory(session_id: str | None, agent) -> None:
    """Persist agent memory when a session id is present."""
    if not session_id:
        return

    try:
        await get_session_backend().save_session_state(
            session_id=session_id,
            memory=agent.memory,
        )
    except Exception as exc:
        logger.warning(
            "Failed to save session state for %s: %s",
            session_id,
            exc,
        )
