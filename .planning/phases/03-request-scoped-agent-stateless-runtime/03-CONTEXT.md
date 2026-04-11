# Phase 3: Request-Scoped Agent & Stateless Runtime - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver per-request agent creation driven by API-provided configuration while keeping the service near-stateless. This phase transforms the current hardcoded `.env`-only agent creation into a request-configurable system. It does not add skill/tool/MCP invocation, context continuity, or session persistence — those belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Agent Configuration Source & Format
- **D-01:** Agent config is minimally overridable per request: `model_name`, `api_key`, and `base_url` only. `sys_prompt`, formatter, and agent type remain fixed (not request-configurable in this phase).
- **D-02:** Field-level fallback: each config field independently falls back to `.env` defaults when not provided in the request. A request can override just `model_name` while keeping `api_key` and `base_url` from `.env`.
- **D-03:** Request body extends the existing `messages` array with a top-level `agent_config` object. Backward-compatible — requests without `agent_config` use `.env` defaults (existing Phase 2 behavior preserved). Example: `{ "messages": [...], "agent_config": { "model_name": "gpt-4o" } }`.
- **D-04:** The `agent_config` object is optional in the request body. When absent, all model config comes from `.env` (same as Phase 2 behavior).

### Verification & Observability
- **D-05:** Verification follows the established pattern: `pytest` automated tests + smoke script. Tests validate that requests with different configs result in agents using the correct configuration.
- **D-06:** Stateless verification includes both instance isolation (each request gets a fresh agent) AND config trace logging — the service should log the effective config used per request so that stateless behavior is observable, not just assumed.
- **D-07:** Success criteria tests: (1) a request with `agent_config` creates an agent using those values, (2) a second request with different `agent_config` uses the new values without server restart, (3) a request without `agent_config` falls back to `.env` defaults.

### Claude's Discretion
- Exact `agent_config` field names and pydantic model structure, as long as they cover `model_name`, `api_key`, `base_url` with field-level `.env` fallback.
- Exact logging format and level for config tracing, as long as it's observable in test output.
- Internal module layout for config resolution logic.
- Exact test structure and smoke script shape, following established Phase 1/2 patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 3 goal, requirements mapping (CORE-02, CORE-03), and success criteria.
- `.planning/REQUIREMENTS.md` — `CORE-02` (request-scoped agent from API config) and `CORE-03` (near-stateless runtime) definitions.

### Prior phase context to preserve
- `.planning/phases/02-streaming-chat-contract/02-CONTEXT.md` — locked streaming contract decisions that Phase 3 must carry forward (request body shape, SSE event model, error semantics).
- `.planning/phases/02-streaming-chat-contract/02-VERIFICATION.md` — validated Phase 2 baseline including current agent creation pattern in `query.py`.
- `.planning/phases/01-environment-workflow-baseline/01-CONTEXT.md` — locked `.env` configuration contract (D-01 through D-05) that Phase 3 extends with request-level overrides.

### Project-level constraints
- `.planning/PROJECT.md` — near-stateless service design constraint, FastAPI API form, `agentscope-runtime` dependency.
- `CLAUDE.md` — repository-level workflow and project constraints.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agent/query.py` — existing `@app.query` handler that already creates a fresh agent per request. Phase 3 modifies the config source from hardcoded `.env` to request-provided with fallback.
- `src/core/settings.py` — existing `Settings` class with 4 required `.env` fields (`MODEL_PROVIDER`, `MODEL_NAME`, `MODEL_API_KEY`, `MODEL_BASE_URL`) and `lru_cache` singleton. Phase 3 adds request-level override resolution on top.
- `src/main.py` — `AgentApp` instance with `/process` endpoint. The query handler registration via `@app.query(framework="agentscope")` stays the same.
- `src/app/lifespan.py` — startup validation continues to enforce `.env` as the baseline config.
- `tests/conftest.py` — shared test fixtures (configured_env, clear_settings_cache, client, valid_payload) that Phase 3 tests can extend.
- `scripts/verify_phase2.sh` — established verification script pattern to follow.

### Established Patterns
- Agent creation happens inside the `@app.query` async generator — each request gets a fresh `ReActAgent` instance.
- Configuration is centralized in typed settings loaded from `.env` — Phase 3 adds a request-layer on top but `.env` remains the fallback base.
- Verification is reproducible via `uv` commands + scripts — Phase 3 should follow this pattern.
- SSE event lifecycle (typed events, error semantics) is established in Phase 2 and must be preserved.

### Integration Points
- The `@app.query` handler in `query.py` is the primary integration point — config resolution logic plugs in before `ReActAgent` creation.
- Request body parsing: the existing `msgs` parameter from the framework needs to coexist with the new `agent_config` field.
- Settings singleton (`get_settings()`) continues to provide defaults — Phase 3 adds a merge/override layer.
- Test infrastructure (conftest fixtures) needs extension for agent config payloads.

</code_context>

<specifics>
## Specific Ideas

- The key transformation in Phase 3 is small in scope but architecturally significant: move from "config from .env only" to "config from request with .env fallback". This is the foundation for all later phases (tracing, context, persistence) which will rely on request-scoped agent behavior.
- Keep `sys_prompt`, formatter, and agent type fixed for now — making them configurable is a natural extension for later phases if needed.

</specifics>

<deferred>
## Deferred Ideas

- Configurable `sys_prompt` per request — could be useful for testing but not required for CORE-02/CORE-03.
- Configurable agent type per request (e.g., switching from ReActAgent to other types) — deferred until multi-agent patterns are explored.
- Configurable formatter per request — deferred, same rationale.
- Skill/tool/MCP invocation trace events — Phase 4.
- Multi-turn context continuity — Phase 5.
- JSON/Redis session persistence — Phases 6-8.

</deferred>

---

*Phase: 03-request-scoped-agent-stateless-runtime*
*Context gathered: 2026-04-11*
