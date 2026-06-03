# Directory Structure

The target source tree should make framework boundaries visible without hiding platform domain concepts behind adapters.

## Proposed Shape

```text
src/agentops/
  main.py
  interfaces/
    http/
      app.py
      runtime_routes.py
      chat_routes.py
      schemas.py
  platform/
    runtime/
      service.py
      models.py
      lifecycle.py
    execution/
      service.py
      models.py
      events.py
    messages/
      models.py
    workspaces/
      service.py
      models.py
    observability/
      service.py
      models.py
  capabilities/
    models.py
    registry.py
    tools/
    skills/
    mcp/
  frameworks/
    base.py
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

`interfaces/http` owns FastAPI routes, request validation, response shapes, and SSE wiring.

`platform/runtime` owns active runtime lifecycle, runtime replacement, agent spec resolution, capability init orchestration, and profile state. It must not expose one mutable agent memory object across sessions.

`platform/execution` owns chat request orchestration, request metadata resolution, session-isolated agent execution creation, event sequencing, and response streaming.

`platform/messages` owns `standard_messages` schemas and conversion helpers. It does not persist transcripts in the first implementation.

`platform/workspaces` owns runtime-scoped workspace creation and cleanup.

`platform/observability` owns platform trace metadata and trace references.

`capabilities` owns framework-neutral capability declarations and local capability implementations.

`frameworks` owns concrete framework adapters and all framework-private object conversion.

## Migration Notes

The first implementation should keep changes narrow by moving behavior into the new structure in phases. Do not introduce Microsoft Agent Framework code before AgentScope v2 is stable.

The current `adapters/agentscope` package can be replaced by `frameworks/agentscope_v2` during the migration.
