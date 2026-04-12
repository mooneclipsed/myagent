# AgentScope Skill/Tool/MCP Validation Platform

## What This Is

A FastAPI-based agent testing shell for personal R&D validation, built around `agentscope-runtime` with `uv` project management. The platform creates an agent per client request and supports streaming chat responses so we can quickly test skill calls, tool calls, MCP calls, and context handling behavior. It also explores resume/session recovery with both JSON-file and Redis backends.

## Core Value

The platform must provide a stable, repeatable call chain where one chat session can reliably trigger and complete skill/tool/MCP interactions.

## Current State

**Shipped:** v1.0 (2026-04-12)
- 8 phases completed, 15 plans executed, 52 tests passing
- 17/18 requirements satisfied (CAP-05 structured tracing deferred by design)
- Streaming SSE chat endpoint with per-request ReActAgent
- Tool (get_weather, calculate) and MCP (get_time) capability invocation
- Dual session persistence backends (JSON-file and Redis) with parity verified
- 4 runnable demo scripts + unified README getting-started guide

**Archived:** [v1.0 Roadmap](milestones/v1.0-ROADMAP.md) | [v1.0 Requirements](milestones/v1.0-REQUIREMENTS.md)

## Next Milestone Goals

*v2.0 not yet defined. Potential areas based on v1.0 findings:*
- CAP-05 structured call-chain tracing (deferred from v1.0)
- Multi-agent orchestration/routing (ANL-03)
- Batch scenario regression suites (ANL-04)
- Call-chain stability scoring (ANL-01)

Run `/gsd-new-milestone` to define v2.0 scope.

<details>
<summary>v1.0 Project Context (archived)</summary>

## Requirements

### Validated

- [x] Use `.env` for model configuration and use `uv` to manage dependencies and execution. Validated in Phase 01.
- [x] Use git to track implementation progress and milestones. Validated in Phase 01.
- [x] Build a streaming chat API with SSE endpoint using AgentApp (agentscope-runtime). Validated in Phase 02.
- [x] Persist and resume sessions using a JSON-file backend (RES-01, RES-03). Validated in Phase 06.
- [x] Persist and resume sessions using a Redis backend (RES-02, RES-04). Validated in Phase 07.
- [x] Validate JSON/Redis resume behavior consistency (RES-05). Validated in Phase 08.
- [x] Documented runnable demo flow for all capabilities (DEV-01, DEV-03). Validated in Phase 08.

### Active

- [ ] Keep service design as stateless as practical, with runtime context coming from API requests/session backends.

### Out of Scope

- Multi-agent orchestration/routing in v1 — initial target is single-agent chat for faster validation loops.
- Non-core platform features beyond the testing shell — deferred to future versions after core call-chain validation.

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
| v1 serves personal R&D validation | Optimize for fast local learning loops over productization | Validated |
| Single-agent chat in v1 | Reduce complexity and isolate core call-chain verification | Validated |
| Include skill/tool/MCP/context validation in v1 scope | Directly targets the primary technical unknowns | Validated |
| Implement both JSON and Redis resume backends in v1 | Compare local and service-style persistence behavior early | Validated |
| FastAPI + streaming interface | Match intended chat testing interaction model | Validated |
| Use `uv` and `.env` conventions | Keep setup reproducible and configuration explicit | Validated |

</details>

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-12 after v1.0 milestone archival*
