---
quick_id: 260415-n2v
description: Refactor tool registration wiring by extracting registry management out of src/tools/__init__.py into a dedicated module under src/tools/ while keeping current bootstrap and name-based registry behavior unchanged.
date: 2026-04-15
status: complete
---

# Quick Task Summary: Tool Registration Wiring Extraction

## Changes Made

### 1. `src/tools/registry.py` — New canonical registry module
- Moved tool registration helpers out of `src/tools/__init__.py`
- `register_default_tools()`, `register_legacy_example_skill_support()`, and `create_base_toolkit()` now live here
- `TOOL_REGISTRY`, `ToolRegistryError`, and `register_configured_tools()` now live here as the single source of truth for name-based bootstrap registration

### 2. `src/tools/__init__.py` — Thin package entrypoint
- Reduced the package entrypoint to imports/re-exports from `src.tools.registry`
- Kept the shared singleton `toolkit` in place for the legacy `/process` path
- Kept `_mcp_clients` in place for legacy startup MCP lifecycle tracking
- Preserved the existing `from src.tools import ...` import surface for current callers

### 3. `tests/test_tools.py` — Extraction-safe regression coverage
- Added assertions that registry helpers are importable directly from `src.tools.registry`
- Added assertions that `src.tools` continues to re-export the same registry objects
- Added a focused `create_base_toolkit()` regression check for default-tool behavior

## Validation

### Targeted tests passed
- `uv run pytest tests/test_tools.py::TestToolRegistry tests/test_session_bootstrap.py::test_bootstrap_with_tools_registers_requested_tools tests/test_session_bootstrap.py::test_bootstrap_rejects_unknown_tool_name tests/test_session_bootstrap.py::test_bootstrap_with_empty_tools_succeeds -x -v`
- Result: `10 passed`

### Notes
- The broader `tests/test_tools.py tests/test_session_bootstrap.py tests/test_skill_runtime.py` suite is currently blocked by pre-existing deletions in `skills/example_skill/` on this branch, not by this refactor.
- No bootstrap wiring or consumer imports needed to change.
