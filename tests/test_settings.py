import pytest

REQUIRED_ENV_KEYS = (
    "MODEL_PROVIDER",
    "MODEL_NAME",
    "MODEL_API_KEY",
    "MODEL_BASE_URL",
)


@pytest.fixture
def configured_env(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_NAME", "gpt-4o-mini")
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://api.example.com/v1")


@pytest.fixture
def clear_settings_cache():
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
    assert settings_first.MODEL_NAME == "gpt-4o-mini"
    assert settings_first.MODEL_API_KEY == "test-key"
    assert settings_first.MODEL_BASE_URL == "https://api.example.com/v1"


def test_settings_loading_does_not_require_env_example_file(configured_env, clear_settings_cache, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from src.core.settings import get_settings

    settings = get_settings()

    assert settings.MODEL_PROVIDER == "openai"
    assert not (tmp_path / ".env.example").exists()
