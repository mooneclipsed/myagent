"""HTTP API schemas for the refactor-v2 contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from agentops.capabilities.v2_models import CapabilitySpec
from agentops.orchestration.models import (
    ChatInput,
    ExecutionConfig,
    FrameworkName,
    ModelConfig,
    RuntimeInitResult,
)


class RuntimeInitRequest(BaseModel):
    """HTTP request for initializing a runtime profile."""

    model_config = ConfigDict(extra="forbid")

    runtime_id: str
    tenant_id: str | None = None
    framework: FrameworkName = "agentscope"
    model_config_: ModelConfig | None = Field(default=None, alias="model_config")
    system_prompt: str | None = None
    capabilities: list[CapabilitySpec] = Field(default_factory=list)


class RuntimeInitResponse(RuntimeInitResult):
    """HTTP response for initialized runtime profile."""


class ChatRequest(ChatInput):
    """HTTP request for one chat turn."""

    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig)

