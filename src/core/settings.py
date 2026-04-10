from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MODEL_PROVIDER: str
    MODEL_NAME: str
    MODEL_API_KEY: str
    MODEL_BASE_URL: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
