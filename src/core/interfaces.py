"""Framework-neutral runtime initialization contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config.schemas import (
    AgentConfig,
    MCPServerConfig,
    MemoryCompressionConfig,
    SkillConfig,
    SkillDownloadConfig,
    ToolConfig,
)


@dataclass(frozen=True)
class RuntimeSpec:
    """Framework-neutral runtime initialization settings."""

    runtime_id: str
    agent_config: AgentConfig | None = None
    memory_compression: MemoryCompressionConfig | None = None
    system_prompt: str | None = None
    tools: list[ToolConfig] = field(default_factory=list)
    skills: list[SkillConfig] = field(default_factory=list)
    skill_downloads: list[SkillDownloadConfig] = field(default_factory=list)
    skills_download_url: str | None = None
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
