# Plan 01 Summary: Register Tools, MCP Server, and Integrate into Agent Lifecycle

**Phase:** 04-capability-invocation-tracing
**Plan:** 01
**Status:** Complete
**Commit:** e14f2cd

## What Was Done

1. Created `src/tools/examples.py` with `get_weather` and `calculate` tool functions returning `ToolResponse`
2. Created `src/tools/__init__.py` with shared `Toolkit` singleton registering both tools at import time
3. Created `src/mcp/server.py` with local MCP server providing `get_time` tool via stdio transport
4. Created `src/mcp/__init__.py` as package init
5. Updated `src/app/lifespan.py` with MCP client lifecycle (connect at startup, LIFO close on shutdown)
6. Updated `src/agent/query.py` to pass `toolkit=toolkit` to each per-request ReActAgent
7. Updated `tests/conftest.py` with `autouse` MCP mock fixture for all tests

## Deviations from Plan

- `toolkit.tool_functions` → `toolkit.tools` (actual framework API)
- MCP server `list_tools` returns `Tool` objects (not plain dicts) to fix `'dict' object has no attribute 'name'` error
- MCP server `call_tool` returns `TextContent` objects (not plain dicts)
- Added `autouse` MCP mock fixture in conftest instead of per-fixture mock (fixes tests that create TestClient directly)

## Verification

- All 23 existing tests pass (zero regressions)
- Toolkit imports and registers 2 tools correctly
- MCP server module imports cleanly
- Lifespan and query handler imports succeed
