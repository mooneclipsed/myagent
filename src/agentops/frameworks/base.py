"""Framework adapter ports."""

from __future__ import annotations

from typing import Protocol

from agentops.orchestration.models import RuntimeProfile


class FrameworkRuntimePort(Protocol):
    """Port implemented by concrete framework runtimes."""

    async def close_runtime(self) -> None:
        """Close framework-owned runtime resources."""

    def describe_runtime(self) -> RuntimeProfile:
        """Return a public-safe runtime description."""

