"""Framework-neutral capability declaration schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CapabilityType = Literal["tool", "mcp", "skill"]
MCPTransport = Literal["stdio", "sse", "streamable_http"]


class ToolCapabilityConfig(BaseModel):
    """Config for a local or native tool capability."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str


class MCPCapabilityConfig(BaseModel):
    """Config for an MCP server capability."""

    model_config = ConfigDict(extra="forbid")

    transport: MCPTransport
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: float = 30


class SkillCapabilityConfig(BaseModel):
    """Config for loading local skills from the project skill root."""

    model_config = ConfigDict(extra="forbid")

    path: str = ".skills/"


class CapabilitySpec(BaseModel):
    """Capability envelope with strict per-type config validation."""

    model_config = ConfigDict(extra="forbid")

    type: CapabilityType
    name: str
    enabled: bool = True
    config: dict[str, Any]

    @model_validator(mode="after")
    def validate_config(self) -> "CapabilitySpec":
        """Validate the config according to the capability type."""
        config_model = _config_model_for_type(self.type)
        config_model.model_validate(self.config)
        return self


def _config_model_for_type(capability_type: CapabilityType) -> type[BaseModel]:
    if capability_type == "tool":
        return ToolCapabilityConfig
    if capability_type == "mcp":
        return MCPCapabilityConfig
    return SkillCapabilityConfig

