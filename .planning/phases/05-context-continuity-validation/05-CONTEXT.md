# Phase 5: Context Continuity Validation - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify that multi-turn context stays consistent within a single session. The agent must receive and utilize prior conversation turns when the client sends a complete message history. This phase does not add server-side session state, session persistence, or resume capabilities — those belong to Phases 6-8.

</domain>

<decisions>
## Implementation Decisions

### Session Identity & State Management
- **D-01:** Client manages full conversation history. Each request carries the complete messages array (all prior turns + new message). No server-side session state or session_id is introduced in this phase.
- **D-02:** Server remains near-stateless — each request still creates a fresh agent. Context continuity comes from the client passing full history, not from server-side session storage.

### Context Passing
- **D-03:** Pass the complete messages array directly to the agent via `agent(msgs)`. Rely on agentscope-runtime's native multi-turn message handling. Do not pre-populate InMemoryMemory manually.
- **D-04:** The client's messages array format follows the existing Phase 2 contract (role + content objects). No new message format is introduced.

### Verification Strategy
- **D-05:** Primary tests use mocked LLM calls. Tests assert that the message array passed to the model contains the full multi-turn history. This is deterministic, repeatable, and consistent with Phase 2-4 mock patterns.
- **D-06:** Smoke script (optional) can demonstrate end-to-end multi-turn flow with a real LLM, but automated CI tests rely on mocks only.
- **D-07:** Success criteria tests: (1) a multi-turn request (3+ messages) results in the agent receiving all prior messages, (2) a single-turn request (1 message) behaves identically to current Phase 4 behavior (backward compatibility).

### Claude's Discretion
- Exact test structure and assertions, as long as they verify full message history is passed to the agent.
- Whether to add any helper/utilities for multi-turn message construction in tests.
- Internal module layout changes (if any) to support context continuity testing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 5 goal, requirements mapping (CAP-04), and success criteria.
- `.planning/REQUIREMENTS.md` — `CAP-04` definition: "User can verify context continuity across multi-turn chat within a session."

### Prior phase context to preserve
- `.planning/phases/04-capability-invocation-tracing/04-CONTEXT.md` — locked tool/MCP registration pattern that Phase 5 must carry forward (agent now has toolkit).
- `.planning/phases/03-request-scoped-agent-stateless-runtime/03-CONTEXT.md` — locked request-scoped agent creation and near-stateless design that Phase 5 preserves.
- `.planning/phases/02-streaming-chat-contract/02-CONTEXT.md` — locked streaming contract (SSE event lifecycle, messages array format) that Phase 5 must not break.

### Project-level constraints
- `.planning/PROJECT.md` — near-stateless service design constraint, FastAPI API form, `agentscope-runtime` dependency.
- `CLAUDE.md` — repository-level workflow and project constraints.

### Framework documentation (research needed)
- agentscope-runtime `ReActAgent` multi-turn message handling — researcher must verify how the agent processes a messages array with multiple turns and confirm it uses the full history for context.
- agentscope-runtime `InMemoryMemory` interaction with multi-turn `msgs` — researcher must confirm whether passing a multi-turn messages array to `agent(msgs)` automatically populates memory or if memory handling is separate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agent/query.py` — existing `@app.query` handler that creates a fresh `ReActAgent` per request with `InMemoryMemory()`. Phase 5 validates that passing multi-turn `msgs` works correctly with this pattern.
- `src/tools/__init__.py` — shared toolkit with registered tools + MCP (from Phase 4). Phase 5 must preserve tool/MCP functionality in multi-turn scenarios.
- `tests/conftest.py` — shared test fixtures (configured_env, clear_settings_cache, client, valid_payload) that Phase 5 tests can extend.
- `tests/` — established mock patterns from Phase 2-4 for testing without real LLM calls.

### Established Patterns
- Each request creates a fresh `ReActAgent` instance in the `@app.query` async generator (Phase 3 pattern).
- Verification follows `pytest` + smoke script pattern (Phase 1/2/3/4 pattern).
- Mock LLM calls for deterministic testing (Phase 2-4 pattern).
- SSE event lifecycle (typed events, error semantics) from Phase 2 must be preserved.

### Integration Points
- `src/agent/query.py` is the primary integration point — the `msgs` parameter already receives the messages array from the request body. Phase 5 validates multi-turn behavior of the existing flow.
- No new endpoints or modules are needed — this phase is about validating existing behavior with multi-turn input.

</code_context>

<specifics>
## Specific Ideas

- The core validation in Phase 5 is confirming that agentscope-runtime's ReActAgent correctly handles multi-turn message arrays. The current code already passes `msgs` to `agent(msgs)` — if the framework natively uses all messages in the array for context, minimal code changes may be needed.
- Research must confirm: does `agent(msgs)` with a 3-message array result in the agent having access to all 3 messages when generating a response?
- The "session" in CAP-04 is defined by the client's message history, not by a server-side session object.

</specifics>

<deferred>
## Deferred Ideas

- Server-side session state management — Phase 6/7 introduce session persistence.
- Session ID / session identifier — not needed when client manages history.
- Pre-populating InMemoryMemory manually — deferred unless research shows direct msgs passing is insufficient.
- Context window limits / truncation strategies — deferred to future work.
- Multi-user session isolation — v1 is for personal R&D validation.

---

*Phase: 05-context-continuity-validation*
*Context gathered: 2026-04-12*
