---
quick_id: 260414-mop
description: Fix 4 robustness issues in skill runtime and query handler
date: 2026-04-14
status: complete
---

# Quick Task Summary: Fix 4 Robustness Issues

## Changes Made

### 1. `src/agent/skill_runtime.py` — make_python_file_runner
- Changed `subprocess.run(..., check=True)` to `check=False`
- Added return-code check: non-zero exit now returns a `ToolResponse` with stderr instead of raising `CalledProcessError`

### 2. `src/agent/skill_runtime.py` — make_python_callable_runner
- Wrapped `importlib.import_module` + `getattr` in try/except for `ValueError`, `ImportError`, `AttributeError`
- Invalid target format (missing `:`) now returns an error ToolResponse instead of crashing
- Wrapped `target(**kwargs)` in try/except to catch `TypeError` and other runtime errors gracefully

### 3. `src/agent/query.py` — session state persistence
- Wrapped streaming + save logic in `try/finally` so session state is saved even when streaming raises an exception
- Added logging for save failures to avoid masking the original streaming error

### 4. `src/agent/query.py` — error type for bootstrapped sessions
- Changed `raise RuntimeError(...)` to `raise ValueError(...)` when a bootstrapped session receives `agent_config` on `/process`
- This produces a 400 Bad Request instead of 500 Internal Server Error

## Test Results

66/66 tests passed. One pre-existing test failure in `test_agent_config.py` (incorrect mock path for `OpenAIChatModel`) is unrelated to these changes.
