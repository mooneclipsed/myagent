from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    model_provider: str = Field(default="openai", alias="MODEL_PROVIDER")
    model_name: str = Field(alias="MODEL_NAME")
    model_api_key: str = Field(alias="MODEL_API_KEY")
    model_base_url: str = Field(alias="MODEL_BASE_URL")
    port: int = Field(default=8000, alias="PORT")
    session_dir: str = Field(default="./sessions", alias="SESSION_DIR")
    session_backend: str = Field(default="json", alias="SESSION_BACKEND")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    studio_enabled: bool = Field(default=False, alias="STUDIO_ENABLED")
    studio_url: str | None = Field(default=None, alias="STUDIO_URL")
    agent_console_output_enabled: bool = Field(default=False, alias="AGENT_CONSOLE_OUTPUT_ENABLED")
    agent_memory_compression_enabled: bool = Field(default=False, alias="AGENT_MEMORY_COMPRESSION_ENABLED")
    agent_memory_compression_trigger_tokens: int = Field(
        default=60000,
        alias="AGENT_MEMORY_COMPRESSION_TRIGGER_TOKENS",
    )
    agent_memory_compression_keep_recent: int = Field(
        default=8,
        alias="AGENT_MEMORY_COMPRESSION_KEEP_RECENT",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
