"""Shared Toolkit helpers with registered tools and legacy MCP client tracking.

Tools and skills are registered via helper functions so bootstrapped
session runtimes can create isolated toolkits without mutating the
module-level shared singleton used by the legacy `/process` flow.
"""

import logging
import os

from agentscope.mcp import StdIOStatefulClient
from agentscope.tool import Toolkit

from src.core.config import ToolConfig, ToolSummary
from src.tools.examples import calculate, get_weather, run_platform_report, summarize_platform_callable

logger = logging.getLogger(__name__)

_example_skill_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "skills", "example_skill")
)


def register_default_tools(target_toolkit: Toolkit) -> None:
    """Register the built-in deterministic tool functions."""
    target_toolkit.register_tool_function(tool_func=get_weather, group_name="basic")
    target_toolkit.register_tool_function(tool_func=calculate, group_name="basic")


def register_legacy_example_skill_support(target_toolkit: Toolkit) -> None:
    """Register the bundled example skill and its legacy script tool."""
    target_toolkit.register_tool_function(
        tool_func=run_platform_report,
        group_name="basic",
    )
    if os.path.isdir(_example_skill_dir):
        target_toolkit.register_agent_skill(skill_dir=_example_skill_dir)
        logger.info("Example agent skill registered from %s", _example_skill_dir)


def create_base_toolkit(*, include_legacy_example_skill_support: bool = True) -> Toolkit:
    """Create a toolkit populated with the default tools and optional legacy example skill support."""
    target_toolkit = Toolkit()
    register_default_tools(target_toolkit)
    if include_legacy_example_skill_support:
        register_legacy_example_skill_support(target_toolkit)
    return target_toolkit


# Shared toolkit singleton (legacy compatibility path)
toolkit = create_base_toolkit(include_legacy_example_skill_support=True)

# Module-level list to track legacy startup MCP clients for LIFO shutdown
_mcp_clients: list[StdIOStatefulClient] = []

# ---------------------------------------------------------------------------
# Name-based tool registry for session bootstrap
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "get_weather": get_weather,
    "calculate": calculate,
    "run_platform_report": run_platform_report,
    "summarize_platform_callable": summarize_platform_callable,
}


class ToolRegistryError(ValueError):
    """Raised when a requested tool name is not found in the local registry."""


def register_configured_tools(
    target_toolkit: Toolkit,
    tool_configs: list[ToolConfig],
) -> list[ToolSummary]:
    """Register requested tools on a session-owned toolkit by name lookup.

    Validates all names before registering any (fail-fast). Returns summaries.
    Raises ToolRegistryError if any requested tool name is not in TOOL_REGISTRY.
    """
    unknown = [tc.name for tc in tool_configs if tc.name not in TOOL_REGISTRY]
    if unknown:
        raise ToolRegistryError(
            f"Unknown tool(s) requested: {', '.join(unknown)}. "
            f"Available: {', '.join(sorted(TOOL_REGISTRY.keys()))}"
        )

    summaries: list[ToolSummary] = []
    for tc in tool_configs:
        func = TOOL_REGISTRY[tc.name]
        target_toolkit.register_tool_function(tool_func=func, group_name="basic")
        description = (func.__doc__ or "").strip().split("\n")[0]
        summaries.append(ToolSummary(name=tc.name, description=description))

    return summaries
