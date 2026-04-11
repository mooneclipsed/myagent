"""Request-scoped agent configuration with .env fallback.

Provides AgentConfig for per-request model overrides and
resolve_effective_config for field-level fallback to .env defaults.

Decisions: D-01 (minimally overridable), D-02 (field-level fallback),
D-04 (optional agent_config), D-06 (config trace logging).
"""

import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.core.settings import get_settings

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Per-request agent model configuration overrides.

    All fields are optional -- when omitted, resolve_effective_config
    falls back to the corresponding .env setting.

    extra="forbid" prevents unexpected fields from silently passing through.
    """

    model_config = ConfigDict(extra="forbid")

    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


def resolve_effective_config(agent_config: AgentConfig | None = None) -> dict:
    """Resolve effective model config by merging request overrides with .env defaults.

    Each field is resolved independently: if the request provides a value,
    it is used; otherwise the .env default is applied (D-02).

    Args:
        agent_config: Optional per-request config overrides.
            When None, all values come from .env (D-04).

    Returns:
        Dict with keys: model_name, api_key, base_url.
    """
    settings = get_settings()

    if agent_config is None:
        effective = {
            "model_name": settings.MODEL_NAME,
            "api_key": settings.MODEL_API_KEY,
            "base_url": settings.MODEL_BASE_URL,
        }
    else:
        effective = {
            "model_name": agent_config.model_name or settings.MODEL_NAME,
            "api_key": agent_config.api_key or settings.MODEL_API_KEY,
            "base_url": agent_config.base_url or settings.MODEL_BASE_URL,
        }

    # Config trace logging (D-06) -- NEVER log api_key values
    source = "request" if agent_config else "env"
    logger.info(
        "effective config: model_name=%s, base_url=%s, source=%s",
        effective["model_name"],
        effective["base_url"],
        source,
    )

    return effective
