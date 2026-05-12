"""Tool, skill, and MCP capability declaration models."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolConfig(BaseModel):
    """Bootstrap configuration for a named tool from the local registry."""

    model_config = ConfigDict(extra="forbid")

    name: str


class SkillConfig(BaseModel):
    """Bootstrap configuration for a dynamic skill bundle."""

    model_config = ConfigDict(extra="forbid")

    skill_dir: str


class SkillDownloadConfig(BaseModel):
    """Bootstrap declaration for a remotely managed skill version."""

    model_config = ConfigDict(extra="forbid")

    skill_id: int = Field(gt=0)
    version_id: int = Field(gt=0)


class SkillDownloadSummary(BaseModel):
    """Result summary for a remotely managed skill install attempt."""

    model_config = ConfigDict(extra="forbid")

    skill_id: int
    version_id: int
    status: Literal["kept", "installed", "failed", "removed"]
    skill_dir: str | None = None
    zip_path: str | None = None
    error: str | None = None


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
    structured_tools: list[str] = Field(default_factory=list)
