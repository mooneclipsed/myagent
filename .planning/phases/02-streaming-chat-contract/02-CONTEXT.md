# Phase 2: Streaming Chat Contract - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a FastAPI chat endpoint that supports end-to-end streaming responses over SSE. This phase defines the streaming request/response contract and proves repeatable stream completion, but does not yet expand into request-scoped agent construction, capability tracing, context continuity, or session persistence.

</domain>

<decisions>
## Implementation Decisions

### Request Contract
- **D-01:** The Phase 2 chat endpoint accepts a `messages` array as the request body shape, rather than a single `message` string.
- **D-02:** The request contract should stay minimal in this phase; additional runtime/session/config fields belong to later phases unless absolutely required to make streaming work.

### Streaming Event Model
- **D-03:** Streaming responses use typed SSE events rather than raw text-only chunks.
- **D-04:** The event lifecycle should be explicit and testable, with distinct event types for stream start, incremental output, and normal completion.

### Error Semantics
- **D-05:** Validation and request-shape failures should return normal HTTP errors before streaming starts.
- **D-06:** Once a stream has started, runtime failures should be emitted as SSE error events and then terminate the stream cleanly.

### Verification Strategy
- **D-07:** Phase 2 acceptance should combine automated `pytest` coverage with a runnable smoke-test script, following the reproducible workflow style established in Phase 1.
- **D-08:** Repeat-request stability in this phase means the stream lifecycle completes reliably on repeated calls without server-side state drift; exact response text does not need to be identical across runs.

### Claude's Discretion
- Exact endpoint path naming and internal module layout.
- Exact event names and payload field names, as long as they preserve the typed lifecycle above and remain easy to verify.
- Exact smoke-test command shape, as long as it is reproducible via `uv` and aligns with the endpoint contract.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 2 goal, dependency on Phase 1, and success criteria for end-to-end SSE chat streaming.
- `.planning/REQUIREMENTS.md` — `CORE-01` definition and milestone traceability for the streaming chat contract.
- `.planning/PROJECT.md` — project-level constraints: FastAPI API form, near-stateless service design, `.env` configuration, and `uv` workflow expectations.

### Established baseline to preserve
- `.planning/phases/01-environment-workflow-baseline/01-CONTEXT.md` — locked startup/config decisions that Phase 2 must carry forward.
- `.planning/phases/01-environment-workflow-baseline/01-VERIFICATION.md` — validated Phase 1 baseline and reproducible verification style.
- `CLAUDE.md` — repository-level workflow and project constraints, including GSD usage and Chinese conversation preference.

No external specs — requirements are fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/main.py` — existing FastAPI application entrypoint to extend with the first chat route.
- `src/app/lifespan.py` — existing startup hook that already enforces fail-fast settings validation before serving requests.
- `src/core/settings.py` — existing typed `.env` settings loader that Phase 2 should continue to rely on rather than introducing ad-hoc config loading.
- `scripts/run_service.sh` — current canonical service boot command that should remain the main way to start the app.
- `scripts/verify_phase1.sh` — example of the current reproducible verification style (`uv`, pytest, smoke check, git evidence).

### Established Patterns
- Startup validation happens in FastAPI lifespan before requests are served.
- Configuration is centralized in typed settings loaded from `.env`.
- Verification is expected to be reproducible from `uv` commands plus scripts, not only by manual testing.
- The current codebase has no existing chat, SSE, or `agentscope-runtime` integration yet, so Phase 2 will define the first streaming contract from a clean baseline.

### Integration Points
- The new streaming endpoint should be added to the existing FastAPI app in `src/main.py` or a directly-related route module wired from it.
- Phase 2 verification should integrate with the current script-based workflow so downstream phases inherit one clear way to run and validate the service.
- The contract created here becomes the foundation for Phase 3 request-scoped runtime work and later capability-tracing/session phases.

</code_context>

<specifics>
## Specific Ideas

- Keep Phase 2 focused on the streaming API contract itself; do not pull request-scoped agent configuration into the request body yet unless it is the minimum needed to make the stream work.
- Prefer a contract that is easy to assert from tests and easy to extend in later phases.

</specifics>

<deferred>
## Deferred Ideas

- Request-scoped agent configuration payloads — Phase 3.
- Skill/tool/MCP invocation trace events — Phase 4.
- Multi-turn context continuity semantics — Phase 5.
- JSON/Redis session persistence and resume behavior — Phases 6-8.

</deferred>

---

*Phase: 02-streaming-chat-contract*
*Context gathered: 2026-04-11*
