"""Shared fixtures for Phase 2+ streaming contract tests."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.tools import _mcp_clients


@pytest.fixture(autouse=True)
def _mock_mcp_client():
    """Auto-mock MCP client for all tests to avoid subprocess dependency."""
    _mcp_clients.clear()
    with patch("src.app.lifespan.StdIOStatefulClient") as MockMCP:
        mock_client = AsyncMock()
        mock_client.name = "mock-mcp"
        MockMCP.return_value = mock_client
        yield
    _mcp_clients.clear()


@pytest.fixture
def configured_env(monkeypatch):
    """Set required env vars for settings loading and disable .env file."""
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_BASE_URL", "http://localhost:9999/v1")
    # Prevent .env file from providing fallback values during tests
    from src.core.settings import Settings

    monkeypatch.setattr(
        Settings,
        "model_config",
        {**Settings.model_config, "env_file": None},
    )


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
