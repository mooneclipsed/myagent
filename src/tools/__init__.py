"""Shared Toolkit singleton with registered tools and MCP client.

Tools are registered at import time (D-02: startup-time registration).
MCP clients are registered in lifespan after async connection.
The toolkit is passed to each per-request ReActAgent in query.py.
"""

import logging
import os

from agentscope.mcp import StdIOStatefulClient
from agentscope.tool import Toolkit

from src.tools.examples import calculate, get_weather

logger = logging.getLogger(__name__)

# Shared toolkit singleton (D-02: all requests share same tools)
toolkit = Toolkit()

# Register example tool functions at import time per D-01 (framework-native)
toolkit.register_tool_function(tool_func=get_weather, group_name="basic")
toolkit.register_tool_function(tool_func=calculate, group_name="basic")

# Phase 8 D-01: Register example agent skill (distinct from tool functions)
_example_skill_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "skills", "example_skill")
)
if os.path.isdir(_example_skill_dir):
    toolkit.register_agent_skill(skill_dir=_example_skill_dir)
    logger.info("Example agent skill registered from %s", _example_skill_dir)

# Module-level list to track MCP clients for LIFO shutdown
_mcp_clients: list[StdIOStatefulClient] = []
