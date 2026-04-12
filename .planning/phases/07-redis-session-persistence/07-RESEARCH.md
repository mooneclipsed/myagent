# Phase 7: Redis Session Persistence - Research

**Researched:** 2026-04-12
**Domain:** agentscope-runtime RedisSession, redis-py async, fakeredis testing
**Confidence:** HIGH

## Summary

Phase 7 adds a Redis backend for session persistence, mirroring Phase 6's JSON backend via the `agentscope-runtime` built-in `RedisSession` class. The `RedisSession` shares the same `SessionBase` interface as `JSONSession` (`save_session_state` / `load_session_state`), so the query handler (`query.py`) requires ZERO changes -- the factory function in `session.py` transparently returns either backend.

The `RedisSession` internally uses `redis.asyncio` (aliased as `redis.asyncio.Redis`) and supports constructor injection of a custom `connection_pool`, which enables `fakeredis` testing without a real Redis instance. Critical finding: `redis` has no `[async]` extra -- `redis.asyncio` is built into the standard `redis` package. The `redis>=6.0.0` dependency already ships transitively via `agentscope-runtime`, so only `fakeredis` needs to be added to dev dependencies.

**Primary recommendation:** Extend `session.py`'s `get_session_backend()` factory to return `RedisSession` when `SESSION_BACKEND=redis`. Inject `fakeredis.aioredis.FakeRedis` connection pool in tests. The query handler, SSE lifecycle, and API contract remain untouched.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use agentscope-runtime's built-in `RedisSession` for session storage. It shares the same `save_session_state` / `load_session_state` interface as `JSONSession`, enabling direct reuse of the query handler's session logic.
- **D-02:** Add `redis[async]` as a project dependency (required by `RedisSession` internally via `redis.asyncio`). **Research correction:** `redis` has no `[async]` extra. `redis.asyncio` is built into the standard `redis` package. The `redis>=6.0.0` dependency already ships transitively via `agentscope-runtime`. No new runtime dependency needed. Only `fakeredis` must be added to dev dependencies.
- **D-03:** Backend selection is environment-level, not request-level. A new `SESSION_BACKEND` env var controls which backend is created at startup: `"json"` (default, Phase 6 behavior) or `"redis"`. Requests cannot dynamically switch backends.
- **D-04:** Only one session backend is active at a time. The singleton pattern from Phase 6 (`get_session_backend()`) is extended to return either `JSONSession` or `RedisSession` based on `SESSION_BACKEND`.
- **D-05:** Use the framework's built-in Redis connection management. Pass `host`, `port`, `db`, `password` from environment variables to `RedisSession` constructor. No custom `ConnectionPool`.
- **D-06:** New env vars: `REDIS_HOST` (default `"localhost"`), `REDIS_PORT` (default `6379`), `REDIS_DB` (default `0`), `REDIS_PASSWORD` (optional).
- **D-07:** No TTL expiration. Redis keys persist indefinitely, consistent with the JSON backend behavior (Phase 6 D-10: no automatic cleanup). The `key_ttl` parameter is not set.
- **D-08:** Use `key_prefix` to isolate session keys (e.g., `"agentops:"`). Prevents key collisions if Redis is shared.
- **D-09:** When `SESSION_BACKEND=redis`, perform a Redis `PING` at startup via lifespan hook. If Redis is unreachable, the service fails to start (fail-fast, consistent with Phase 1 startup validation pattern).
- **D-10:** Tests use `fakeredis` to simulate Redis -- no real Redis instance needed. CI remains zero-dependency. Test pattern mirrors Phase 6 `test_session.py`.
- **D-11:** Success criteria tests: (1) chat with `session_id` persists state to Redis (via fakeredis), (2) subsequent chat with same `session_id` resumes with prior context, (3) `SESSION_BACKEND=json` still works (backward compatibility), (4) startup health check fails when Redis is unreachable.

### Claude's Discretion
- Exact `session.py` module refactoring to support backend selection.
- Whether to use a factory function or protocol-based abstraction for session backend.
- Exact fakeredis setup in test fixtures.
- Internal test structure, following established Phase 1-6 patterns.

### Deferred Ideas (OUT OF SCOPE)
- Per-request backend switching -- deferred. Environment-level selection is sufficient for R&D validation.
- Redis TTL / session expiration -- deferred to Phase 8 or later. Consistent with JSON backend (no cleanup).
- Session listing / management API -- deferred. Not needed for core save/resume validation.
- Persisting `agent_config` alongside session state -- deferred.
- Parity validation between JSON and Redis -- Phase 8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RES-02 | User can persist session state to Redis backend | RedisSession.save_session_state() verified: accepts session_id, user_id, memory as keyword arg. Stores JSON-serialized state dict to Redis key with optional prefix. |
| RES-04 | User can resume chat from previously persisted session in Redis backend | RedisSession.load_session_state() verified: accepts session_id, user_id, memory, allow_not_exist. Deserializes JSON from Redis and calls load_state_dict() on memory module. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agentscope-runtime | 1.1.3 | Agent runtime with built-in RedisSession | Framework under evaluation; RedisSession is part of `agentscope.session` module [VERIFIED: source inspection] |
| redis (via transitive dep) | 6.4.0 (installed) | redis.asyncio for async Redis client | Ships as transitive dependency of agentscope-runtime (`redis>=6.0.0`). Contains built-in `redis.asyncio` module [VERIFIED: pip show + import] |
| fakeredis | 2.35.0 (latest on PyPI) | In-memory Redis mock for testing | Supports `redis.asyncio` via `fakeredis.aioredis.FakeRedis`; same API surface as `redis.asyncio.Redis` [VERIFIED: PyPI API + GitHub source] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fakeredis[json] | 2.35.0 | RedisJson support in fakeredis | Only if session state uses Redis JSON commands (not needed -- RedisSession uses plain string SET/GET) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fakeredis.aioredis.FakeRedis | Real Redis in Docker | Docker adds CI dependency; fakeredis keeps tests zero-dependency |
| fakeredis.aioredis.FakeRedis | mock/patch redis.asyncio | fakeredis provides actual behavior testing; mocks only verify call patterns |

**Installation:**
```bash
# redis is already a transitive dependency via agentscope-runtime
# Only fakeredis needs to be added as dev dependency
uv add --dev fakeredis>=2.31.0
```

**Version verification:**
```
redis: 6.4.0 (installed, latest is 7.4.0 but agentscope-runtime requires >=6.0.0 with no upper bound)
fakeredis: 2.35.0 (latest on PyPI as of 2026-04-12, agentscope-runtime[dev] requires >=2.31.0)
```

## Architecture Patterns

### Recommended Project Structure (changes only)
```
src/
├── agent/
│   ├── session.py      # MODIFY: extend get_session_backend() factory for Redis
│   └── query.py        # NO CHANGES needed
├── core/
│   └── settings.py     # MODIFY: add SESSION_BACKEND, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
├── app/
│   └── lifespan.py     # MODIFY: add Redis PING health check + RedisSession.close() on shutdown
tests/
├── conftest.py         # MODIFY: add fakeredis fixtures
├── test_session.py     # MODIFY: add Redis session tests
pyproject.toml          # MODIFY: add fakeredis to dev dependencies
```

### Pattern 1: Factory Function for Session Backend
**What:** `get_session_backend()` returns either `JSONSession` or `RedisSession` based on `SESSION_BACKEND` env var.
**When to use:** Always -- this is the only way to obtain a session backend instance.
**Example:**
```python
# src/agent/session.py (extended)
from agentscope.session import JSONSession, RedisSession

_session_backend: JSONSession | RedisSession | None = None

def get_session_backend() -> JSONSession | RedisSession:
    global _session_backend
    if _session_backend is None:
        settings = get_settings()
        backend = getattr(settings, "SESSION_BACKEND", "json")

        if backend == "redis":
            _session_backend = RedisSession(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                key_prefix="agentops:",  # D-08
                # key_ttl intentionally omitted (D-07: no TTL)
            )
            logger.info("Session backend: Redis (host=%s, port=%d)", settings.REDIS_HOST, settings.REDIS_PORT)
        else:
            _session_backend = JSONSession(save_dir=settings.SESSION_DIR)
            logger.info("Session backend: JSON (dir=%s)", settings.SESSION_DIR)

    return _session_backend
```
[Source: Verified by inspecting agentscope.session.RedisSession source code]

### Pattern 2: Fakeredis Test Fixture
**What:** Create a fakeredis-backed RedisSession for tests without a real Redis instance.
**When to use:** All Redis session tests.
**Example:**
```python
# tests/conftest.py (addition)
import fakeredis.aioredis

@pytest.fixture
def redis_env(configured_env, monkeypatch):
    """Configure env for Redis session backend with fakeredis."""
    monkeypatch.setenv("SESSION_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
```

```python
# tests/test_session.py (Redis round-trip test pattern)
import asyncio
import fakeredis.aioredis
from agentscope.session import RedisSession
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg

def test_session_real_redis_round_trip():
    """RES-02 + RES-04: Real RedisSession save/load with fakeredis."""
    async def _round_trip():
        # Create fakeredis instance and extract its connection pool
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        connection_pool = fake_redis.connection_pool

        # Inject fakeredis pool into RedisSession
        session = RedisSession(
            connection_pool=connection_pool,
            key_prefix="agentops:",
        )
        session_id = "test-redis-round-trip-001"

        # Save
        memory_save = InMemoryMemory()
        await memory_save.add(
            Msg(name="user", content="hello from redis test", role="user")
        )
        await session.save_session_state(session_id=session_id, memory=memory_save)

        # Load into fresh memory
        memory_load = InMemoryMemory()
        await session.load_session_state(session_id=session_id, memory=memory_load)

        # Verify
        msgs = await memory_load.get_memory()
        assert len(msgs) == 1
        assert msgs[0].content == "hello from redis test"

        await session.close()

    asyncio.run(_round_trip())
```
[Source: Verified via fakeredis GitHub source + RedisSession constructor inspection]

### Pattern 3: Redis Health Check at Startup
**What:** PING Redis during lifespan startup to fail-fast if unreachable.
**When to use:** When SESSION_BACKEND=redis.
**Example:**
```python
# src/app/lifespan.py (addition in app_lifespan)
if settings.SESSION_BACKEND == "redis":
    from src.agent.session import get_session_backend
    backend = get_session_backend()
    client = backend.get_client()
    await client.ping()
    logger.info("Redis health check passed")
```
[Source: Verified redis.asyncio.Redis has `ping` method [VERIFIED: dir() inspection]]

### Anti-Patterns to Avoid
- **Don't add `redis[async]` to pyproject.toml:** The `[async]` extra does not exist in the `redis` package. `redis.asyncio` is built into the standard `redis` package. Adding `redis[async]` will cause a pip resolution error or be silently ignored. [VERIFIED: PyPI API check - `redis` provides_extras is empty]
- **Don't create a custom ConnectionPool:** The framework manages connections internally. Pass host/port/db/password directly to `RedisSession`. Custom pools are only for testing (fakeredis injection). [CITED: CONTEXT.md D-05]
- **Don't store raw Redis client in module state:** Use `get_session_backend()` singleton. Access the underlying client via `backend.get_client()` only when needed (e.g., PING health check).
- **Don't forget to close RedisSession on shutdown:** `RedisSession` has an async `close()` method that must be called during lifespan shutdown. `JSONSession` has no `close()` method, so use `hasattr` check or isinstance check. [VERIFIED: source inspection - JSONSession has no close(), RedisSession does]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Redis key management | Custom key format + serialization | `RedisSession` with `key_prefix` | RedisSession handles key format (`user_id:{user_id}:session:{session_id}:state`), JSON serialization, and TTL refresh atomically via GETEX |
| Async Redis client setup | Manual `redis.asyncio.Redis()` creation | `RedisSession(host=, port=, ...)` constructor | Constructor handles `decode_responses=True`, connection pool creation, and import validation |
| Session state serialization | Custom JSON encode/decode for Redis | `save_session_state` / `load_session_state` | RedisSession uses `json.dumps`/`json.loads` with `ensure_ascii=False` internally |
| Redis health check | Custom connection test | `redis.asyncio.Redis.ping()` | Standard PING/PONG protocol command, `await client.ping()` returns `True` |

**Key insight:** `RedisSession` and `JSONSession` share the `SessionBase` abstract interface. The query handler calls `save_session_state(session_id=..., memory=memory)` identically for both backends. This is the entire point of the abstraction.

## Runtime State Inventory

> Phase 7 is not a rename/refactor/migration phase. This section is included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None -- Phase 7 adds a new storage backend, no existing data to migrate | N/A |
| Live service config | None -- Redis connection is configured via env vars at startup | N/A |
| OS-registered state | None | N/A |
| Secrets/env vars | New env vars: SESSION_BACKEND, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD | Add to .env.example (not to git) |
| Build artifacts | None -- no compiled artifacts affected | N/A |

## Common Pitfalls

### Pitfall 1: redis[async] Extra Does Not Exist
**What goes wrong:** Adding `redis[async]` to pyproject.toml dependencies will either fail or be silently ignored. The `redis` package has no `[async]` extra -- `redis.asyncio` is always available in the standard package.
**Why it happens:** The `RedisSession.__init__` error message says "Please install it via 'pip install redis[async]'", but this is misleading. The async support is built into the base `redis` package.
**How to avoid:** Do not add any redis dependency to pyproject.toml. The `redis>=6.0.0` transitive dependency from `agentscope-runtime` already provides `redis.asyncio`.
**Warning signs:** `pip install redis[async]` succeeds but does nothing different from `pip install redis`.
[VERIFIED: PyPI API -- redis package has empty provides_extras list]

### Pitfall 2: decode_responses Must Be True
**What goes wrong:** RedisSession internally creates `redis.asyncio.Redis(..., decode_responses=True)`. If you inject a fakeredis connection pool with `decode_responses=False`, the `load_session_state` method will receive `bytes` instead of `str`, causing JSON decode to fail.
**Why it happens:** RedisSession has a fallback `if isinstance(data, (bytes, bytearray)): data = data.decode("utf-8")` but relying on it is fragile.
**How to avoid:** Always create `FakeRedis(decode_responses=True)` in test fixtures to match the production configuration.
**Warning signs:** `TypeError: the JSON object must be str, bytes or bytearray, not NoneType` in tests.
[VERIFIED: RedisSession.load_session_state source has bytes fallback]

### Pitfall 3: RedisSession.close() on Shutdown
**What goes wrong:** If the Redis client connection is not closed on shutdown, you may see "Unclosed connection" warnings or resource leaks.
**Why it happens:** `JSONSession` has no `close()` method, so the existing lifespan shutdown code doesn't close any session backend. Phase 6's shutdown only closes MCP clients.
**How to avoid:** Add RedisSession close in lifespan shutdown: check if backend is a `RedisSession` and call `await backend.close()`.
**Warning signs:** `ResourceWarning: unclosed connection` in test output or logs.
[VERIFIED: RedisSession has `async def close()`, JSONSession does not]

### Pitfall 4: Singleton Reset Between Tests
**What goes wrong:** `get_session_backend()` caches the backend in a module-level `_session_backend` variable. If one test creates a JSONSession and the next test expects a RedisSession, the cached singleton from the first test will be returned.
**Why it happens:** Tests run in the same process by default. The singleton is never reset.
**How to avoid:** Add a `_reset_session_backend()` helper (or use monkeypatch) to clear the module-level variable before each test that depends on session backend selection. Follow the same pattern as `get_settings().cache_clear()`.
**Warning signs:** Tests pass individually but fail when run together.

### Pitfall 5: key_prefix Trailing Colon
**What goes wrong:** If `key_prefix` is set without a trailing colon, keys become ambiguous (e.g., `agentopssession:123` vs `agentops:session:123`).
**Why it happens:** The prefix is prepended literally with no separator added.
**How to avoid:** Always include trailing colon in key_prefix: `"agentops:"` (not `"agentops"`).
**Warning signs:** Redis keys are not namespaced correctly; `KEYS agentops*` returns unexpected results.
[VERIFIED: RedisSession._get_session_key source: `self.key_prefix + self.SESSION_KEY.format(...)`]

## Code Examples

### Verified: RedisSession Constructor (from source)
```python
# Source: agentscope.session.RedisSession (VERIFIED via inspect.getsource)
from agentscope.session import RedisSession

# Production usage (env vars from settings)
session = RedisSession(
    host="localhost",       # REDIS_HOST
    port=6379,              # REDIS_PORT
    db=0,                   # REDIS_DB
    password=None,          # REDIS_PASSWORD (optional)
    key_prefix="agentops:", # D-08: isolate keys
    # key_ttl NOT set (D-07: no TTL)
)

# Test usage (fakeredis injection)
import fakeredis.aioredis
fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
session = RedisSession(
    connection_pool=fake.connection_pool,
    key_prefix="agentops:",
)
```

### Verified: RedisSession Key Format
```python
# Source: agentscope.session.RedisSession (VERIFIED via source inspection)
# Key pattern: "{key_prefix}user_id:{user_id}:session:{session_id}:state"
# Example with key_prefix="agentops:" and user_id="default_user":
#   "agentops:user_id:default_user:session:test-session-001:state"

# The save_session_state serializes all state modules to JSON:
# {"memory": {"messages": [...]}}
# And stores as a plain string via SET (with optional ex=TTL)
```

### Verified: RedisSession Save/Load Signatures
```python
# Source: agentscope.session.RedisSession (VERIFIED via inspect.getsource)
async def save_session_state(
    self,
    session_id: str,
    user_id: str = "default_user",  # Note: default is "default_user" not ""
    **state_modules_mapping: StateModule,  # keyword args: memory=memory
) -> None: ...

async def load_session_state(
    self,
    session_id: str,
    user_id: str = "default_user",
    allow_not_exist: bool = True,
    **state_modules_mapping: StateModule,  # keyword args: memory=memory
) -> None: ...
```

### Verified: JSONSession Default user_id Difference
```python
# JSONSession default user_id is "" (empty string)
# RedisSession default user_id is "default_user"
# This is a minor API inconsistency in agentscope-runtime.
# For consistency, always pass user_id explicitly when calling save/load.
# In query.py, user_id is NOT passed, so defaults are used.
# JSONSession keys: "{session_id}.json" (no user_id prefix when user_id="")
# RedisSession keys: "agentops:user_id:default_user:session:{session_id}:state"
```
[VERIFIED: source inspection of both classes]

### Verified: Redis Health Check Pattern
```python
# Source: redis.asyncio.Redis (VERIFIED via dir() inspection)
client = redis_session.get_client()
# ping() is an async method
result = await client.ping()  # Returns True on success, raises ConnectionError on failure
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `aioredis` standalone package | `redis.asyncio` (built into redis-py) | redis-py 4.2+ (2021) | No separate install needed; `aioredis` is deprecated |
| `redis[async]` extra | No extra needed | redis-py 5.0+ | async support is always available in base package |
| Real Redis for testing | `fakeredis.aioredis.FakeRedis` | fakeredis 2.x+ | Zero-dependency async Redis testing |

**Deprecated/outdated:**
- `aioredis` package: Merged into redis-py. Use `redis.asyncio` instead. [CITED: redis.io FAQ]
- `redis[async]` extra: Does not exist in modern redis-py. The import error message in `RedisSession.__init__` references it, but it is misleading.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | fakeredis.aioredis.FakeRedis can be injected into RedisSession via connection_pool parameter | Architecture Patterns | Tests fail; need alternative injection strategy |
| A2 | fakeredis 2.35.0 is compatible with redis 6.4.0 (fakeredis requires redis>=4.3 for Python>3.8) | Standard Stack | Version conflict requiring redis upgrade |
| A3 | TestClient (sync) properly handles async RedisSession operations in the SSE handler | Testing | Tests hang or fail; need async test client |

**Risk assessment for A1 (LOW):** The injection path is `FakeRedis -> .connection_pool -> RedisSession(connection_pool=pool) -> redis.asyncio.Redis(connection_pool=pool)`. Since `FakeRedis` inherits from `redis.asyncio.Redis` and uses the same `ConnectionPool` type, this should work. The risk is that `decode_responses=True` must be set on the `FakeRedis` instance to match production behavior.

**Risk assessment for A2 (LOW):** fakeredis 2.35.0 requires `redis>=4.3` for Python>3.8. The installed redis 6.4.0 satisfies this constraint. No conflict expected.

**Risk assessment for A3 (LOW):** The existing test pattern uses `TestClient` (sync) which runs the async handler in a thread. `RedisSession.save_session_state` and `load_session_state` are async but called within the async query handler context. `TestClient` handles this transparently -- Phase 6 JSONSession tests already work this way with the same async pattern.

## Open Questions

1. **Should `redis` be added to pyproject.toml as an explicit dependency?**
   - What we know: `redis>=6.0.0` is already a transitive dependency via `agentscope-runtime`. It is installed and `redis.asyncio` works.
   - What's unclear: Whether to explicitly declare it for clarity and version pinning.
   - Recommendation: Do NOT add it. Declaring transitive dependencies is an anti-pattern. If a specific version is needed, pin it via agentscope-runtime's dependency resolution.

2. **Should fakeredis version be pinned or use a range?**
   - What we know: `agentscope-runtime[dev]` requires `fakeredis>=2.31.0`. Latest is 2.35.0.
   - What's unclear: Whether exact pinning is needed.
   - Recommendation: Use `fakeredis>=2.31.0` to match agentscope-runtime's constraint. This is consistent with the project's approach of not over-constraining dev dependencies.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| redis (redis.asyncio) | RedisSession | Yes (transitive) | 6.4.0 | -- |
| fakeredis | Test suite | No | -- | Must install: `uv add --dev fakeredis>=2.31.0` |
| Redis server | Production runtime | Not checked | -- | Not needed for dev/test (fakeredis mocks it) |
| pytest-asyncio | Async test support | No | -- | Not needed -- existing pattern uses `asyncio.run()` and sync `TestClient` |

**Missing dependencies with no fallback:**
- `fakeredis>=2.31.0` must be added to dev dependencies before writing Redis session tests.

**Missing dependencies with fallback:**
- `pytest-asyncio` is not installed but not needed. The existing test pattern uses `asyncio.run()` for direct async round-trip tests and sync `TestClient` for API-level tests. No change needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_session.py -x -q` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RES-02 | Persist session state to Redis backend | unit (round-trip) | `uv run pytest tests/test_session.py::test_session_real_redis_round_trip -x` | No - Wave 0 |
| RES-02 | Chat with session_id persists to Redis | integration | `uv run pytest tests/test_session.py::test_session_persists_to_redis -x` | No - Wave 0 |
| RES-04 | Resume chat from Redis session | integration | `uv run pytest tests/test_session.py::test_session_resume_redis -x` | No - Wave 0 |
| D-09 | Startup health check fails when Redis unreachable | unit | `uv run pytest tests/test_session.py::test_redis_health_check_failure -x` | No - Wave 0 |
| D-03 | SESSION_BACKEND=json still works | integration | `uv run pytest tests/test_session.py::test_session_persists_to_json -x` | Yes (Phase 6) |
| D-10 | fakeredis test fixture works | unit | `uv run pytest tests/test_session.py -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_session.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_session.py` -- add Redis session tests (round-trip, persist, resume, health check)
- [ ] `tests/conftest.py` -- add `redis_env` fixture with fakeredis setup
- [ ] `pyproject.toml` -- add `fakeredis>=2.31.0` to dev dependencies

## Security Domain

> Phase 7 adds Redis connectivity but does not introduce new user-facing authentication, session management, or cryptographic patterns beyond what Phase 6 established.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Redis auth is infrastructure-level via REDIS_PASSWORD env var, not user-facing |
| V3 Session Management | No | Session IDs are UUID4-generated, same as Phase 6. No new session management patterns. |
| V4 Access Control | No | No new access control patterns |
| V5 Input Validation | Yes | validate_session_id() from Phase 6 still applies. Redis key injection is mitigated by key_prefix and framework-managed key format. |
| V6 Cryptography | No | Redis connection uses standard TCP. REDIS_PASSWORD is stored in .env (externalized config). |

### Known Threat Patterns for Redis Session Persistence

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Redis key injection via session_id | Tampering | `validate_session_id()` blocks path traversal and special characters; framework manages key format internally |
| Redis connection without auth | Spoofing | REDIS_PASSWORD env var support; network-level Redis ACL recommended for production |
| Session state tampering in Redis | Tampering | Redis ACLs in production; R&D context does not require encryption at rest |
| Redis server SSRF | Elevation | REDIS_HOST/PORT are env-configured, not user-supplied. No user control over Redis address. |

## Sources

### Primary (HIGH confidence)
- agentscope.session.RedisSession source code -- inspected via `inspect.getsource(RedisSession)` [VERIFIED: source inspection]
- agentscope.session.JSONSession source code -- inspected via `inspect.getsource(JSONSession)` [VERIFIED: source inspection]
- agentscope.session.SessionBase source code -- inspected via `inspect.getsource(SessionBase)` [VERIFIED: source inspection]
- redis package PyPI API -- `redis` 7.4.0 latest, provides_extras is empty, no `[async]` extra [VERIFIED: PyPI JSON API]
- fakeredis package PyPI API -- 2.35.0 latest, requires `redis>=4.3` for Python>3.8 [VERIFIED: PyPI JSON API]
- fakeredis GitHub source (`fakeredis/aioredis.py`) -- FakeRedis inherits redis.asyncio.Redis, connection_pool injection path verified [VERIFIED: GitHub source]

### Secondary (MEDIUM confidence)
- [fakeredis.readthedocs.io](https://fakeredis.readthedocs.io/) -- official docs, async testing support confirmed
- [fakeredis GitHub changelog](https://fakeredis.readthedocs.io/en/latest/about/changelog/) -- v2.33.0+ supports redis-py 7.1.0 and async tests on RESP2/RESP3
- [redis.io FAQ](https://redis.io/faq/doc/26366kjrif/what-is-the-difference-between-aioredis-v2-0-and-redis-py-asyncio) -- aioredis merged into redis-py

### Tertiary (LOW confidence)
- None -- all critical claims verified via source inspection or PyPI API.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - redis and fakeredis versions verified via PyPI API and source inspection
- Architecture: HIGH - RedisSession API fully verified via inspect.getsource; fakeredis injection path confirmed via GitHub source
- Pitfalls: HIGH - redis[async] non-existence verified via PyPI API; decode_responses and close() issues verified via source inspection

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable domain, low churn expected)
