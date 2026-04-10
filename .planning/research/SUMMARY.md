# Project Research Summary

**Project:** AgentScope Skill/Tool/MCP Validation Platform
**Domain:** agent testing platform for tool/skill/MCP/context validation with resumable sessions
**Researched:** 2026-04-10
**Confidence:** MEDIUM

## Executive Summary

This project is an agent testing shell that validates deterministic call chains for tool/skill/MCP flows with resumable sessions. Experts build this class of product by combining streaming chat APIs (SSE), strict event schemas, append-only run logs, and pluggable session backends so that every step in the chain can be replayed and verified across resumes.

The recommended approach is a FastAPI + AgentScope runtime integration with a request-scoped agent factory, structured streaming events (not raw tokens), and a canonical session schema persisted to JSON and Redis. Build the streaming contract and event log first, then layer in AgentScope runtime, tool/MCP gateways, and persistence parity tests. This aligns with the architectural separation between API, orchestration, runtime adapters, and persistence.

Key risks center on streaming lifecycle mismatches, incomplete session state serialization, and backend divergence. Mitigate by enforcing explicit stream phases, persisting full tool/MCP state with IDs, and running shared fixtures across JSON and Redis. Add observability early so regressions in call-chain stability are detectable.

## Key Findings

### Recommended Stack

FastAPI (with Starlette) and Uvicorn provide the streaming SSE foundation needed for incremental event delivery. Python 3.11 is the stable runtime for async streaming and best compatibility with AgentScope and MCP SDKs. Redis complements a JSON file backend to test real-world resume semantics, while Pydantic v2 enforces strict schemas for requests, events, and session state.

**Core technologies:**
- Python 3.11: primary runtime — stable async stack with broad FastAPI/MCP ecosystem support.
- FastAPI 0.135.3: API framework — built-in SSE/streaming patterns and strong typing.
- agentscope-runtime 1.1.3: agent runtime under test — required for config-driven agent creation.
- modelcontextprotocol 1.27.0: MCP client/server — official SDK for tool/resource/prompt protocols.
- Redis 7.x: session persistence — resumable sessions and parity testing with JSON.

### Expected Features

MVP focuses on streaming chat with structured tool/MCP events, deterministic run capture, and session resume across JSON and Redis. Differentiators emphasize objective stability scoring and backend comparison harnesses once core traces are reliable. v2+ defers multi-agent orchestration, replay, and scenario runners until single-agent invariants are stable.

**Must have (table stakes):**
- Streaming chat endpoint with request-scoped agent — users expect live incremental outputs and consistent session behavior.
- Deterministic run capture + structured errors — enables reproducibility and actionable failures.
- Tool/skill/MCP invocation tracing — core evidence for call-chain stability.
- Context state inspection + session persistence/resume (JSON + Redis) — validates resumability and backend behavior.
- Config-driven agent instantiation — required by the runtime evaluation goals.

**Should have (competitive):**
- Call-chain stability score — objective pass/fail summaries from traces.
- Backend comparison harness — diff JSON vs Redis resume behavior.
- Context diff visualizer — detect unintended context drift.

**Defer (v2+):**
- Scenario runner (YAML test cases) — batch validation once manual runs stabilize.
- Step-by-step replay — depends on full deterministic capture across providers.
- Multi-agent orchestration — only after single-agent invariants are solved.

### Architecture Approach

The architecture centers on a FastAPI streaming API that delegates to an orchestration layer with a request-scoped agent factory and a deterministic call-chain runner. A canonical session schema and append-only event log drive both SSE streaming and persistence. Runtime adapters isolate AgentScope and tool/MCP details, while storage adapters keep JSON and Redis behavior interchangeable and testable.

**Major components:**
1. API layer (FastAPI chat route + SSE streaming) — validates requests and emits structured events with IDs.
2. Orchestration layer (session manager, agent factory, call-chain runner) — coordinates deterministic execution and logging.
3. Runtime/integration layer (AgentScope runtime, tool/MCP gateway) — normalizes external calls and policies.
4. Persistence layer (JSON + Redis stores) — implements a single session schema with parity tests.
5. Observability layer (events + logging) — captures timing, errors, and call-chain telemetry.

### Critical Pitfalls

1. **Streaming lifecycle mismatch** — avoid by defining explicit stream phases (thinking/tool_call/tool_result/final) and gating output on tool completion.
2. **Agent continuity breaks on rehydrate** — avoid by persisting a versioned agent config snapshot and validating registry parity on resume.
3. **Tool/MCP state not serialized** — avoid by storing tool queues, results, MCP session IDs, and context window state in a canonical schema.
4. **Backpressure ignored in streaming** — avoid by bounded queues, disconnect cancellation, and timeouts.
5. **Backend divergence (JSON vs Redis)** — avoid by shared schemas and fixture-based parity tests.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Streaming Contract + Core Event Log
**Rationale:** Streaming semantics and event IDs are the foundation for deterministic validation and resume.
**Delivers:** `/chat` SSE endpoint, structured event schema, append-only event log, basic observability.
**Addresses:** streaming chat endpoint, deterministic run capture, structured error diagnostics.
**Avoids:** streaming lifecycle mismatch, backpressure issues, missing telemetry.

### Phase 2: AgentScope Integration + Tool/MCP Traceability
**Rationale:** Once the contract exists, integrate the runtime and normalize tool/MCP calls to validate call-chain stability.
**Delivers:** request-scoped agent factory, tool/MCP gateway, structured tool/MCP tracing, MCP conformance checks.
**Addresses:** tool/skill/MCP invocation tracing, config-driven agent instantiation.
**Avoids:** agent continuity breaks, opaque errors, MCP capability assumptions, non-idempotent tool side effects.

### Phase 3: Session Persistence + Resume Parity
**Rationale:** Persistence depends on stable event schemas and complete tool/MCP state capture.
**Delivers:** canonical session schema, JSON + Redis stores, resume flow with Last-Event-ID, parity tests.
**Addresses:** session persistence + resume, context state inspection, backend comparison harness (if feasible).
**Avoids:** missing tool/MCP state, backend divergence, context bloat.

### Phase 4: Analysis Enhancements (Optional v1.x)
**Rationale:** Add differentiators only after core stability is verified.
**Delivers:** call-chain stability score, context diff visualizer, reporting exports.
**Addresses:** competitive features without destabilizing core flows.

### Phase Ordering Rationale

- Streaming and event schema must precede runtime integration to ensure deterministic logs.
- Tool/MCP traceability depends on stable event phases and call IDs.
- Persistence and resume require complete state serialization, so they follow runtime integration.
- Differentiators rely on reliable traces and snapshots, so they come last.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** AgentScope runtime + MCP integration semantics need conformance validation.
- **Phase 3:** Session schema design and parity testing strategies may require deeper validation.

Phases with standard patterns (skip research-phase):
- **Phase 1:** FastAPI SSE streaming + event logging is well-documented and stable.
- **Phase 4:** Stability scoring and diff visualizers follow standard analytics patterns once data is available.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Based on official docs and PyPI versions, but not yet validated in project context. |
| Features | MEDIUM | Based on project requirements and domain knowledge; limited external validation. |
| Architecture | MEDIUM | Standard patterns with AgentScope integration; needs implementation proof. |
| Pitfalls | MEDIUM | Practitioner knowledge; no external sources cited. |

**Overall confidence:** MEDIUM

### Gaps to Address

- AgentScope runtime boundaries for config-driven rehydration and resume need hands-on validation during Phase 2.
- Canonical session schema (tool/MCP state and context policy) must be formalized and tested in Phase 3.
- MCP capability coverage and conformance tests require early prototyping to prevent late surprises.

## Sources

### Primary (HIGH confidence)
- https://fastapi.tiangolo.com/uk/tutorial/server-sent-events/ — SSE streaming patterns
- https://runtime.agentscope.io/en/intro.html — AgentScope runtime overview
- https://runtime.agentscope.io/en/agent_app.html — AgentApp integration patterns

### Secondary (MEDIUM confidence)
- https://fastapi.tiangolo.com/release-notes/ — FastAPI 0.135.3 streaming updates
- https://modelcontextprotocol.io/docs/sdk — MCP SDK overview and tiers
- https://redis.io/docs/latest/develop/clients/ — Redis client usage patterns
- https://www.starlette.io/responses/ — streaming responses and SSE
- https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events — SSE behavior and reconnection

### Tertiary (LOW confidence)
- Project context in `/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md` — internal requirements
- Pitfalls based on practitioner experience — requires validation in implementation

---
*Research completed: 2026-04-10*
*Ready for roadmap: yes*
