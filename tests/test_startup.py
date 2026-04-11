import pytest

# Fixtures configured_env and clear_settings_cache are provided by conftest.py


def test_startup_fails_when_MODEL_PROVIDER_missing(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)

    from fastapi.testclient import TestClient
    from src.main import app

    with pytest.raises(Exception) as exc_info:
        with TestClient(app):
            pass

    assert "MODEL_PROVIDER" in str(exc_info.value)


def test_startup_fails_when_MODEL_NAME_missing(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_NAME", raising=False)

    from fastapi.testclient import TestClient
    from src.main import app

    with pytest.raises(Exception) as exc_info:
        with TestClient(app):
            pass

    assert "MODEL_NAME" in str(exc_info.value)


def test_startup_fails_when_MODEL_API_KEY_missing(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    from fastapi.testclient import TestClient
    from src.main import app

    with pytest.raises(Exception) as exc_info:
        with TestClient(app):
            pass

    assert "MODEL_API_KEY" in str(exc_info.value)


def test_startup_fails_when_MODEL_BASE_URL_missing(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)

    from fastapi.testclient import TestClient
    from src.main import app

    with pytest.raises(Exception) as exc_info:
        with TestClient(app):
            pass

    assert "MODEL_BASE_URL" in str(exc_info.value)


def test_startup_succeeds_with_required_keys_and_cached_settings(configured_env, clear_settings_cache):
    from fastapi.testclient import TestClient
    from src.core.settings import get_settings
    from src.main import app

    with TestClient(app):
        pass

    settings_first = get_settings()
    settings_second = get_settings()
    assert settings_first is settings_second


def test_startup_path_does_not_depend_on_env_example_file(configured_env, clear_settings_cache, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from fastapi.testclient import TestClient
    from src.main import app

    with TestClient(app):
        pass

    assert not (tmp_path / ".env.example").exists()
