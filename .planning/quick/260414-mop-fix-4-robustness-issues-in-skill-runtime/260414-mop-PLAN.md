---
quick_id: 260414-mop
description: Fix 4 robustness issues in skill runtime and query handler
date: 2026-04-14
---

# Quick Task Plan: Fix 4 Robustness Issues

## Plan 1: Skill Runtime & Query Handler Robustness Fixes

### Task 1: Fix make_python_file_runner subprocess crash
- **files**: `src/agent/skill_runtime.py`
- **action**: Change `check=True` to `check=False` in `subprocess.run()`. Add return-code check that returns a `ToolResponse` with stderr on non-zero exit instead of raising `CalledProcessError`.
- **verify**: Non-zero exit from a skill script returns error text in ToolResponse, not an exception.
- **done**: `make_python_file_runner` handles script failures gracefully.

### Task 2: Fix make_python_callable_runner error handling
- **files**: `src/agent/skill_runtime.py`
- **action**: Wrap `importlib.import_module` + `getattr` in try/except for `ImportError`, `AttributeError`, `ValueError`. Wrap `target(**kwargs)` call in try/except for `TypeError` and general `Exception`. Return `ToolResponse` error messages instead of letting exceptions propagate.
- **verify**: Invalid module/function targets and signature mismatches return error ToolResponse.
- **done**: `make_python_callable_runner` handles import and call failures gracefully.

### Task 3: Fix session state not saved on streaming error
- **files**: `src/agent/query.py`
- **action**: Wrap the `async for ... stream_printing_messages` + `save_session_state` block in `try/finally` so session state is persisted even when streaming raises an exception.
- **verify**: Session memory is saved regardless of streaming success or failure.
- **done**: `chat_query` saves session state in finally block.

### Task 4: Fix bootstrapped session agent_config error returns 500
- **files**: `src/agent/query.py`
- **action**: Change `raise RuntimeError(...)` to `raise ValueError(...)` when a bootstrapped session receives `agent_config` on `/process`. This produces a 400 Bad Request instead of 500 Internal Server Error.
- **verify**: Sending agent_config to a bootstrapped session returns 400, not 500.
- **done**: Error type changed to ValueError for proper HTTP status.
