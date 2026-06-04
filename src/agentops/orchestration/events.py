"""Platform event schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import FrameworkName, ModelConfig, TraceRef

EventName = Literal[
    "session_start",
    "session_restored",
    "session_end",
    "before_turn",
    "after_turn",
    "user_input_submit",
    "before_tool_call",
    "after_tool_call",
    "tool_error",
]


class EffectiveModel(BaseModel):
    """Non-secret model metadata emitted in events."""

    model_config = ConfigDict(extra="forbid")

    provider: str | None = None
    model_name: str
    base_url_host: str | None = None


class PlatformEvent(BaseModel):
    """SSE event envelope exposed by AgentOps."""

    model_config = ConfigDict(extra="forbid")

    event: EventName
    runtime_id: str
    tenant_id: str | None = None
    session_id: str
    request_id: str | None = None
    sequence: int = Field(ge=1)
    framework: FrameworkName
    effective_model: EffectiveModel
    prompt_hash: str
    trace_ref: TraceRef | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def effective_model_from_config(
    model_config: ModelConfig,
    *,
    provider: str | None = None,
    base_url_host: str | None = None,
) -> EffectiveModel:
    """Build non-secret event model metadata from model config."""
    return EffectiveModel(
        provider=provider,
        model_name=model_config.model_name or "",
        base_url_host=base_url_host,
    )

