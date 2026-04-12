# AgentScope Skill/Tool/MCP Validation Platform

## What This Is

A FastAPI-based agent testing shell for personal R&D validation, built around `agentscope-runtime` with `uv` project management. The platform creates an agent per client request and supports streaming chat responses so we can quickly test skill calls, tool calls, MCP calls, and context handling behavior. It also explores resume/session recovery with both JSON-file and Redis backends.

## Core Value

The platform must provide a stable, repeatable call chain where one chat session can reliably trigger and complete skill/tool/MCP interactions.

## Requirements

### Validated

- [x] Use `.env` for model configuration and use `uv` to manage dependencies and execution. Validated in Phase 01: Environment & Workflow Baseline.
- [x] Use git to track implementation progress and milestones. Validated in Phase 01: Environment & Workflow Baseline.

### Active

- [ ] Validate skill invocation, tool invocation, MCP invocation, and context management in end-to-end chat flows.
- [ ] Implement resume/session persistence and recovery using both JSON file storage and Redis storage.
- [ ] Keep service design as stateless as practical, with runtime context coming from API requests/session backends.

### Validated (Phase 2)

- [x] Build a streaming chat API with SSE endpoint using AgentApp (agentscope-runtime). Validated in Phase 02: Streaming Chat Contract.

### Validated (Phase 6)

- [x] Persist and resume sessions using a JSON-file backend (RES-01, RES-03). Validated in Phase 06: JSON Session Persistence.

### Validated (Phase 7)

- [x] Persist and resume sessions using a Redis backend (RES-02, RES-04). Validated in Phase 07: Redis Session Persistence.

### Out of Scope

- Multi-agent orchestration/routing in v1 — initial target is single-agent chat for faster validation loops.
- Non-core platform features beyond the testing shell — deferred to future versions after core call-chain validation.

## Context

The project is meant for personal development-time experimentation, not external production use in v1. Primary objective is confidence in call-chain stability across skill/tool/MCP integration before expanding functionality. `agentscope-runtime` capability boundaries (especially config-driven agent creation and resume support) are part of the exploration scope and should be validated through runnable API flows.

## Constraints

- **Runtime Dependency**: Core runtime should rely on `agentscope-runtime` — this is the primary framework under evaluation.
- **API Form**: Must expose chat via FastAPI with streaming responses — enables direct conversational testing.
- **State Model**: Prefer near-stateless server design — avoid unnecessary in-memory coupling.
- **Session Backends**: Resume must support both JSON-file and Redis storage — required for comparative validation.
- **Environment**: Model/provider config comes from `.env` — keep config externalized.
- **Tooling**: Use `uv` for project/dependency management — standardize local workflow.
- **Versioning**: Track progress with git commits — preserve development checkpoints.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| v1 serves personal R&D validation | Optimize for fast local learning loops over productization | — Pending |
| Single-agent chat in v1 | Reduce complexity and isolate core call-chain verification | — Pending |
| Include skill/tool/MCP/context validation in v1 scope | Directly targets the primary technical unknowns | — Pending |
| Implement both JSON and Redis resume backends in v1 | Compare local and service-style persistence behavior early | — Pending |
| FastAPI + streaming interface | Match intended chat testing interaction model | — Pending |
| Use `uv` and `.env` conventions | Keep setup reproducible and configuration explicit | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after Phase 07 completion*