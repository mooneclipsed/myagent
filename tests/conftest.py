"""Shared fixtures for Phase 2+ streaming contract tests."""

import asyncio
import pytest
from fastapi.testclient import TestClient

from src.application.runtime_service import close_all_session_runtimes


@pytest.fixture(autouse=True)
def _clear_session_runtimes():
    """Clear active runtime profile before and after each test."""
    asyncio.run(close_all_session_runtimes())
    yield
    asyncio.run(close_all_session_runtimes())


@pytest.fixture
def configured_env(monkeypatch):
    """Set required env vars for settings loading and disable .env file."""
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_BASE_URL", "http://localhost:9999/v1")
    # Prevent .env file from providing fallback values during tests
    from src.config.settings import Settings

    monkeypatch.setattr(
        Settings,
        "model_config",
        {**Settings.model_config, "env_file": None},
    )


@pytest.fixture
def clear_settings_cache():
    """Clear the lru_cache on get_settings before and after each test."""
    try:
        from src.config.settings import get_settings

        get_settings.cache_clear()
    except Exception:
        pass
    yield
    try:
        from src.config.settings import get_settings

        get_settings.cache_clear()
    except Exception:
        pass


@pytest.fixture
def client(configured_env, clear_settings_cache):
    """Create a TestClient with env configured so app boots without errors."""
    from src.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_payload():
    """Minimal valid AgentScope Runtime /chat request payload."""
    return {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, reply with one word."}],
            }
        ]
    }


@pytest.fixture
def multi_turn_payload():
    """Multi-turn /chat request payload with 3 messages."""
    return {
        "input": [
            {"role": "user", "content": [{"type": "text", "text": "My name is Alice."}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Hello Alice!"}]},
            {"role": "user", "content": [{"type": "text", "text": "What is my name?"}]},
        ]
    }


@pytest.fixture
def config_override_payload():
    """Payload with agent_config override per D-03."""
    return {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, reply with one word."}],
            }
        ],
        "agent_config": {
            "model_name": "gpt-4o",
            "api_key": "sk-override-key",
            "base_url": "http://custom-api.example.com/v1",
        },
    }
