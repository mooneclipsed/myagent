# Directory Structure

The target source tree should make framework boundaries visible without hiding platform domain concepts behind adapters.

## Proposed Shape

```text
src/agentops/
  main.py
  api/
    routes.py
    schemas.py
  orchestration/
    runtime.py
    execution.py
    models.py
    events.py
    messages.py
    workspace.py
    observability.py
  capabilities/
    models.py
    registry.py
    tools/
    skills/
    mcp/
  frameworks/
    base.py
    registry.py
    agentscope_v2/
      runtime.py
      execution.py
      capabilities.py
      sessions.py
      observability.py
    microsoft_agent_framework/
      README.md
  config/
    settings.py
    models.py
  integrations/
    skill_api_client.py
  resources/
    mcp_servers/
```

## Responsibilities

`api` owns the HTTP boundary: FastAPI route registration, request/response schemas, validation mapping, and streaming response wiring. There is no extra `interfaces/http` nesting until a second interface type exists.

`api/routes.py` can contain both runtime init and chat routes in the first implementation. Split it later only if route volume or ownership makes the file hard to navigate.

`api/schemas.py` owns HTTP-specific schemas only. Framework-neutral domain models belong in `orchestration/models.py` or `capabilities/models.py`.

`orchestration/runtime.py` owns active runtime lifecycle, runtime replacement, agent spec resolution, capability init orchestration, and profile state. It must not expose one mutable agent memory object across sessions. It may keep private in-memory active runtime state that contains the framework runtime handle, but that handle must not appear in public response schemas.

`orchestration/execution.py` owns chat request orchestration, request metadata resolution, session-isolated agent execution creation, event sequencing, and response streaming.

`orchestration/messages.py` owns `StandardMessage` schemas and conversion helpers. It does not persist transcripts in the first implementation.

`orchestration/workspace.py` owns runtime-scoped workspace creation and cleanup.

`orchestration/observability.py` owns platform trace metadata and trace references.

`capabilities` owns framework-neutral capability declarations and local capability implementations.

`frameworks` owns concrete framework adapters and all framework-private object conversion.

`frameworks/registry.py` owns framework selection. It maps init-time framework values such as `agentscope` to concrete adapter factories. In this design, public framework value `agentscope` maps to the `frameworks/agentscope_v2` adapter. The first implementation should use an explicit in-process registry, not plugin discovery.

## Model Placement

Multiple `models.py` files are allowed only when each one owns a different boundary.

`api/schemas.py` contains HTTP-only request and response schemas. These models may include transport-specific aliases, response envelopes, validation error shapes, and streaming response documentation. They should translate into platform models quickly and should not contain framework logic.

`orchestration/models.py` contains framework-neutral AgentOps domain models, such as `RuntimeProfile`, `AgentSpec`, `ExecutionConfig`, `WorkspaceRef`, `TraceRef`, and runtime status values. These are the core data structures used by orchestration services.

`capabilities/models.py` contains capability declaration schemas, such as `tool`, `mcp`, and `skill` configs, capability summaries, and capability validation results. These models describe what an agent can use, not how a framework registers it.

Framework adapter packages should avoid a broad `models.py` unless they need framework-private DTOs. If needed, those models must stay private to the adapter and must not leak into `api` or `orchestration`.

Prefer moving shared cross-boundary types upward. For example, if both `api` and `orchestration` use a type as business data, it belongs in `orchestration/models.py`; if only the HTTP layer uses it, it belongs in `api/schemas.py`.

## Migration Notes

The first implementation should keep changes narrow by moving behavior into the new structure in phases. Do not introduce Microsoft Agent Framework code before AgentScope v2 is stable.

The current `adapters/agentscope` package can be replaced by `frameworks/agentscope_v2` during the migration.
