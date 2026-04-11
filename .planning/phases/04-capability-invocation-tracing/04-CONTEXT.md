# Phase 4: Capability Invocation Tracing - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Register tool, skill, and MCP capabilities with the ReActAgent and prove end-to-end invocation works through the streaming chat endpoint. This phase focuses on making capability calls functional — structured tracing/observability (CAP-05, and the "observe structured events" portions of CAP-01/02/03) is deferred to a future phase where OpenTelemetry or a similar SDK will be integrated.

</domain>

<decisions>
## Implementation Decisions

### Tool Registration
- **D-01:** Use agentscope-runtime's framework-native tool registration mechanism (e.g., `@app.tool` or `agent.tool()`) to register tools with the ReActAgent. Do not build a custom registration layer.
- **D-02:** Register tools at service startup time. All requests share the same set of registered tools. Do not implement per-request dynamic tool registration in this phase.
- **D-03:** Include concrete example tools (e.g., `get_weather`, `calculate`) for end-to-end verification. These tools must be simple, deterministic, and callable through the streaming chat flow without external dependencies.

### MCP Integration
- **D-04:** Use agentscope-runtime's built-in MCP support for MCP server/tool registration. Do not add a separate MCP SDK dependency.
- **D-05:** Include a local example MCP server for end-to-end verification. The server should be simple (e.g., file read, time query), have no network dependencies, and be startable alongside the main service.

### Scope Adjustment — Tracing Deferred
- **D-06:** Structured call-chain tracing (CAP-05: run correlation ID, ordered step inspection, structured invocation/result/error events) is deferred to a future phase. The future implementation will use OpenTelemetry or a similar observability SDK rather than a custom tracing solution.
- **D-07:** Phase 4 success criteria is revised: the user must be able to trigger tool and MCP calls through chat and confirm the calls execute (visible in agent responses). The "observe structured trace events" requirement is not in scope.

### Claude's Discretion
- Exact example tool implementations, as long as they cover at least one tool call and one MCP call end-to-end.
- Exact MCP server implementation and protocol details.
- Internal module layout for tool/MCP registration code.
- How tools are declared in the agentscope-runtime framework (decorator vs config vs programmatic API).
- Verification approach, following established Phase 1/2/3 patterns (pytest + smoke script).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance
- `.planning/ROADMAP.md` — Phase 4 goal, requirements mapping (CAP-01, CAP-02, CAP-03, CAP-05), and success criteria. Note: tracing portion of these requirements is deferred per D-06/D-07.
- `.planning/REQUIREMENTS.md` — CAP-01, CAP-02, CAP-03, CAP-05 definitions.

### Prior phase context to preserve
- `.planning/phases/03-request-scoped-agent-stateless-runtime/03-CONTEXT.md` — locked request-scoped agent creation pattern that Phase 4 extends with tool/MCP capabilities.
- `.planning/phases/02-streaming-chat-contract/02-CONTEXT.md` — locked streaming contract (SSE event lifecycle, error semantics) that must be preserved when tool calls are added.
- `.planning/phases/01-environment-workflow-baseline/01-CONTEXT.md` — locked `.env` configuration contract.

### Project-level constraints
- `.planning/PROJECT.md` — near-stateless service design, FastAPI API form, `agentscope-runtime` dependency.
- `CLAUDE.md` — repository-level workflow and project constraints.

### Framework documentation (research needed)
- agentscope-runtime tool registration API — researcher must investigate how ReActAgent registers and invokes tools.
- agentscope-runtime MCP integration API — researcher must investigate built-in MCP support capabilities.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agent/query.py` — existing `@app.query` handler that creates a fresh `ReActAgent` per request. Phase 4 extends this to register tools/MCP on the agent before invocation.
- `src/core/config.py` — `AgentConfig` and `resolve_effective_config` for request-scoped config. Tool registration may need to interact with the agent config system.
- `src/main.py` — `AgentApp` instance. Tool/MCP registration may happen here at startup or in the query handler.
- `src/app/lifespan.py` — startup validation hook. Tool/MCP server initialization could be added here.
- `tests/conftest.py` — shared test fixtures that Phase 4 tests can extend.

### Established Patterns
- Each request creates a fresh `ReActAgent` instance in the `@app.query` async generator.
- Configuration is centralized in typed settings loaded from `.env`.
- Verification is reproducible via `uv` commands + scripts (Phase 1/2/3 pattern).
- SSE event lifecycle (typed events, error semantics) from Phase 2 must be preserved.

### Integration Points
- `src/agent/query.py` is the primary integration point — tool registration plugs into the agent creation flow before `agent(msgs)` is called.
- `src/main.py` / `src/app/lifespan.py` are potential startup-time registration points for tool definitions and MCP server connections.
- Example tools and MCP server will need new module files (e.g., `src/tools/`, `src/mcp/`).

</code_context>

<specifics>
## Specific Ideas

- The core transformation in Phase 4 is making the agent "capable" — going from a plain chat agent to one that can invoke registered tools and MCP services during a conversation.
- Research must investigate the exact agentscope-runtime API for tool registration on ReActAgent. The framework may use decorators, config objects, or programmatic registration.
- Example tools should be deterministic (no external API calls) to keep tests stable and reproducible.
- The local MCP server should be startable as a subprocess or in-process alongside the main service.

</specifics>

<deferred>
## Deferred Ideas

- Structured call-chain trace events (CAP-05: run correlation ID, ordered step inspection) — deferred to future phase with OpenTelemetry integration.
- Observing structured invocation/result/error events for tool/skill/MCP calls (the "observe" portions of CAP-01, CAP-02, CAP-03) — deferred alongside tracing.
- Per-request dynamic tool registration — startup-time fixed registration is sufficient for R&D validation.
- Configurable tool set per request — deferred until tool registration is proven stable.
- Skill invocation (CAP-01 mentions "skill") — agentscope-runtime may not distinguish skills from tools; researcher should clarify this during research phase.

</deferred>

---

*Phase: 04-capability-invocation-tracing*
*Context gathered: 2026-04-11*
