"""Shared toolkit exports."""

from .registry import (
    TOOL_REGISTRY,
    ToolRegistryError,
    create_base_toolkit,
    get_skill_paths,
    get_tool_names,
    register_configured_tools,
    register_default_tools,
    register_legacy_example_skill_support,
)

# Shared toolkit singleton (legacy compatibility path)
toolkit = create_base_toolkit(include_legacy_example_skill_support=False)

__all__ = [
    "TOOL_REGISTRY",
    "ToolRegistryError",
    "create_base_toolkit",
    "get_skill_paths",
    "get_tool_names",
    "register_configured_tools",
    "register_default_tools",
    "register_legacy_example_skill_support",
    "toolkit",
]
