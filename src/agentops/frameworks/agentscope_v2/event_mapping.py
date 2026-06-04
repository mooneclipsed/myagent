"""Map AgentScope v2 stream events to AgentOps platform events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentscope.event import ReplyEndEvent, ReplyStartEvent, TextBlockDeltaEvent

from agentops.orchestration.events import PlatformEvent, effective_model_from_config
from agentops.orchestration.models import RuntimeProfile
from agentops.orchestration.observability import base_url_host


@dataclass
class PlatformEventMapper:
    """Convert AgentScope v2 events into platform events."""

    profile: RuntimeProfile
    session_id: str
    request_id: str | None = None
    sequence: int = 0

    def map_event(self, event: Any) -> PlatformEvent | None:
        """Map one AgentScope event to one platform event when supported."""
        if isinstance(event, ReplyStartEvent):
            return self._next_event(
                event="before_turn",
                payload={
                    "framework_event": "reply_start",
                    "reply_id": event.reply_id,
                    "agent_name": event.name,
                },
            )
        if isinstance(event, TextBlockDeltaEvent):
            return self._next_event(
                event="after_turn",
                payload={
                    "status": "streaming",
                    "framework_event": "text_block_delta",
                    "reply_id": event.reply_id,
                    "block_id": event.block_id,
                    "delta": event.delta,
                },
            )
        if isinstance(event, ReplyEndEvent):
            return self._next_event(
                event="after_turn",
                payload={
                    "status": "completed",
                    "framework_event": "reply_end",
                    "reply_id": event.reply_id,
                },
            )
        return None

    def _next_event(self, *, event: str, payload: dict[str, Any]) -> PlatformEvent:
        self.sequence += 1
        return PlatformEvent(
            event=event,
            runtime_id=self.profile.runtime_id,
            tenant_id=self.profile.tenant_id,
            session_id=self.session_id,
            request_id=self.request_id,
            sequence=self.sequence,
            framework=self.profile.framework,
            effective_model=effective_model_from_config(
                self.profile.agent_spec.model_config_,
                base_url_host=base_url_host(self.profile.agent_spec.model_config_.base_url),
            ),
            prompt_hash=self.profile.agent_spec.prompt_hash,
            trace_ref=self.profile.trace,
            payload=payload,
        )
