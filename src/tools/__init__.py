"""Shared toolkit exports and legacy MCP client tracking."""

from agentscope.mcp import StdIOStatefulClient

from src.tools.registry import (
    TOOL_REGISTRY,
    ToolRegistryError,
    create_base_toolkit,
    register_configured_tools,
    register_default_tools,
    register_legacy_example_skill_support,
)

# Shared toolkit singleton (legacy compatibility path)
toolkit = create_base_toolkit(include_legacy_example_skill_support=True)

# Module-level list to track legacy startup MCP clients for LIFO shutdown
_mcp_clients: list[StdIOStatefulClient] = []

__all__ = [
    "TOOL_REGISTRY",
    "ToolRegistryError",
    "create_base_toolkit",
    "register_configured_tools",
    "register_default_tools",
    "register_legacy_example_skill_support",
    "toolkit",
    "_mcp_clients",
]
