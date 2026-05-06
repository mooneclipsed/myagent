import pytest

# Fixtures configured_env and clear_settings_cache are provided by conftest.py


def test_missing_MODEL_PROVIDER_raises_validation_error(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)

    from src.core.settings import get_settings

    with pytest.raises(Exception) as exc_info:
        get_settings()

    assert "MODEL_PROVIDER" in str(exc_info.value)


def test_missing_MODEL_NAME_raises_validation_error(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_NAME", raising=False)

    from src.core.settings import get_settings

    with pytest.raises(Exception) as exc_info:
        get_settings()

    assert "MODEL_NAME" in str(exc_info.value)


def test_missing_MODEL_API_KEY_raises_validation_error(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    from src.core.settings import get_settings

    with pytest.raises(Exception) as exc_info:
        get_settings()

    assert "MODEL_API_KEY" in str(exc_info.value)


def test_missing_MODEL_BASE_URL_raises_validation_error(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)

    from src.core.settings import get_settings

    with pytest.raises(Exception) as exc_info:
        get_settings()

    assert "MODEL_BASE_URL" in str(exc_info.value)


def test_get_settings_loads_values_once_with_all_required_keys(configured_env, clear_settings_cache):
    from src.core.settings import get_settings

    settings_first = get_settings()
    settings_second = get_settings()

    assert settings_first is settings_second
    assert settings_first.MODEL_PROVIDER == "openai"
    assert settings_first.MODEL_NAME == "test-model"
    assert settings_first.MODEL_API_KEY == "test-key"
    assert settings_first.MODEL_BASE_URL == "http://localhost:9999/v1"
    assert settings_first.STUDIO_ENABLED is False
    assert settings_first.AGENT_CONSOLE_OUTPUT_ENABLED is False


def test_settings_loading_does_not_require_env_example_file(configured_env, clear_settings_cache, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from src.core.settings import get_settings

    settings = get_settings()

    assert settings.MODEL_PROVIDER == "openai"
    assert not (tmp_path / ".env.example").exists()
