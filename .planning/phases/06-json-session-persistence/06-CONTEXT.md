# Phase 6: JSON Session Persistence - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Persist and resume sessions using a JSON-file backend. This is the first server-side session storage layer — transitioning from the client-managed message history (Phase 5) to server-persisted session state. Users can save a session to JSON, then resume and continue the conversation from where they left off.

This phase does NOT add Redis persistence (Phase 7), parity validation (Phase 8), or structured trace inspection.

</domain>

<decisions>
## Implementation Decisions

### Session State Model
- **D-01:** Use agentscope-runtime's built-in `JSONSession` for session storage and `InMemoryMemory.state_dict()` / `load_state_dict()` for memory serialization. Leverage the framework's existing serialization rather than building custom JSON storage.
- **D-02:** Persist only the agent's memory (conversation history). Do NOT persist `agent_config` — each resume re-evaluates config from request or `.env` defaults.
- **D-03:** Agent config changes between save and resume are allowed. If the client provides `agent_config` during resume, it is used; otherwise `.env` defaults apply. No config locking to original session values.

### Session Identity & API Design
- **D-04:** Client provides `session_id` in the request body. When absent or empty, a new session is created and the generated `session_id` is returned in the response. When present, the server loads the existing session and resumes.
- **D-05:** Extend the existing `/process` endpoint by adding an optional `session_id` field to the request body. When `session_id` is absent, behavior is identical to current stateless flow (backward compatible). When present, session persistence is activated.
- **D-06:** Request body becomes: `{ "messages": [...], "agent_config": {...}, "session_id": "abc123" }`. All three top-level fields are optional.

### Resume Behavior
- **D-07:** On resume, the server loads the saved memory state from JSON, creates a fresh `ReActAgent` with the restored `InMemoryMemory`, and processes the new message. The client only needs to send `session_id` + new message — no need to resend full conversation history.
- **D-08:** After each request with a `session_id`, the updated memory state is saved back to the JSON file. This ensures the session is always up-to-date for the next resume.

### File Storage Layout
- **D-09:** Sessions are stored in a flat `sessions/` directory (configurable via environment variable, e.g., `SESSION_DIR`). Each session is one JSON file: `{session_id}.json`.
- **D-10:** No automatic cleanup or TTL expiration. Session files persist until manually deleted. Cleanup strategy deferred to Phase 8 or later.

### Verification
- **D-11:** Verification follows the established pattern: `pytest` automated tests + smoke script. Tests validate save, load, resume round-trip, and backward compatibility (requests without session_id).
- **D-12:** Success criteria tests: (1) a chat with session_id persists session state to JSON file, (2) a subsequent chat with same session_id resumes and has access to prior context, (3) a chat without session_id behaves identically to Phase 5 (backward compatibility).

### Claude's Discretion
- Exact `session_id` generation format (UUID, nanoid, etc.) — as long as it's unique and URL-safe.
- Exact JSON file internal structure — as long as JSONSession's built-in format is used.
- Internal module layout for session management code.
- Exact test structure and smoke script shape, following established Phase 1-5 patterns.
- How to integrate session save/load into the query handler lifecycle (before/after agent call).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 6 goal, requirements mapping (RES-01, RES-03), and success criteria.
- `.planning/REQUIREMENTS.md` — `RES-01` (persist session to JSON backend) and `RES-03` (resume from JSON session) definitions.

### Prior phase context to preserve
- `.planning/phases/05-context-continuity-validation/05-CONTEXT.md` — locked context continuity decisions (client-managed history, near-stateless design) that Phase 6 extends with server-side persistence.
- `.planning/phases/04-capability-invocation-tracing/04-CONTEXT.md` — locked tool/MCP registration pattern that Phase 6 must preserve during session save/resume.
- `.planning/phases/03-request-scoped-agent-stateless-runtime/03-CONTEXT.md` — locked request-scoped agent creation and config resolution that Phase 6 integrates with session restore.
- `.planning/phases/02-streaming-chat-contract/02-CONTEXT.md` — locked streaming contract (SSE event lifecycle, messages array format) that Phase 6 must not break.

### Framework capabilities to research
- `agentscope.session.JSONSession` — built-in JSON file session storage. Researcher must verify API: constructor args (save_dir), save/load methods, session_id handling.
- `agentscope.memory.InMemoryMemory.state_dict()` / `load_state_dict()` — memory serialization. Researcher must verify the state dict format and restoration behavior.
- `agentscope.session.SessionBase` — base session class for understanding the save/load lifecycle.

### Project-level constraints
- `.planning/PROJECT.md` — near-stateless service design constraint (extended, not violated, by optional session persistence), FastAPI API form, `agentscope-runtime` dependency.
- `CLAUDE.md` — repository-level workflow and project constraints.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agent/query.py` — existing `@app.query` handler that creates a fresh `ReActAgent` per request with `InMemoryMemory()`. Phase 6 modifies this to optionally load/save session state.
- `src/core/config.py` — `AgentConfig` model and `resolve_effective_config()` for per-request config. Phase 6 continues to use this for agent creation during resume.
- `src/core/settings.py` — `Settings` class with `.env` config. Phase 6 may add `SESSION_DIR` setting.
- `src/main.py` — `AgentApp` instance with `/process` endpoint. No changes needed to endpoint registration.
- `src/app/lifespan.py` — startup/shutdown hooks. Phase 6 may need session directory initialization at startup.
- `tests/conftest.py` — shared test fixtures. Phase 6 tests can extend these.

### Established Patterns
- Each request creates a fresh `ReActAgent` in the `@app.query` async generator (Phase 3 pattern). Phase 6 preserves this but optionally restores memory state.
- Verification via `pytest` + smoke script (Phase 1-5 pattern).
- Mock LLM calls for deterministic testing (Phase 2-5 pattern).
- SSE event lifecycle from Phase 2 must be preserved.
- Backward compatibility: requests without new fields must work identically to previous behavior.

### Integration Points
- `src/agent/query.py` is the primary integration point — session save/load wraps around the existing agent creation and message processing.
- Request body parsing: the new `session_id` field coexists with existing `messages` and `agent_config`.
- `src/app/lifespan.py` may need session directory initialization at startup.
- `src/core/settings.py` may need a new `SESSION_DIR` setting.

</code_context>

<specifics>
## Specific Ideas

- The key transformation: from "client sends full history every time" (Phase 5) to "server stores and restores history, client just sends session_id + new message". This is a meaningful UX improvement for conversational testing.
- agentscope-runtime's `JSONSession` handles the file I/O — we mainly need to wire it into the query handler lifecycle correctly.
- The `session_id` response should be included in the SSE stream or response metadata so the client knows what ID was assigned for new sessions.
- Session directory should have a sensible default (e.g., `./sessions/`) and be configurable.

</specifics>

<deferred>
## Deferred Ideas

- Session cleanup / TTL / expiration — deferred to Phase 8 or later. Manual cleanup is acceptable for R&D use.
- Persisting `agent_config` alongside session state — deferred. Could be useful for reproducibility but adds complexity.
- Session listing / management API — deferred. Not needed for core save/resume validation.
- Session metadata (timestamps, turn counts) — deferred. Not required for RES-01/RES-03.
- Redis session persistence — Phase 7.
- Parity validation between JSON and Redis — Phase 8.

</deferred>

---

*Phase: 06-json-session-persistence*
*Context gathered: 2026-04-12*
