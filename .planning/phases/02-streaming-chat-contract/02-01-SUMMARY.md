---
phase: 02-streaming-chat-contract
plan: 01
subsystem: api
tags: [agentscope-runtime, sse, streaming, fastapi, react-agent]

# Dependency graph
requires:
  - phase: 01-environment-workflow-baseline
    provides: FastAPI app with lifespan, typed settings from .env, uv project management
provides:
  - AgentApp replacing bare FastAPI as the service entry point
  - /process POST endpoint with SSE streaming via @app.query decorator
  - ReActAgent with OpenAIChatModel per-request agent creation pattern
  - stream_printing_messages async generator bridge to SSE events
affects: [02-02, streaming-chat-contract, session-persistence]

# Tech tracking
tech-stack:
  added: [agentscope-runtime==1.1.3, agentscope==1.0.18, openai, sse-starlette, dashscope, a2a-sdk, ag-ui-protocol]
  patterns: [AgentApp as FastAPI subclass, @app.query decorator for SSE, ReActAgent per-request, client_kwargs for base_url]

key-files:
  created:
    - src/agent/__init__.py
    - src/agent/query.py
  modified:
    - src/main.py
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Removed explicit fastapi/pydantic/uvicorn pins to let agentscope-runtime manage transitive dependency versions"
  - "Created both agent files together since __init__.py imports query.py and main.py imports agent package -- all needed for tests to pass"
  - "Used client_kwargs for base_url on OpenAIChatModel per research finding (Pitfall 4)"

patterns-established:
  - "AgentApp entry point: src/main.py instantiates AgentApp with app_name, app_description, lifespan"
  - "Query handler registration: @app.query(framework='agentscope') decorator on async generator in src/agent/query.py"
  - "Per-request agent creation: fresh ReActAgent + OpenAIChatModel + InMemoryMemory per query"
  - "Console output disabled: agent.set_console_output_enabled(enabled=False) to prevent noisy stdout"

requirements-completed: [CORE-01]

# Metrics
duration: 3min
completed: 2026-04-11
---

# Phase 02 Plan 01: AgentApp Streaming Infrastructure Summary

**AgentApp replacing bare FastAPI with SSE /process endpoint using agentscope-runtime @app.query decorator and ReActAgent**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-11T08:46:17Z
- **Completed:** 2026-04-11T08:50:04Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Replaced bare FastAPI with AgentApp from agentscope-runtime -- service boots and inherits all FastAPI capabilities
- Registered /process POST endpoint with SSE streaming via @app.query(framework="agentscope") decorator
- All 12 Phase 1 tests pass without modification (settings validation, startup behavior preserved)
- Dependency resolution clean: agentscope-runtime==1.1.3 resolves fastapi==0.135.3, pydantic==2.12.5, uvicorn==0.44.0 transitively

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Update dependencies, replace FastAPI with AgentApp, create SSE streaming query handler** - `ea02a27` (feat)

_Note: Tasks 1 and 2 were combined into a single commit because Task 1's main.py imports src.agent which requires query.py from Task 2 to exist for the import chain to resolve. Both tasks form an atomic unit._

## Files Created/Modified
- `pyproject.toml` - Removed conflicting fastapi/pydantic/uvicorn pins, added agentscope-runtime==1.1.3 and pydantic-settings>=2.0
- `src/main.py` - Replaced FastAPI() with AgentApp(app_name, app_description, lifespan) + agent package import
- `src/agent/__init__.py` - Package init that imports query module to trigger handler registration
- `src/agent/query.py` - @app.query SSE streaming handler with ReActAgent, OpenAIChatModel, stream_printing_messages
- `uv.lock` - Updated lockfile with 135 resolved packages (was ~20)

## Decisions Made
- Combined Task 1 and Task 2 into single commit because the import chain (main.py -> src.agent -> src.agent.query) requires all files to exist for tests to pass
- Used pydantic-settings>=2.0 (not pinned) since agentscope-runtime manages pydantic version transitively
- Kept dev dependencies (httpx, pytest) with exact pins for reproducibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Combined Task 1 and Task 2 commits**
- **Found during:** Task 1 (Update dependencies and replace FastAPI)
- **Issue:** main.py imports src.agent which imports src.agent.query -- both files must exist for the import chain to resolve and Phase 1 tests to pass
- **Fix:** Created all files (main.py, __init__.py, query.py) together in a single commit
- **Files modified:** src/main.py, src/agent/__init__.py, src/agent/query.py
- **Verification:** uv run pytest tests/ -x -q passes (12/12), /process endpoint registered
- **Committed in:** ea02a27

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor -- combined two atomic commits into one due to import chain dependency. No scope creep.

## Issues Encountered
- agentscope-runtime logs INFO/WARNING messages on import (Celery fallback, Nacos SDK, LocalInterruptBackend) -- these are harmless and expected for optional integrations not configured in this phase

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AgentApp service boots and /process endpoint is registered
- Ready for Plan 02-02: streaming contract tests (SSE lifecycle events, validation errors, repeated request stability)
- The /process endpoint accepts POST with `{"input": [{"role": "user", "content": [{"type": "text", "text": "..."}]}]}` format
- Health endpoints auto-registered: /health, /, /shutdown, /admin/status

## Self-Check: PASSED

- FOUND: src/agent/__init__.py
- FOUND: src/agent/query.py
- FOUND: src/main.py
- FOUND: pyproject.toml
- FOUND: uv.lock
- FOUND: ea02a27

---
*Phase: 02-streaming-chat-contract*
*Completed: 2026-04-11*
