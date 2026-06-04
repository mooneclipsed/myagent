"""Observability metadata helpers."""

from __future__ import annotations

from hashlib import sha256
from urllib.parse import urlparse


def hash_system_prompt(system_prompt: str) -> str:
    """Return a stable non-secret hash for a system prompt."""
    digest = sha256(system_prompt.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def base_url_host(base_url: str | None) -> str | None:
    """Return only the host component of a base URL."""
    if not base_url:
        return None
    parsed = urlparse(base_url)
    return parsed.netloc or parsed.path or None

