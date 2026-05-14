"""AgentScope agent construction helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import TextBlock
from agentscope.model import ChatResponse, OpenAIChatModel
from agentscope.model._model_base import ChatModelBase
from agentscope.token import OpenAITokenCounter
from agentscope.tool import Toolkit

from ...config.schemas import AgentModelConfig, MemoryCompressionConfig
from ...config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class CompressionFallbackModel(ChatModelBase):
    """Structured compression model with plain-text fallback for compatible APIs."""

    def __init__(self, model: OpenAIChatModel) -> None:
        super().__init__(model_name=model.model_name, stream=False)
        self.model = model

    async def __call__(self, messages: list[dict], structured_model=None, **kwargs: Any) -> ChatResponse:
        try:
            return await self.model(messages, structured_model=structured_model, **kwargs)
        except Exception as exc:
            if structured_model is None:
                raise
            logger.warning(
                "Structured memory compression failed; falling back to text summary: %s",
                exc,
            )
            response = await self.model(messages, **kwargs)
            text = _extract_text_response(response)
            metadata = _coerce_summary_metadata(text)
            return ChatResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=text,
                    ),
                ],
                usage=response.usage,
                metadata=metadata,
            )


def build_react_agent(
    resolved_config: AgentModelConfig,
    memory: InMemoryMemory,
    toolkit: Toolkit,
    system_prompt: str | None = None,
    memory_compression: MemoryCompressionConfig | None = None,
) -> ReActAgent:
    """Create a ReActAgent bound to the given memory and toolkit."""
    effective_system_prompt = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    settings = get_settings()
    formatter = OpenAIChatFormatter()
    compression_config = _build_compression_config(
        resolved_config=resolved_config,
        memory_compression=memory_compression,
    )
    logger.info(
        "Building ReActAgent: model=%s base_url=%s system_prompt_len=%d console_output=%s formatter=%s compression=%s",
        resolved_config.model_name,
        resolved_config.base_url,
        len(effective_system_prompt),
        settings.AGENT_CONSOLE_OUTPUT_ENABLED,
        type(formatter).__name__,
        bool(compression_config),
    )
    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=resolved_config.model_name,
            api_key=resolved_config.api_key,
            client_kwargs={"base_url": resolved_config.base_url},
            stream=True,
        ),
        sys_prompt=effective_system_prompt,
        formatter=formatter,
        memory=memory,
        toolkit=toolkit,
        compression_config=compression_config,
    )
    agent.set_console_output_enabled(
        enabled=settings.AGENT_CONSOLE_OUTPUT_ENABLED,
    )
    return agent


def _build_compression_config(
    resolved_config: AgentModelConfig,
    memory_compression: MemoryCompressionConfig | None = None,
) -> ReActAgent.CompressionConfig | None:
    """Resolve env/runtime settings into an AgentScope compression config."""
    settings = get_settings()
    enabled = (
        memory_compression.enabled
        if memory_compression and memory_compression.enabled is not None
        else settings.AGENT_MEMORY_COMPRESSION_ENABLED
    )
    if not enabled:
        return None

    trigger_tokens = (
        memory_compression.trigger_tokens
        if memory_compression and memory_compression.trigger_tokens is not None
        else settings.AGENT_MEMORY_COMPRESSION_TRIGGER_TOKENS
    )
    keep_recent = (
        memory_compression.keep_recent
        if memory_compression and memory_compression.keep_recent is not None
        else settings.AGENT_MEMORY_COMPRESSION_KEEP_RECENT
    )
    return ReActAgent.CompressionConfig(
        enable=True,
        agent_token_counter=OpenAITokenCounter(resolved_config.model_name),
        trigger_threshold=trigger_tokens,
        keep_recent=keep_recent,
        compression_model=CompressionFallbackModel(
            OpenAIChatModel(
                model_name=resolved_config.model_name,
                api_key=resolved_config.api_key,
                client_kwargs={"base_url": resolved_config.base_url},
                stream=False,
            ),
        ),
        compression_formatter=OpenAIChatFormatter(),
    )


def _extract_text_response(response: ChatResponse) -> str:
    texts = []
    for block in response.content:
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])
    return "\n".join(texts).strip()


def _coerce_summary_metadata(text: str) -> dict[str, str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    keys = [
        "task_overview",
        "current_state",
        "important_discoveries",
        "next_steps",
        "context_to_preserve",
    ]
    if isinstance(parsed, dict) and all(isinstance(parsed.get(key), str) for key in keys):
        return {key: parsed[key] for key in keys}

    fallback = text or "Previous conversation was compressed, but no textual summary was returned."
    return {
        "task_overview": fallback[:300],
        "current_state": fallback[:300],
        "important_discoveries": "",
        "next_steps": "",
        "context_to_preserve": fallback[:300],
    }
