---
phase: "07-redis-session-persistence"
plan: "01"
subsystem: session-persistence
tags: [redis, session-backend, settings, lifespan, health-check]
dependency_graph:
  requires: [phase-06-json-session-persistence]
  provides: [redis-session-backend, redis-health-check, redis-shutdown]
  affects: [src/core/settings.py, src/agent/session.py, src/app/lifespan.py, pyproject.toml]
tech_stack:
  added: [fakeredis>=2.31.0]
  patterns: [session-backend-factory, conditional-startup-health-check]
key_files:
  created: []
  modified:
    - src/core/settings.py
    - src/agent/session.py
    - src/app/lifespan.py
    - pyproject.toml
decisions:
  - SESSION_BACKEND env var toggles between JSONSession and RedisSession via factory pattern
  - RedisSession uses key_prefix="agentops:" to namespace keys
  - Redis PING health check is fail-fast at startup (service refuses to start if Redis unreachable)
  - Session directory creation is conditional on SESSION_BACKEND=json
  - fakeredis added as dev dependency for testing Redis backend without a running Redis server
metrics:
  duration: 4 min
  tasks: 2
  completed: "2026-04-12"
---

# Phase 07 Plan 01: Redis Session Backend Support Summary

Factory-based Redis session backend with fail-fast health check and graceful shutdown, enabling SESSION_BACKEND=redis as a drop-in alternative to JSON files.

## Changes Made

### Task 1: Add Redis settings fields and extend session factory
- **Commit:** 06ead43
- Added 5 new settings fields: SESSION_BACKEND, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
- Extended `get_session_backend()` to return JSONSession or RedisSession based on SESSION_BACKEND env var
- Added `reset_session_backend()` helper for test teardown and shutdown cleanup
- Added fakeredis>=2.31.0 to dev dependencies in pyproject.toml
- Files: `src/core/settings.py`, `src/agent/session.py`, `pyproject.toml`

### Task 2: Add Redis PING health check to lifespan and RedisSession.close() on shutdown
- **Commit:** fc23fe9
- Added conditional Redis PING health check at startup when SESSION_BACKEND=redis
- Made session directory creation conditional on SESSION_BACKEND=json only
- Added RedisSession.close() call at shutdown with reset_session_backend() singleton cleanup
- Imports _session_backend directly (not via get_session_backend()) to avoid instantiation during shutdown
- Uses hasattr check for close() since JSONSession lacks that method
- Files: `src/app/lifespan.py`

## Verification Results

- `uv sync` -- fakeredis installed successfully
- `from src.agent.session import get_session_backend, reset_session_backend` -- imports succeed
- `grep SESSION_BACKEND src/core/settings.py` -- field present
- `grep RedisSession src/agent/session.py` -- import and usage present
- `grep ping() src/app/lifespan.py` -- health check present
- `grep close() src/app/lifespan.py` -- shutdown close present
- `grep fakeredis pyproject.toml` -- dev dependency present
- `uv run pytest tests/ --ignore=tests/test_context.py -x -q` -- 41 passed, 0 failed (backward compatible)
- `query.py` has zero changes across both commits

## Decisions Made

1. **SESSION_BACKEND toggle via factory** -- Single env var controls which backend class is instantiated; no code changes needed in query.py or any other consumer of get_session_backend().
2. **key_prefix="agentops:"** -- Namespaces Redis keys to avoid collision with other services sharing the same Redis instance.
3. **Fail-fast Redis PING** -- Consistent with Phase 1 startup validation pattern; service refuses to start if Redis is unreachable.
4. **Conditional session directory** -- Only creates the sessions/ directory when using JSON backend; avoids unnecessary filesystem writes when Redis is active.
5. **Direct _session_backend import for shutdown** -- Avoids accidentally creating a new session backend instance during shutdown by importing the module variable directly.

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. No new trust boundaries beyond those documented in the plan's threat model.

## Self-Check: PASSED

- All 4 modified files verified present on disk
- Commit 06ead43 (task 1) verified in git log
- Commit fc23fe9 (task 2) verified in git log
