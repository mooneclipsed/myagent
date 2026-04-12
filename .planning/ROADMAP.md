# Roadmap: AgentScope Skill/Tool/MCP Validation Platform

## Overview

This roadmap delivers a stable, repeatable call-chain validation shell by building the streaming contract first, then layering in request-scoped runtime behavior, capability tracing, resumable persistence (JSON then Redis), and finally parity validation with runnable demo flows.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Environment & Workflow Baseline** - Config and tooling ready for reproducible runs. (completed 2026-04-11)
- [x] **Phase 2: Streaming Chat Contract** - SSE chat endpoint delivers end-to-end streaming responses. (completed 2026-04-11)
- [x] **Phase 3: Request-Scoped Agent & Stateless Runtime** - Per-request agent creation with minimal server state. (completed 2026-04-11)
- [x] **Phase 4: Capability Invocation Tracing** - Skill/tool/MCP calls emit structured trace events. (completed 2026-04-11)
- [x] **Phase 5: Context Continuity Validation** - Multi-turn context stays consistent within a session. (completed 2026-04-12)
- [ ] **Phase 6: JSON Session Persistence** - Persist and resume sessions via JSON backend.
- [ ] **Phase 7: Redis Session Persistence** - Persist and resume sessions via Redis backend.
- [ ] **Phase 8: Parity & Demo Flows** - Parity checks and documented runnable examples.

## Phase Details

### Phase 1: Environment & Workflow Baseline
**Goal**: Users can configure models and run the project with a reproducible workflow and visible progress checkpoints.
**Depends on**: Nothing (first phase)
**Requirements**: CORE-04, CORE-05, DEV-02
**Success Criteria** (what must be TRUE):
  1. User can set model/provider configuration via `.env` and see it applied without code changes.
  2. User can install dependencies and run the service using `uv` commands.
  3. User can observe milestone progress in git history with commits aligned to roadmap phases.
**Plans**: 2 plans
Plans:
- [x] 01-01-PLAN.md — Enforce typed `.env` startup contract, `uv` verification path, and git checkpoint traceability.
- [x] 01-02-PLAN.md — Close CORE-05 run-path gap with uvicorn dependency, service run script, and verification evidence updates.

### Phase 2: Streaming Chat Contract
**Goal**: Users can call a chat endpoint and receive streaming responses end-to-end.
**Depends on**: Phase 1
**Requirements**: CORE-01
**Success Criteria** (what must be TRUE):
  1. User can open a streaming chat request and receive incremental SSE events until completion.
  2. User can repeat the same request and observe the stream completes without server-side state drift.
**Plans**: 2 plans
Plans:
- [x] 02-01-PLAN.md -- Replace bare FastAPI with AgentApp, add agentscope-runtime dependency, and register SSE streaming query handler at /process.
- [x] 02-02-PLAN.md -- Verify SSE streaming contract with automated tests (lifecycle, errors, repeat stability) and reproducible smoke script.

### Phase 3: Request-Scoped Agent & Stateless Runtime
**Goal**: Users can create a per-request agent from API config while keeping the service near-stateless.
**Depends on**: Phase 2
**Requirements**: CORE-02, CORE-03
**Success Criteria** (what must be TRUE):
  1. User can submit an API config payload and see a request-scoped agent created for that request.
  2. User can make a second request with different config and see the new config applied without server restart.
  3. User can verify runtime state is sourced from request/session backends rather than in-memory coupling.
**Plans**: 2 plans
Plans:
- [x] 03-01-PLAN.md -- Add AgentConfig model, config resolution logic, and update query handler for request-scoped agent creation.
- [x] 03-02-PLAN.md -- Verify request-scoped config with automated tests and Phase 3 smoke script.

### Phase 4: Capability Invocation Tracing
**Goal**: Users can trigger tool and MCP calls through chat and confirm the calls execute (visible in agent responses). Structured tracing (CAP-05, observe structured events) deferred to future phase per D-06/D-07.
**Depends on**: Phase 3
**Requirements**: CAP-01, CAP-02, CAP-03, CAP-05
**Success Criteria** (what must be TRUE):
  1. User can trigger a tool call through chat and see the tool result in the agent response.
  2. User can trigger an MCP call through chat and see the MCP tool result in the agent response.
  3. Tool functions are registered at startup and shared across all requests.
  4. MCP server subprocess starts at service startup and closes cleanly on shutdown.
**Plans**: 2 plans
Plans:
- [x] 04-01-PLAN.md -- Register example tool functions and MCP server into shared Toolkit, integrate MCP lifecycle into lifespan, pass toolkit to per-request ReActAgent.
- [x] 04-02-PLAN.md -- Verify tool registration, MCP lifecycle, and response format with automated tests and Phase 4 smoke script.

### Phase 5: Context Continuity Validation
**Goal**: Users can verify context continuity across multi-turn chat within a session.
**Depends on**: Phase 4
**Requirements**: CAP-04
**Success Criteria** (what must be TRUE):
  1. User can carry a multi-turn conversation and observe prior turns influencing later responses.
  2. User can confirm the session retains context across multiple turns without losing earlier messages.
**Plans**: 1 plan
Plans:
- [x] 05-01-PLAN.md -- Write multi-turn context continuity tests (CAP-04) and Phase 5 verification script.

### Phase 6: JSON Session Persistence
**Goal**: Users can persist and resume sessions using a JSON-file backend.
**Depends on**: Phase 5
**Requirements**: RES-01, RES-03
**Success Criteria** (what must be TRUE):
  1. User can persist a session to the JSON backend and confirm the session state is stored.
  2. User can resume a chat from the persisted JSON session and continue the conversation.
**Plans**: 2 plans
Plans:
- [x] 06-01-PLAN.md -- Create session module, update settings with SESSION_DIR, wire JSONSession load/save into query handler and lifespan.
- [x] 06-02-PLAN.md -- Verify session persistence, resume round-trip, and backward compatibility with automated tests and Phase 6 smoke script.

### Phase 7: Redis Session Persistence
**Goal**: Users can persist and resume sessions using a Redis backend.
**Depends on**: Phase 6
**Requirements**: RES-02, RES-04
**Success Criteria** (what must be TRUE):
  1. User can persist a session to Redis and confirm the session state is stored.
  2. User can resume a chat from the persisted Redis session and continue the conversation.
**Plans**: 2 plans
Plans:
- [x] 07-01-PLAN.md -- Add Redis settings, extend session factory for JSONSession/RedisSession, add lifespan health check.
- [x] 07-02-PLAN.md -- Verify Redis session persistence with automated tests and Phase 7 verification script.

### Phase 8: Parity & Demo Flows
**Goal**: Users can validate parity across JSON/Redis and run documented examples for all capabilities.
**Depends on**: Phase 7
**Requirements**: RES-05, DEV-01, DEV-03
**Success Criteria** (what must be TRUE):
  1. User can run the same core flow against JSON and Redis backends and observe consistent resume behavior.
  2. User can follow a documented demo flow to start and validate the service end-to-end.
  3. User can run documented examples for skill, tool, MCP, and resume capabilities.
**Plans**: 2 plans
Plans:
- [x] 08-01-PLAN.md — Register example skill, create RES-05 parity test for JSON/Redis session backend consistency.
- [x] 08-02-PLAN.md — Create demo scripts for all capability classes and update README.md as unified getting-started guide.

## Progress

**Execution Order:**
Phases execute in numeric order: 2 → 2.1 → 2.2 → 3 → 3.1 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Environment & Workflow Baseline | 2/2 | Complete   | 2026-04-11 |
| 2. Streaming Chat Contract | 2/2 | Complete | 2026-04-11 |
| 3. Request-Scoped Agent & Stateless Runtime | 2/2 | Complete | 2026-04-11 |
| 4. Capability Invocation Tracing | 2/2 | Complete | 2026-04-11 |
| 5. Context Continuity Validation | 1/1 | Complete | 2026-04-12 |
| 6. JSON Session Persistence | 0/2 | Not started | - |
| 7. Redis Session Persistence | 0/0 | Not started | - |
| 8. Parity & Demo Flows | 0/2 | Not started | - |
