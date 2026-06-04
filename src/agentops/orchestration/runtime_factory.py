"""Runtime manager assembly helpers."""

from __future__ import annotations

from pathlib import Path

from agentops.frameworks.agentscope_v2 import AgentScopeRuntimeBuilder
from agentops.frameworks.registry import resolve_framework

from .runtime_manager import RuntimeBuilder, RuntimeManager


def _create_runtime_builder(framework: str) -> RuntimeBuilder:
    """Create a runtime builder for a public framework name."""
    descriptor = resolve_framework(framework)
    if descriptor.name == "agentscope":
        return AgentScopeRuntimeBuilder()
    raise RuntimeError(f"Framework '{framework}' is registered without a runtime builder.")


def create_runtime_manager(
    *,
    framework: str = "agentscope",
    workspace_root: Path | str | None = None,
) -> RuntimeManager:
    """Create a runtime manager assembled with the framework runtime builder."""
    return RuntimeManager(
        workspace_root=workspace_root,
        builder=_create_runtime_builder(framework),
    )


runtime_manager = create_runtime_manager()
