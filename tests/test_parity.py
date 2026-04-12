"""RES-05: Parity test for JSON/Redis session backend consistency.

Validates that the same session data produces identical conversation
content when resumed from JSON and Redis backends.
"""
import asyncio

import fakeredis.aioredis
import pytest
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.session import JSONSession, RedisSession


def test_parity_json_redis_resume(tmp_path):
    """RES-05: Same session data produces identical conversation content across JSON and Redis backends."""
    async def _parity_test():
        session_id = "parity-test-session-001"
        session_dir = str(tmp_path / "json_sessions")

        # Create identical memory content
        messages = [
            Msg(name="user", content="Hello from parity test", role="user"),
            Msg(name="assistant", content="I received your message", role="assistant"),
            Msg(name="user", content="Can you remember this?", role="user"),
            Msg(name="assistant", content="Yes, I remember everything", role="assistant"),
        ]

        # --- Save with JSON backend ---
        json_session = JSONSession(save_dir=session_dir)
        json_memory = InMemoryMemory()
        for msg in messages:
            await json_memory.add(msg)
        await json_session.save_session_state(session_id=session_id, memory=json_memory)

        # --- Save with Redis (fakeredis) backend ---
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        redis_session = RedisSession(
            connection_pool=fake_redis.connection_pool,
            key_prefix="agentops:",
        )
        redis_memory = InMemoryMemory()
        for msg in messages:
            await redis_memory.add(msg)
        await redis_session.save_session_state(session_id=session_id, memory=redis_memory)

        # --- Load from JSON ---
        json_loaded = InMemoryMemory()
        await json_session.load_session_state(session_id=session_id, memory=json_loaded)
        json_msgs = await json_loaded.get_memory()

        # --- Load from Redis ---
        redis_loaded = InMemoryMemory()
        await redis_session.load_session_state(session_id=session_id, memory=redis_loaded)
        redis_msgs = await redis_loaded.get_memory()

        # --- Compare conversation content (D-05) ---
        assert len(json_msgs) == len(redis_msgs), (
            f"Message count mismatch: JSON={len(json_msgs)}, Redis={len(redis_msgs)}"
        )
        for i, (j_msg, r_msg) in enumerate(zip(json_msgs, redis_msgs)):
            assert j_msg.content == r_msg.content, (
                f"Message {i} content mismatch: JSON={j_msg.content!r}, Redis={r_msg.content!r}"
            )
            assert j_msg.name == r_msg.name, (
                f"Message {i} name mismatch: JSON={j_msg.name!r}, Redis={r_msg.name!r}"
            )
            assert j_msg.role == r_msg.role, (
                f"Message {i} role mismatch: JSON={j_msg.role!r}, Redis={r_msg.role!r}"
            )

        await redis_session.close()

    asyncio.run(_parity_test())
