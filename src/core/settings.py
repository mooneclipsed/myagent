from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MODEL_PROVIDER: str
    MODEL_NAME: str
    MODEL_API_KEY: str
    MODEL_BASE_URL: str
    SESSION_DIR: str = "./sessions"
    SESSION_BACKEND: str = "json"  # "json" or "redis" (D-03)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    STUDIO_URL: str | None = None
    AGENT_CONSOLE_OUTPUT_ENABLED: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
