# Requirements: AgentScope Skill/Tool/MCP Validation Platform

**Defined:** 2026-04-10
**Core Value:** The platform must provide a stable, repeatable call chain where one chat session can reliably trigger and complete skill/tool/MCP interactions.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Runtime Core

- [x] **CORE-01**: User can call a FastAPI chat endpoint and receive streaming responses (SSE) end-to-end.
- [x] **CORE-02**: User can create/configure a single request-scoped agent from API-provided config payload.
- [x] **CORE-03**: Service keeps runtime near-stateless; request/session state comes from API payload and selected session backend.
- [x] **CORE-04**: User can configure model/provider via `.env` without code changes.
- [x] **CORE-05**: Project is managed with `uv` for dependency and execution workflows.

### Capability Validation

- [ ] **CAP-01**: User can run a chat that triggers skill invocation and observe structured invocation/result events.
- [ ] **CAP-02**: User can run a chat that triggers tool invocation and observe structured invocation/result/error events.
- [ ] **CAP-03**: User can run a chat that triggers MCP invocation and observe structured request/response events.
- [ ] **CAP-04**: User can verify context continuity across multi-turn chat within one session.
- [ ] **CAP-05**: User can inspect call-chain trace data for one run with ordered steps and run correlation ID.

### Resume & Persistence

- [ ] **RES-01**: User can persist session state to JSON-file backend.
- [ ] **RES-02**: User can persist session state to Redis backend.
- [ ] **RES-03**: User can resume chat from previously persisted session in JSON backend.
- [ ] **RES-04**: User can resume chat from previously persisted session in Redis backend.
- [ ] **RES-05**: User can verify JSON/Redis resume behavior is consistent for core flows.

### Dev Workflow & Traceability

- [ ] **DEV-01**: User can start and validate the service through a documented runnable demo flow.
- [x] **DEV-02**: User can track progress through git commits tied to project milestones.
- [ ] **DEV-03**: User can run at least one documented example per capability class (skill/tool/MCP/resume).

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Analysis & Expansion

- **ANL-01**: User can view a call-chain stability score for each run.
- **ANL-02**: User can view context diffs across turns.
- **ANL-03**: User can run multi-agent orchestration/routing scenarios.
- **ANL-04**: User can run batch scenario regression suites.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| GUI-heavy dashboard | v1 prioritizes API-first validation shell and call-chain reliability |
| External multi-user auth/productization | v1 is for personal R&D validation |
| Non-core extensions beyond skill/tool/MCP/context/resume validation | Deferred until core validation is proven |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 2 | Complete |
| CORE-02 | Phase 3 | Complete |
| CORE-03 | Phase 3 | Complete |
| CORE-04 | Phase 1 | Complete |
| CORE-05 | Phase 1 | Complete |
| CAP-01 | Phase 4 | Pending |
| CAP-02 | Phase 4 | Pending |
| CAP-03 | Phase 4 | Pending |
| CAP-04 | Phase 5 | Pending |
| CAP-05 | Phase 4 | Pending |
| RES-01 | Phase 6 | Pending |
| RES-02 | Phase 7 | Pending |
| RES-03 | Phase 6 | Pending |
| RES-04 | Phase 7 | Pending |
| RES-05 | Phase 8 | Pending |
| DEV-01 | Phase 8 | Pending |
| DEV-02 | Phase 1 | Complete |
| DEV-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-11 after Phase 3 completion*
