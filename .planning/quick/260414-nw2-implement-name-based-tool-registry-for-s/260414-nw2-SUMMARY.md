---
quick_id: 260414-nw2
description: Implement name-based tool registry for session bootstrap
date: 2026-04-14
status: complete
---

# Quick Task Summary: Name-Based Tool Registry

## Changes Made

### 1. `src/core/config.py` — New config/response models
- Added `ToolConfig(name: str)` for client-side tool requests
- Added `ToolSummary(name: str, description: str)` for bootstrap response
- Added `tools` field to `SessionBootstrapRequest` and `SessionBootstrapResponse`

### 2. `src/tools/__init__.py` — Local tool registry
- Added `TOOL_REGISTRY` dict mapping name → function (get_weather, calculate, run_platform_report, summarize_platform_callable)
- Added `ToolRegistryError(ValueError)` for unknown tool lookups
- Added `register_configured_tools(toolkit, tool_configs)` — validates all names (fail-fast), registers on toolkit, returns summaries

### 3. `src/agent/session_runtime.py` — Bootstrap wiring
- Replaced `create_base_toolkit(include_legacy_example_skill_support=False)` with bare `Toolkit()`
- Added `register_configured_tools()` call with `ToolRegistryError → SessionRuntimeValidationError` mapping (HTTP 400)
- Added `tool_summaries` field to `SessionRuntime` dataclass

### 4. `src/app/session_routes.py` — Response updated
- Bootstrap response now includes `tools=runtime.tool_summaries`

### 5. Tests — 8 new tests
- `test_tools.py`: TestToolRegistry (5 tests) — registry contents, callable check, registration success/empty/failure
- `test_session_bootstrap.py`: 3 integration tests — tools bootstrap success, unknown tool 400, empty tools OK

## Test Results

80/80 tests passed. All existing tests unaffected. Legacy path unchanged.
