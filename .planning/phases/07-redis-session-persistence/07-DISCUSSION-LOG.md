# Phase 7: Redis Session Persistence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 07-redis-session-persistence
**Areas discussed:** Redis session implementation, Backend selection mechanism, Redis connection management, Test strategy, TTL strategy, Startup health check

---

## Redis Session Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Use framework RedisSession | agentscope-runtime has built-in RedisSession with same save/load API as JSONSession | ✓ |
| Custom Redis storage layer | Build own Redis wrapper, still use state_dict() for serialization | |

**User's choice:** Use framework RedisSession (recommended)
**Notes:** Framework's RedisSession shares the SessionBase interface with JSONSession, enabling transparent backend switching.

---

## Backend Selection Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Environment variable | SESSION_BACKEND=json\|redis, set at deploy time | ✓ |
| Request-level parameter | Per-request backend choice via request body field | |
| Auto-detection | Automatically pick backend based on session_id format | |

**User's choice:** Environment variable configuration (recommended)
**Notes:** Keeps the design simple — one backend per service instance. Sufficient for R&D validation use case.

---

## Redis Connection Management

| Option | Description | Selected |
|--------|-------------|----------|
| Framework built-in | Pass host/port/db/password to RedisSession, let it manage the connection | ✓ |
| Custom connection pool | Create redis.asyncio.ConnectionPool and pass to RedisSession | |

**User's choice:** Use framework built-in connection (recommended)
**Notes:** RedisSession internally creates redis.asyncio.Redis client. No need to manage pool lifecycle separately.

---

## Test Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| fakeredis mock | In-memory Redis simulation, zero external dependencies | ✓ |
| Real Redis instance | Requires Redis in CI, more production-like | |
| Mixed | Unit tests with fakeredis, integration with real Redis | |

**User's choice:** fakeredis mock (recommended)
**Notes:** Consistent with existing project test pattern — all tests use mocks (no real LLM, no real MCP).

---

## TTL Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| No TTL | Keys persist indefinitely, consistent with JSON backend | ✓ |
| Configurable TTL | Use RedisSession key_ttl for sliding expiration | |

**User's choice:** No TTL (recommended)
**Notes:** R&D validation use case. Consistent with Phase 6 D-10 (no automatic cleanup for JSON sessions).

---

## Startup Health Check

| Option | Description | Selected |
|--------|-------------|----------|
| PING at startup | Fail-fast if Redis unreachable, consistent with Phase 1 pattern | ✓ |
| Lazy connection | Connect on first request, service starts fast but may fail later | |

**User's choice:** PING at startup (recommended)
**Notes:** Matches existing fail-fast startup validation from Phase 1 (settings validation, MCP connection).

---

## Claude's Discretion

- Exact session.py module refactoring approach
- Factory vs protocol-based abstraction for backend selection
- Exact fakeredis test fixture setup
- Internal test structure following Phase 1-6 patterns

## Deferred Ideas

None — discussion stayed within phase scope.
