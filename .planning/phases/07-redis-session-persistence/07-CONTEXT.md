# Phase 7: Redis Session Persistence - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Persist and resume sessions using a Redis backend, mirroring the Phase 6 JSON persistence with an alternative storage layer. Users can save a session to Redis and resume the conversation from where they left off. This phase does NOT add parity validation (Phase 8), new API fields, or changes to the session state model.

</domain>

<decisions>
## Implementation Decisions

### Redis Session Backend
- **D-01:** Use agentscope-runtime's built-in `RedisSession` for session storage. It shares the same `save_session_state` / `load_session_state` interface as `JSONSession`, enabling direct reuse of the query handler's session logic.
- **D-02:** Add `redis[async]` as a project dependency (required by `RedisSession` internally via `redis.asyncio`).

### Backend Selection Mechanism
- **D-03:** Backend selection is environment-level, not request-level. A new `SESSION_BACKEND` env var controls which backend is created at startup: `"json"` (default, Phase 6 behavior) or `"redis"`. Requests cannot dynamically switch backends.
- **D-04:** Only one session backend is active at a time. The singleton pattern from Phase 6 (`get_session_backend()`) is extended to return either `JSONSession` or `RedisSession` based on `SESSION_BACKEND`.

### Redis Connection Management
- **D-05:** Use the framework's built-in Redis connection management. Pass `host`, `port`, `db`, `password` from environment variables to `RedisSession` constructor. No custom `ConnectionPool`.
- **D-06:** New env vars: `REDIS_HOST` (default `"localhost"`), `REDIS_PORT` (default `6379`), `REDIS_DB` (default `0`), `REDIS_PASSWORD` (optional).

### Redis Key & TTL
- **D-07:** No TTL expiration. Redis keys persist indefinitely, consistent with the JSON backend behavior (Phase 6 D-10: no automatic cleanup). The `key_ttl` parameter is not set.
- **D-08:** Use `key_prefix` to isolate session keys (e.g., `"agentops:"`). Prevents key collisions if Redis is shared.

### Startup Health Check
- **D-09:** When `SESSION_BACKEND=redis`, perform a Redis `PING` at startup via lifespan hook. If Redis is unreachable, the service fails to start (fail-fast, consistent with Phase 1 startup validation pattern).

### Verification
- **D-10:** Tests use `fakeredis` to simulate Redis — no real Redis instance needed. CI remains zero-dependency. Test pattern mirrors Phase 6 `test_session.py`.
- **D-11:** Success criteria tests: (1) chat with `session_id` persists state to Redis (via fakeredis), (2) subsequent chat with same `session_id` resumes with prior context, (3) `SESSION_BACKEND=json` still works (backward compatibility), (4) startup health check fails when Redis is unreachable.

### Claude's Discretion
- Exact `session.py` module refactoring to support backend selection.
- Whether to use a factory function or protocol-based abstraction for session backend.
- Exact fakeredis setup in test fixtures.
- Internal test structure, following established Phase 1-6 patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 7 goal, requirements mapping (RES-02, RES-04), and success criteria.
- `.planning/REQUIREMENTS.md` — `RES-02` (persist session to Redis backend) and `RES-04` (resume from Redis session) definitions.

### Prior phase context to preserve
- `.planning/phases/06-json-session-persistence/06-CONTEXT.md` — locked session state model, API design (session_id in request body), resume behavior, and query handler integration pattern that Phase 7 extends.
- `.planning/phases/05-context-continuity-validation/05-CONTEXT.md` — locked context continuity decisions that Phase 7 preserves.
- `.planning/phases/04-capability-invocation-tracing/04-CONTEXT.md` — locked tool/MCP registration pattern that must work during Redis session save/resume.

### Framework capabilities (verified)
- `agentscope.session.RedisSession` — built-in Redis session storage. Constructor: `(host, port, db, password, connection_pool, key_ttl, key_prefix)`. Methods: `save_session_state(session_id, user_id, memory=...)`, `load_session_state(session_id, user_id, memory=...)`.
- `agentscope.session.JSONSession` — existing JSON session backend from Phase 6.
- `agentscope.session.SessionBase` — shared base class with common `save_session_state` / `load_session_state` interface.

### Project-level constraints
- `.planning/PROJECT.md` — near-stateless service design, FastAPI API form, `agentscope-runtime` dependency, session backends constraint (JSON + Redis).
- `CLAUDE.md` — repository-level workflow and project constraints.

### Testing dependencies
- `fakeredis` — in-memory Redis mock for testing. Must be added to dev dependencies.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agent/session.py` — existing session module with `get_session_backend()` singleton, `generate_session_id()`, `validate_session_id()`. Phase 7 extends `get_session_backend()` to support Redis based on env config.
- `src/agent/query.py` — existing `@app.query` handler with session save/load logic (D-07, D-08). **No changes needed** — it already calls `get_session_backend()` which returns either backend transparently.
- `src/core/settings.py` — `Settings` class. Phase 7 adds `SESSION_BACKEND`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` fields.
- `src/app/lifespan.py` — startup hooks. Phase 7 adds Redis PING health check when `SESSION_BACKEND=redis`.
- `tests/conftest.py` — shared fixtures. Phase 7 adds fakeredis-based fixtures.
- `tests/test_session.py` — existing JSON session tests. Phase 7 adds Redis session tests following the same pattern.

### Established Patterns
- Singleton session backend via module-level variable (Phase 6 pattern) — Phase 7 extends this.
- `save_session_state` / `load_session_state` called in query handler around agent lifecycle (Phase 6 D-07/D-08).
- Fail-fast startup validation (Phase 1 pattern) — Redis PING check follows this.
- Mock-based testing without real external dependencies (Phase 2-6 pattern).
- SSE event lifecycle from Phase 2 must be preserved.

### Integration Points
- `src/agent/session.py` — primary change: `get_session_backend()` becomes a factory returning JSONSession or RedisSession.
- `src/core/settings.py` — add Redis connection settings.
- `src/app/lifespan.py` — add Redis health check at startup.
- `pyproject.toml` — add `redis[async]` to dependencies, `fakeredis` to dev dependencies.

</code_context>

<specifics>
## Specific Ideas

- The key insight: `query.py` should need ZERO changes because it already uses `get_session_backend()` as an abstraction. The only work is in `session.py`, `settings.py`, `lifespan.py`, and tests.
- `RedisSession` uses `redis.asyncio` internally — the same async pattern as the existing JSON session.
- `key_prefix` should default to `"agentops:"` to isolate keys in shared Redis instances.
- fakeredis supports `redis.asyncio` — verify compatibility during research.

</specifics>

<deferred>
## Deferred Ideas

- Per-request backend switching — deferred. Environment-level selection is sufficient for R&D validation.
- Redis TTL / session expiration — deferred to Phase 8 or later. Consistent with JSON backend (no cleanup).
- Session listing / management API — deferred. Not needed for core save/resume validation.
- Persisting `agent_config` alongside session state — deferred.
- Parity validation between JSON and Redis — Phase 8.

---
*Phase: 07-redis-session-persistence*
*Context gathered: 2026-04-12*
