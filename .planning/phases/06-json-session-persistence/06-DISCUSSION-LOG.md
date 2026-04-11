# Phase 6: JSON Session Persistence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 06-json-session-persistence
**Areas discussed:** Session State Model, Session Identity & API Design, Resume Behavior, File Storage Layout

---

## Session State Model

| Option | Description | Selected |
|--------|-------------|----------|
| 框架内建方案 | Use JSONSession + InMemoryMemory.state_dict(). Don't persist agent_config. | ✓ |
| 扩展内建方案 | JSONSession + extra metadata (timestamps, turn count, agent_config) | |
| 完全自定义 | Custom JSON storage, manual serialization | |

**User's choice:** 框架内建方案 (recommended)
**Notes:** Leverage agentscope-runtime's built-in JSONSession and state_dict()/load_state_dict() serialization. Keep agent_config ephemeral — re-evaluated on each request from request body or .env defaults.

## Session Identity & API Design

| Option | Description | Selected |
|--------|-------------|----------|
| 客户端提供 session_id | Client provides session_id in request body; server generates if absent | ✓ |
| 服务端生成 | Server always generates and returns session_id | |
| 内容哈希 | Hash-based session_id from request content | |

**User's choice:** 客户端提供 (recommended)
**Notes:** Client controls session identity. New sessions: no session_id → server generates and returns. Existing sessions: client provides session_id to resume.

### API Endpoint Design

| Option | Description | Selected |
|--------|-------------|----------|
| 扩展现有端点 | Add session_id field to /process request body. Backward compatible. | ✓ |
| 独立端点 | New /session/save and /session/resume endpoints | |
| 混合方案 | Extend /process + add /session/{id} management endpoint | |

**User's choice:** 扩展现有端点 (recommended)
**Notes:** One endpoint handles all cases. No session_id → stateless (Phase 5 behavior). With session_id → persistent session flow. Request body: `{ "messages": [...], "agent_config": {...}, "session_id": "abc123" }`.

## Resume Behavior & Consistency

### Agent/Memory Rebuild

| Option | Description | Selected |
|--------|-------------|----------|
| 重建 agent + memory | Load memory from JSON, create fresh agent with restored memory, process new message | ✓ |
| 补充式历史 | Load history messages only, client still provides full messages array | |

**User's choice:** 重建 agent + memory (recommended)
**Notes:** Client only sends session_id + new message. Server handles memory restoration internally.

### Config Consistency on Resume

| Option | Description | Selected |
|--------|-------------|----------|
| 锁死原始 config | Resume must use same config as original session | |
| 允许 config 变更 | Allow different agent_config on resume, client decides | ✓ |

**User's choice:** 允许 config 变更
**Notes:** Flexible — allows testing with different models/providers while keeping conversation context. No config locking needed.

## File Storage Layout

### Directory Structure

| Option | Description | Selected |
|--------|-------------|----------|
| 平铺目录 | Flat sessions/ dir, one file per session ({session_id}.json). Path configurable via env. | ✓ |
| 嵌套目录 | Nested by date or user_id (sessions/2026-04/ or sessions/{user_id}/) | |

**User's choice:** 平铺目录 (recommended)
**Notes:** Simple and debuggable. SESSION_DIR env var for configuration.

### Cleanup Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 无自动清理 | No TTL, files persist until manually deleted. Cleanup deferred to Phase 8. | ✓ |
| TTL 过期清理 | Auto-cleanup expired sessions based on TTL | |

**User's choice:** 无自动清理 (recommended)
**Notes:** Keep it simple for R&D use. Phase 8 demo flows may revisit cleanup.

## Claude's Discretion

- session_id generation format (UUID, nanoid, etc.)
- JSON file internal structure (JSONSession built-in format)
- Internal module layout for session management
- Test structure and smoke script shape
- Integration of session save/load into query handler lifecycle

## Deferred Ideas

- Session cleanup / TTL / expiration — Phase 8 or later
- Persisting agent_config with session — adds complexity, not needed for RES-01/RES-03
- Session listing/management API — not needed for core validation
- Session metadata (timestamps, turn counts) — deferred
