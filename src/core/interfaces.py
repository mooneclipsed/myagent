"""Framework-neutral runtime interface and chat data contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..config.schemas import (
    AgentConfig,
    MCPServerConfig,
    MemoryCompressionConfig,
    SkillConfig,
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
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)


@dataclass(frozen=True)
class ChatMessage:
    """Framework-neutral chat message."""

    role: str
    content: Any
    name: str | None = None


@dataclass(frozen=True)
class ChatRequest:
    """Framework-neutral chat execution request."""

    messages: list[ChatMessage]
    runtime_id: str | None = None
    session_id: str | None = None
    agent_config: AgentConfig | None = None


@dataclass(frozen=True)
class ChatEvent:
    """Framework-neutral streamed chat event."""

    role: str
    name: str | None
    content: Any
    last: bool = False
    text: str | None = None


class AgentRuntime(Protocol):
    """Interface implemented by concrete agent framework runtimes."""

    async def initialize(self, spec: RuntimeSpec) -> Any:
        """Initialize framework-specific runtime resources."""

    async def chat(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        """Stream a chat response for a request."""

    async def reload(self, spec: RuntimeSpec) -> Any:
        """Reload runtime resources from a new spec."""

    async def shutdown(self, runtime_id: str) -> None:
        """Shutdown framework-specific runtime resources."""

