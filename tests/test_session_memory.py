"""Tests for AgentScope session memory persistence helpers."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agentscope.memory import InMemoryMemory
from agentscope.message import Msg

from agentops.adapters.agentscope.session_memory import save_session_memory


def test_save_session_memory_skips_empty_memory():
    memory = InMemoryMemory()
    agent = SimpleNamespace(memory=memory)
    backend = SimpleNamespace(save_session_state=AsyncMock())

    with patch("agentops.adapters.agentscope.session_memory.get_session_backend", return_value=backend):
        asyncio.run(save_session_memory("empty-session", agent))

    backend.save_session_state.assert_not_awaited()


def test_save_session_memory_persists_non_empty_memory():
    memory = InMemoryMemory()
    asyncio.run(memory.add(Msg(name="user", content="hello", role="user")))
    agent = SimpleNamespace(memory=memory)
    backend = SimpleNamespace(save_session_state=AsyncMock())

    with patch("agentops.adapters.agentscope.session_memory.get_session_backend", return_value=backend):
        asyncio.run(save_session_memory("non-empty-session", agent))

    backend.save_session_state.assert_awaited_once_with(
        session_id="non-empty-session",
        memory=memory,
    )
