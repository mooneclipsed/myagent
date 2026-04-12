# Phase 8: Parity & Demo Flows - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate parity across JSON and Redis session backends and provide documented runnable examples for all capabilities (skill, tool, MCP, resume). Users can run the same core flow against both backends and observe consistent resume behavior, follow a documented demo flow to start and validate the service end-to-end, and run documented examples for each capability class.

This phase does NOT add new capabilities, new API endpoints, or structured tracing. It validates and documents what Phases 1-7 built.

</domain>

<decisions>
## Implementation Decisions

### Skill Definition & Classification
- **D-01:** Research agentscope-runtime's independent skill mechanism during the research phase. If the framework provides a distinct skill API (e.g., pipeline, workflow, service functions), create a separate skill demo example. If skill and tool are the same concept in the framework, document tool examples as covering the skill category with an explicit note.

### Demo Flow Form
- **D-02:** Demo flows are Python automation scripts with built-in assertions. Scripts exit with non-zero code on failure, making them suitable for automated validation.
- **D-03:** One independent script per capability class: `demo_tool.py`, `demo_mcp.py`, `demo_resume.py`, and `demo_skill.py` (pending D-01 research outcome). Each script can run standalone.
- **D-04:** Scripts are placed in `scripts/demos/` directory and executed via `uv run`. Dependency on `httpx` (already a dev dependency).

### Parity Validation Scope
- **D-05:** Parity validation verifies **conversation content consistency** — the same session data resumed from JSON and Redis backends produces the same conversation result. This is the core RES-05 requirement.
- **D-06:** Parity is implemented as a **pytest test** (not a demo script). The test runs the same resume flow against both backends and asserts the final responses are consistent.
- **D-07:** Redis is simulated with **fakeredis** in parity tests. CI remains zero-dependency. Consistent with Phase 7 test pattern.

### Documentation Placement & Structure
- **D-08:** Update **README.md** as the unified getting-started guide. No separate docs/ directory.
- **D-09:** README content is concise and practical: project introduction, quick-start instructions, demo run commands per capability, and expected output examples.

### Claude's Discretion
- Exact pytest test structure for parity validation, as long as it covers conversation content consistency.
- README formatting and section organization.
- Whether demo scripts need a shared helper module (e.g., common httpx client setup).
- Internal structure of each demo script.
- How to handle demo scripts that require a running service (pre-start check, auto-start, or document prerequisite).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 8 goal, requirements mapping (RES-05, DEV-01, DEV-03), and success criteria.
- `.planning/REQUIREMENTS.md` — `RES-05` (consistent JSON/Redis resume behavior), `DEV-01` (documented runnable demo flow), `DEV-03` (documented examples per capability class).

### Prior phase context to preserve
- `.planning/phases/07-redis-session-persistence/07-CONTEXT.md` — locked Redis session backend, backend selection mechanism (`SESSION_BACKEND` env var), fakeredis test pattern, startup health check.
- `.planning/phases/06-json-session-persistence/06-CONTEXT.md` — locked JSON session backend, session API design (session_id in request body), resume behavior, file storage layout.
- `.planning/phases/04-capability-invocation-tracing/04-CONTEXT.md` — locked tool/MCP registration pattern, example tools (get_weather, calculate), MCP server setup. Note: Phase 4 deferred skill vs tool distinction — Phase 8 must resolve this.
- `.planning/phases/05-context-continuity-validation/05-CONTEXT.md` — locked context continuity pattern (client-managed history, near-stateless design).

### Framework capabilities (research needed)
- agentscope-runtime skill mechanism — researcher MUST investigate whether the framework distinguishes skills from tools. Check for pipeline, workflow, service function, or other capability registration APIs beyond `toolkit.register_tool_function`.

### Project-level constraints
- `.planning/PROJECT.md` — near-stateless service design, FastAPI API form, `agentscope-runtime` dependency, session backends constraint (JSON + Redis).
- `CLAUDE.md` — repository-level workflow and project constraints.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agent/session.py` — session factory with `get_session_backend()` singleton. Returns JSONSession or RedisSession based on `SESSION_BACKEND` env var. Parity tests switch this env var between runs.
- `src/agent/query.py` — `@app.query` handler with session save/load logic. Completely backend-agnostic — parity tests reuse this without changes.
- `src/tools/examples.py` — registered example tools (`get_weather`, `calculate`). Demo scripts trigger these via chat prompts.
- `src/mcp/server.py` — MCP server setup. Demo scripts trigger MCP capabilities via chat prompts.
- `tests/test_session.py` — existing session tests for both JSON and Redis backends (457 lines). Parity test can reuse test fixtures and patterns.
- `tests/conftest.py` — shared test fixtures (configured_env, clear_settings_cache, client). Parity tests and demo tests reuse these.
- `scripts/run_service.sh` — service runner. Demo scripts document this as the prerequisite service start command.

### Established Patterns
- Session backend abstraction: `save_session_state` / `load_session_state` interface shared by JSONSession and RedisSession (Phase 6/7 pattern).
- Mock-based testing without real external dependencies (Phase 2-7 pattern).
- fakeredis for Redis simulation in tests (Phase 7 pattern).
- Verification via pytest + smoke scripts (Phase 1-7 pattern).
- SSE streaming responses — demo scripts must handle SSE parsing.

### Integration Points
- Parity test: switches `SESSION_BACKEND` between `"json"` and `"redis"`, runs identical resume flow, compares results.
- Demo scripts: start service → send chat request via HTTP → parse SSE response → assert expected content.
- README.md: references `scripts/demos/` scripts and `scripts/run_service.sh`.

</code_context>

<specifics>
## Specific Ideas

- The parity test is conceptually simple: save a session with JSON backend, save the same session with Redis backend, resume both, compare the agent's response. The abstraction layer makes this straightforward.
- Demo scripts should be self-contained — a user should be able to read the README, start the service, run `uv run scripts/demos/demo_tool.py`, and see a pass/fail result.
- The skill resolution (D-01) is the main research unknown. Everything else is well-defined by prior phase decisions.

</specifics>

<deferred>
## Deferred Ideas

- Session cleanup / TTL / expiration — still deferred. Manual cleanup acceptable for R&D use.
- Session listing / management API — still deferred. Not needed for core validation.
- Structured call-chain tracing (CAP-05) — still deferred to future phase with OpenTelemetry.
- Full API documentation (OpenAPI/Swagger) — deferred. README covers practical usage.
- Performance benchmarking between JSON and Redis backends — deferred. Parity focuses on correctness, not performance.

---

*Phase: 08-parity-demo-flows*
*Context gathered: 2026-04-12*
