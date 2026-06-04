"""Tests for configured AgentScope v2 session storage assembly."""

import asyncio

from agentops.config.settings import Settings
from agentops.frameworks.agentscope_v2.session_store import AgentScopeAppSessionStore, InMemoryAgentScopeSessionStore
from agentops.frameworks.agentscope_v2.storage import (
    AgentScopeSessionStoreConfigError,
    AgentScopeSessionStoreProvider,
    create_session_store_provider_from_settings,
)


def _settings(**overrides) -> Settings:
    values = {
        "model_name": "test-model",
        "model_api_key": "test-key",
        "model_base_url": "http://localhost:9999/v1",
    }
    values.update(overrides)
    return Settings(**values)


def test_json_backend_uses_in_memory_session_store() -> None:
    provider = create_session_store_provider_from_settings(_settings(session_backend="json"))

    store = provider.create_store(user_id="tenant-1")

    assert provider.backend == "json"
    assert isinstance(store, InMemoryAgentScopeSessionStore)


def test_memory_backend_uses_in_memory_session_store() -> None:
    provider = create_session_store_provider_from_settings(_settings(session_backend="memory"))

    store = provider.create_store(user_id="tenant-1")

    assert provider.backend == "memory"
    assert isinstance(store, InMemoryAgentScopeSessionStore)


def test_redis_backend_configures_agentscope_redis_storage() -> None:
    provider = create_session_store_provider_from_settings(_settings(
        session_backend="redis",
        redis_host="redis.internal",
        redis_port=6380,
        redis_db=2,
        redis_password="secret",
    ))

    assert provider.backend == "redis"
    assert provider.redis_storage is not None
    assert provider.redis_storage._host == "redis.internal"
    assert provider.redis_storage._port == 6380
    assert provider.redis_storage._db == 2
    assert provider.redis_storage._password == "secret"


def test_redis_store_requires_open_provider() -> None:
    provider = create_session_store_provider_from_settings(_settings(session_backend="redis"))

    try:
        provider.create_store(user_id="tenant-1")
    except AgentScopeSessionStoreConfigError as exc:
        assert str(exc) == "Redis session store has not been opened."
    else:
        raise AssertionError("Expected Redis provider to require open().")


def test_redis_provider_creates_app_session_store_after_open(monkeypatch) -> None:
    provider = create_session_store_provider_from_settings(_settings(session_backend="redis"))
    calls = []

    async def fake_enter():
        calls.append("enter")
        return provider.redis_storage

    async def fake_exit(exc_type, exc_value, traceback):
        calls.append("exit")

    monkeypatch.setattr(provider.redis_storage, "__aenter__", fake_enter)
    monkeypatch.setattr(provider.redis_storage, "__aexit__", fake_exit)

    asyncio.run(provider.open())
    store = provider.create_store(user_id="tenant-1")
    asyncio.run(provider.close())

    assert calls == ["enter", "exit"]
    assert isinstance(store, AgentScopeAppSessionStore)
    assert store.user_id == "tenant-1"


def test_unknown_backend_fails_clearly() -> None:
    try:
        create_session_store_provider_from_settings(_settings(session_backend="sqlite"))
    except AgentScopeSessionStoreConfigError as exc:
        assert str(exc) == "Unsupported SESSION_BACKEND for AgentScope v2: sqlite"
    else:
        raise AssertionError("Expected unsupported backend to fail.")


def test_memory_provider_close_is_noop() -> None:
    provider = AgentScopeSessionStoreProvider(backend="memory")

    asyncio.run(provider.open())
    asyncio.run(provider.close())

    assert isinstance(provider.create_store(user_id="tenant-1"), InMemoryAgentScopeSessionStore)
