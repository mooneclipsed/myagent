"""Request-scoped and session-bootstrap configuration with .env fallback.

Provides AgentConfig for per-request model overrides,
MCP bootstrap request/response models, skill bootstrap models, and
resolve_effective_config for field-level fallback to .env defaults.

Decisions: D-01 (minimally overridable), D-02 (field-level fallback),
D-04 (optional request config), D-06 (config trace logging).
"""

import logging
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.settings import get_settings

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Per-request agent model configuration overrides."""

    model_config = ConfigDict(extra="forbid")

    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class SkillScriptConfig(BaseModel):
    """Structured script capability declared by a skill bundle."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal["python_callable", "python_file"]
    description: str
    execution_mode: Literal["direct", "shell"]
    expose: Literal["lazy", "eager"] = "lazy"
    structured_tool: bool = True
    target: str | None = None
    entrypoint: str | None = None
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
        }
    )

    @model_validator(mode="after")
    def validate_kind_specific_fields(self):
        if self.kind == "python_callable" and not self.target:
            raise ValueError("python_callable script requires target")
        if self.kind == "python_file" and not self.entrypoint:
            raise ValueError("python_file script requires entrypoint")
        return self


class ToolConfig(BaseModel):
    """Bootstrap configuration for a named tool from the local registry."""

    model_config = ConfigDict(extra="forbid")

    name: str


class SkillConfig(BaseModel):
    """Bootstrap configuration for a dynamic skill bundle."""

    model_config = ConfigDict(extra="forbid")

    skill_dir: str
    activation_mode: Literal["lazy", "eager"] = "lazy"
    expose_structured_tools: bool = True


class _BaseMCPServerConfig(BaseModel):
    """Shared MCP server configuration fields."""

    model_config = ConfigDict(extra="forbid")

    name: str


class StdioMCPServerConfig(_BaseMCPServerConfig):
    """Bootstrap configuration for stdio MCP servers."""

    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str] | None = None
    env: dict[str, str] | None = None
    cwd: str | None = None


class HttpMCPServerConfig(_BaseMCPServerConfig):
    """Bootstrap configuration for stateful HTTP MCP servers."""

    type: Literal["http"] = "http"
    transport: Literal["sse", "streamable_http"]
    url: str
    headers: dict[str, str] | None = None
    timeout: float = 30
    sse_read_timeout: float = 60 * 5


MCPServerConfig = Annotated[
    StdioMCPServerConfig | HttpMCPServerConfig,
    Field(discriminator="type"),
]


class MCPServerSummary(BaseModel):
    """Normalized MCP server summary returned from bootstrap."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["stdio", "http"]
    transport: Literal["sse", "streamable_http"] | None = None


class ToolSummary(BaseModel):
    """Normalized tool summary returned from bootstrap."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str


class SkillSummary(BaseModel):
    """Normalized skill summary returned from bootstrap."""

    model_config = ConfigDict(extra="forbid")

    name: str
    activation_mode: Literal["lazy", "eager"]
    structured_tools: list[str] = Field(default_factory=list)


class SessionBootstrapRequest(BaseModel):
    """Bootstrap request for creating a session-scoped agent runtime."""

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    agent_config: AgentConfig | None = None
    system_prompt: str | None = None
    tools: list[ToolConfig] = Field(default_factory=list)
    skills: list[SkillConfig] = Field(default_factory=list)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)


class SessionBootstrapResponse(BaseModel):
    """Bootstrap response for a ready session runtime."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    status: Literal["ready"] = "ready"
    tools: list[ToolSummary] = Field(default_factory=list)
    skills: list[SkillSummary] = Field(default_factory=list)
    mcp_servers: list[MCPServerSummary] = Field(default_factory=list)


class SessionShutdownResponse(BaseModel):
    """Response returned after closing a bootstrapped session runtime."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    status: Literal["closed"] = "closed"


def resolve_effective_config(agent_config: AgentConfig | None = None) -> dict:
    """Resolve effective model config by merging request overrides with .env defaults."""
    settings = get_settings()

    if agent_config is None:
        effective = {
            "model_name": settings.MODEL_NAME,
            "api_key": settings.MODEL_API_KEY,
            "base_url": settings.MODEL_BASE_URL,
        }
    else:
        effective = {
            "model_name": agent_config.model_name or settings.MODEL_NAME,
            "api_key": agent_config.api_key or settings.MODEL_API_KEY,
            "base_url": agent_config.base_url or settings.MODEL_BASE_URL,
        }

    source = "request" if agent_config else "env"
    logger.info(
        "effective config: model_name=%s, base_url=%s, source=%s",
        effective["model_name"],
        effective["base_url"],
        source,
    )

    return effective
