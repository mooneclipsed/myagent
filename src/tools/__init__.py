"""Shared toolkit exports."""

from .registry import (
    TOOL_REGISTRY,
    ToolRegistryError,
    create_base_toolkit,
    register_configured_tools,
    register_default_tools,
    register_legacy_example_skill_support,
)

# Shared toolkit singleton (legacy compatibility path)
toolkit = create_base_toolkit(include_legacy_example_skill_support=True)

__all__ = [
    "TOOL_REGISTRY",
    "ToolRegistryError",
    "create_base_toolkit",
    "register_configured_tools",
    "register_default_tools",
    "register_legacy_example_skill_support",
    "toolkit",
]
