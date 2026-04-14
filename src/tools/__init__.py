"""Shared Toolkit helpers with registered tools and legacy MCP client tracking.

Tools and skills are registered via helper functions so bootstrapped
session runtimes can create isolated toolkits without mutating the
module-level shared singleton used by the legacy `/process` flow.
"""

import logging
import os

from agentscope.mcp import StdIOStatefulClient
from agentscope.tool import Toolkit

from src.tools.examples import calculate, get_weather, run_platform_report

logger = logging.getLogger(__name__)

_example_skill_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "skills", "example_skill")
)


def register_default_tools(target_toolkit: Toolkit) -> None:
    """Register the built-in deterministic tool functions."""
    target_toolkit.register_tool_function(tool_func=get_weather, group_name="basic")
    target_toolkit.register_tool_function(tool_func=calculate, group_name="basic")
    target_toolkit.register_tool_function(
        tool_func=run_platform_report,
        group_name="basic",
    )


def register_default_skills(target_toolkit: Toolkit) -> None:
    """Register bundled agent skills when present."""
    if os.path.isdir(_example_skill_dir):
        target_toolkit.register_agent_skill(skill_dir=_example_skill_dir)
        logger.info("Example agent skill registered from %s", _example_skill_dir)


def create_base_toolkit() -> Toolkit:
    """Create a toolkit populated with the default tools and skills."""
    target_toolkit = Toolkit()
    register_default_tools(target_toolkit)
    register_default_skills(target_toolkit)
    return target_toolkit


# Shared toolkit singleton (legacy compatibility path)
toolkit = create_base_toolkit()

# Module-level list to track legacy startup MCP clients for LIFO shutdown
_mcp_clients: list[StdIOStatefulClient] = []
