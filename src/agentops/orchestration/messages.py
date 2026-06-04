"""Framework-neutral message schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MessageType = Literal[
    "user_message",
    "assistant_message",
    "tool_call",
    "tool_result",
    "error",
]
ContentPartType = Literal["text", "file_ref", "image_ref"]
ToolProvider = Literal["local", "mcp", "skill"]
ToolResultStatus = Literal["success", "failed"]


class ContentPart(BaseModel):
    """Portable message content part."""

    model_config = ConfigDict(extra="forbid")

    type: ContentPartType
    text: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageContentPayload(BaseModel):
    """Payload for user and assistant messages."""

    model_config = ConfigDict(extra="forbid")

    content: list[ContentPart]


class ToolCallPayload(BaseModel):
    """Payload for a normalized tool call."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str
    provider: ToolProvider
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultPayload(BaseModel):
    """Payload for a normalized tool result."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str | None = None
    name: str
    provider: ToolProvider
    status: ToolResultStatus
    content: list[ContentPart] = Field(default_factory=list)


class ErrorPayload(BaseModel):
    """Payload for a normalized error message."""

    model_config = ConfigDict(extra="forbid")

    code: str | None = None
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StandardMessage(BaseModel):
    """Framework-neutral message used for API and adapter conversion."""

    model_config = ConfigDict(extra="forbid")

    type: MessageType
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "StandardMessage":
        """Validate the payload according to the message type."""
        payload_model = _payload_model_for_type(self.type)
        payload_model.model_validate(self.payload)
        return self


def _payload_model_for_type(message_type: MessageType) -> type[BaseModel]:
    if message_type in ("user_message", "assistant_message"):
        return MessageContentPayload
    if message_type == "tool_call":
        return ToolCallPayload
    if message_type == "tool_result":
        return ToolResultPayload
    return ErrorPayload

