# Quick Task 260413-n8u: 支持根据请求 JSON 动态加载 MCP 配置：先聚焦 MCP，不做白名单；支持 stdio 和 http 两类；先形成可执行实现方案，不立刻改代码。 - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Task Boundary

Design a future implementation that lets a session bootstrap request provide MCP configuration via JSON, with initial support for `stdio` and `http` MCP servers. The goal of this quick task is to define a concrete implementation plan only; no code changes, whitelist policy, or dynamic skill-loading implementation are included.

</domain>

<decisions>
## Implementation Decisions

### Resource scope and assembly
- Dynamic MCP resources must not be registered into the global shared toolkit.
- The initial session bootstrap should create a session-scoped agent/toolkit by extending the existing built-in/default capabilities with the MCP servers declared in the bootstrap payload.
- Existing static defaults may remain as baseline capabilities, but dynamic MCP registration must stay isolated from other sessions.

### HTTP configuration model
- External config keeps `type: "http"` and must expose `transport`.
- Supported HTTP transports are `sse` and `streamable_http`.
- The initial design should align with AgentScope's HTTP MCP client model rather than inventing a new transport abstraction.

### Session lifecycle
- MCP resources are session-scoped, not per-message request scoped.
- A session bootstrap request provides the runtime configuration for model, tool, skill, and MCP setup, and the pod then reuses that initialized agent/resources for subsequent turns.
- The initial runtime assumption is one active session per pod.
- Resources are closed either by an explicit shutdown/close request or during pod teardown.
- HTTP MCP should follow stateful session semantics in the initial design; stateless HTTP client support is out of scope for this first implementation plan.

### Failure handling
- If any declared MCP server fails to initialize or register during session bootstrap, session startup fails with a clear error.
- The initial design does not attempt partial availability or optional MCP configuration flags.

### Claude's Discretion
- Exact naming of the bootstrap endpoint or request schema sections.
- The internal registry object shape used to track session resources.
- Whether explicit close is exposed as a dedicated API or a management command, as long as pod teardown remains a safe cleanup path.

</decisions>

<specifics>
## Specific Ideas

- Current static MCP registration lives in `src/app/lifespan.py` and the current shared toolkit construction lives in `src/tools/__init__.py`.
- Current agent creation is per request in `src/agent/query.py`; future work should separate session bootstrap from per-turn processing rather than extending global process state.
- The service is intended to run in Kubernetes pods, so lifecycle design should treat pod teardown as a valid cleanup path for session-scoped resources.

</specifics>

<canonical_refs>
## Canonical References

- `CLAUDE.md` — project constraints, GSD workflow requirement, and language/document conventions.
- `.planning/PROJECT.md` — platform goals, near-statelessness guidance, and current milestone context.
- `.planning/STATE.md` — current shipped state and prior quick-task context.

</canonical_refs>
