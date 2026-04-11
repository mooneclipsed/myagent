"""Shared fixtures for Phase 2 streaming contract tests."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def configured_env(monkeypatch):
    """Set required env vars for settings loading."""
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_BASE_URL", "http://localhost:9999/v1")


@pytest.fixture
def clear_settings_cache():
    """Clear the lru_cache on get_settings before and after each test."""
    try:
        from src.core.settings import get_settings

        get_settings.cache_clear()
    except Exception:
        pass
    yield
    try:
        from src.core.settings import get_settings

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
    """Minimal valid /process request payload per D-01 and D-02."""
    return {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello, reply with one word."}],
            }
        ]
    }
