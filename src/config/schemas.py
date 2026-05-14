"""Request-scoped and runtime initialization configuration with .env fallback.

Provides AgentConfig for per-request model overrides,
MCP runtime request/response models, skill runtime models, and
resolve_agent_model_config for field-level fallback to .env defaults.

Decisions: D-01 (minimally overridable), D-02 (field-level fallback),
D-04 (optional request config), D-06 (config trace logging).
"""

import logging
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..capabilities.schemas import (
    MCPServerConfig,
    MCPServerSummary,
    SkillConfig,
    SkillDownloadConfig,
    SkillDownloadSummary,
    SkillSummary,
    ToolConfig,
    ToolSummary,
)

from .settings import get_settings

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Per-request agent model configuration overrides."""

    model_config = ConfigDict(extra="forbid")

    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class AgentModelConfig(BaseModel):
    """Fully resolved agent model configuration."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    api_key: str
    base_url: str


class MemoryCompressionConfig(BaseModel):
    """Runtime memory compression settings for AgentScope ReActAgent."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    trigger_tokens: int | None = Field(default=None, gt=0)
    keep_recent: int | None = Field(default=None, ge=1)


class RuntimeInitializeRequest(BaseModel):
    """Request for creating a runtime profile."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    agent_config: AgentConfig | None = None
    memory_compression: MemoryCompressionConfig | None = None
    system_prompt: str | None = None
    tools: list[ToolConfig] = Field(default_factory=list)
    skills: list[SkillConfig] = Field(default_factory=list)
    skill_downloads: list[SkillDownloadConfig] = Field(default_factory=list)
    skills_download_url: str | None = None
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)

    @field_validator("runtime_id", mode="before")
    @classmethod
    def coerce_runtime_id(cls, value: object) -> object:
        if isinstance(value, int):
            return str(value)
        return value


class RuntimeProfileResponse(BaseModel):
    """Response for a ready runtime profile."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    status: Literal["ready"] = "ready"
    tools: list[ToolSummary] = Field(default_factory=list)
    skills: list[SkillSummary] = Field(default_factory=list)
    skill_downloads: list[SkillDownloadSummary] = Field(default_factory=list)
    mcp_servers: list[MCPServerSummary] = Field(default_factory=list)


def resolve_agent_model_config(agent_config: AgentConfig | None = None) -> AgentModelConfig:
    """Resolve effective model config by merging request overrides with .env defaults."""
    settings = get_settings()

    if agent_config is None:
        effective = AgentModelConfig(
            model_name=settings.model_name,
            api_key=settings.model_api_key,
            base_url=settings.model_base_url,
        )
    else:
        effective = AgentModelConfig(
            model_name=agent_config.model_name or settings.model_name,
            api_key=agent_config.api_key or settings.model_api_key,
            base_url=agent_config.base_url or settings.model_base_url,
        )

    source = "request" if agent_config else "env"
    logger.info(
        "effective config: model_name=%s, base_url=%s, source=%s",
        effective.model_name,
        effective.base_url,
        source,
    )

    return effective
