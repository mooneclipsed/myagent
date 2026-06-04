"""Framework-neutral orchestration data models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .messages import StandardMessage

FrameworkName = Literal["agentscope"]
RuntimeStatus = Literal["initializing", "ready", "failed", "closed"]


class ModelConfig(BaseModel):
    """Model connection config used to build an agent spec."""

    model_config = ConfigDict(extra="forbid")

    model_name: str | None = None
    api_key: str | None = Field(default=None, exclude=True)
    base_url: str | None = Field(default=None, exclude=True)


class AgentSpec(BaseModel):
    """Immutable agent configuration resolved during runtime init."""

    model_config = ConfigDict(extra="forbid")

    model_config_: ModelConfig = Field(alias="model_config")
    system_prompt: str = Field(exclude=True)
    prompt_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceRef(BaseModel):
    """Public workspace reference."""

    model_config = ConfigDict(extra="forbid")

    root: str
    runtime_path: str


class StorageRef(BaseModel):
    """Public storage mode description."""

    model_config = ConfigDict(extra="forbid")

    type: str
    summary: str | None = None


class TraceRef(BaseModel):
    """Public tracing destination description."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    provider: str | None = None


class CapabilitySummary(BaseModel):
    """Public capability summary."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["tool", "mcp", "skill"]
    name: str
    status: Literal["loaded", "failed"] = "loaded"
    description: str | None = None


class RuntimeProfile(BaseModel):
    """Serializable public runtime profile."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    tenant_id: str | None = None
    framework: FrameworkName = "agentscope"
    agent_spec: AgentSpec
    capabilities: list[CapabilitySummary] = Field(default_factory=list)
    workspace: WorkspaceRef
    storage: StorageRef
    trace: TraceRef
    status: RuntimeStatus


class ExecutionConfig(BaseModel):
    """Request-scoped execution options."""

    model_config = ConfigDict(extra="forbid")

    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatInput(BaseModel):
    """First-version chat input with no conversation history."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    session_id: str
    input: str
    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig)


class RuntimeInitResult(BaseModel):
    """Public-safe runtime init response."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    framework: FrameworkName
    status: RuntimeStatus
    capabilities: list[CapabilitySummary] = Field(default_factory=list)
    workspace: WorkspaceRef
    storage: StorageRef
    tracing: TraceRef


class TurnResult(BaseModel):
    """Normalized completed turn result."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed", "interrupted"]
    message: StandardMessage | None = None

