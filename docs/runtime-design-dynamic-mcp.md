# Dynamic MCP Runtime Design

## Purpose

This document explains the runtime design used for dynamic MCP bootstrap in the current codebase. The design is implementation-oriented and describes how runtime-scoped MCP resources are created, reused, and cleaned up without mutating the process-wide shared toolkit.

The focus here is the MCP runtime path. Runtime bootstrap can conceptually receive model, tool, skill, and MCP configuration together, but this document only covers the MCP-related runtime design.

## Chosen Model

The implemented model is:

- **single active runtime profile per pod**
- **runtime-owned toolkit**
- **legacy global toolkit retained for non-bootstrap callers**

This means the process can hold one active bootstrapped runtime profile in memory at a time. That runtime owns its own `Toolkit` and MCP client list. Each `/chat` request builds a temporary agent with conversation memory keyed by `session_id`.

The runtime-scoped profile is coordinated from `src/agentops/application/runtime_service.py` and implemented by `src/agentops/adapters/agentscope/runtime.py`.

## Why Dynamic MCP Is Not Written Into the Global Toolkit

The codebase already has a module-level shared toolkit in `src/agentops/tools/__init__.py`. That shared toolkit is useful for:

- built-in deterministic tools
- bundled example skills
- the legacy `/chat` path without runtime bootstrap
- the startup-time example MCP server used for backward compatibility

Dynamic MCP configuration is not added to that global toolkit because bootstrap-time MCP servers are runtime-owned resources rather than process defaults.

Using a runtime-owned toolkit has several advantages:

1. **Isolation**
   - Dynamic MCP registrations belong only to the active runtime profile.
   - They do not leak into unrelated requests.

2. **Clear ownership**
   - The same runtime profile owns the toolkit and the MCP clients.
   - Shutdown and teardown logic can close exactly the resources created during bootstrap.

3. **Safe rollback**
   - Bootstrap is all-or-nothing.
   - If any MCP server fails to connect or register, the partially created MCP clients are closed and the runtime is not published.

4. **Legacy compatibility**
   - The original shared toolkit remains available for callers that still use `/chat` without first bootstrapping a runtime.

The helper `create_base_toolkit()` in `src/agentops/tools/registry.py` is the bridge between the two worlds:

- the request-scoped fallback path still uses the module-level `toolkit`
- the initialization path creates a fresh runtime-owned toolkit

## How This Reuses AgentScope Runtime

This design does not replace `agentscope-runtime`. It reuses the existing framework structure and adds a runtime initialization lifecycle around it.

The following existing framework pieces are still central:

- `AgentApp` from `agentscope_runtime.engine`
- FastAPI routes registered on `AgentApp`
- `ReActAgent` from AgentScope
- `Toolkit.register_mcp_client(...)`
- `stream_printing_messages(...)`

The codebase continues to rely on `AgentApp` as the HTTP/SSE shell:

- `src/agentops/main.py`
- `src/agentops/application/chat_service.py`
- `src/agentops/api/lifecycle.py`

The main change is not the transport layer. The main change is **when and how the `ReActAgent` is created**:

- initialization path: prepare a runtime profile with toolkit/config/MCP resources
- chat path: create a request-scoped agent inside `/chat` from that runtime profile

## Runtime Components

### 1. Base Toolkit Helpers

`src/agentops/tools/registry.py` now provides:

- `register_default_tools(target_toolkit)`
- `register_default_skills(target_toolkit)`
- `create_base_toolkit()`

This allows the bootstrap path to reuse the same default tool and skill registration logic without writing session-scoped MCP configuration into the global singleton.

### 2. Runtime Profile Registry

`src/agentops/application/runtime_service.py` owns the in-memory runtime state.

Important elements:

- `SessionRuntime`
  - `runtime_id`
  - `toolkit`
  - `system_prompt`
  - `mcp_clients`
  - `resolved_config`
  - `mcp_servers`

- single active runtime storage
  - `_active_runtime`
  - `_runtime_lock`

- lifecycle helpers
- `initialize_runtime_from_request(...)`
  - `close_all_session_runtimes()`
  - `get_runtime_profile(...)`

This is intentionally a **single-active-runtime** implementation. It matches the deployment assumption of one `runtime_id` per pod.

### 3. Runtime Routes

`src/agentops/api/runtime.py` adds one API:

- `POST /runtimes/init`

These routes are registered from `src/agentops/main.py` and live alongside the `/chat` endpoint.

### 4. Chat Reuse Path

`src/agentops/application/chat_service.py` handles `/chat` and adds a runtime lookup step.

Behavior:

- if `runtime_id` matches the active initialized runtime, build a temporary agent from the runtime profile and the request `session_id` memory
- otherwise, return an error for unknown runtime ids

This enables reusable runtime-level config and isolated conversation memory.

## End-to-End Flow

## Runtime Initialization

`POST /runtimes/init`

Input:

- required `runtime_id`
- optional `agent_config`
- optional `memory_compression`
- `mcp_servers`

The initialization handler does the following:

1. Validate the requested `runtime_id`
2. Enforce the single-active-runtime-per-pod rule
3. Resolve the effective model configuration
4. Resolve runtime-level memory compression settings
5. Build a fresh runtime-owned toolkit
6. Create MCP clients from request configuration
7. Connect each MCP client
8. Register MCP tools into the runtime-owned toolkit
9. Publish the runtime profile only after all MCP initialization steps succeed

If any MCP server fails during connect or registration:

- already connected clients are closed in reverse order
- the runtime is not published
- initialization returns a clear error

This is a fail-fast initialization design.

## Chat

`POST /chat`

When a request includes `session_id`:

- the handler uses it as the conversation memory key
- same-`session_id` requests are serialized to avoid memory lost updates

When a request includes `runtime_id`:

- the handler checks whether that `runtime_id` maps to the active pod runtime
- if yes, it loads memory by `session_id`, builds a temporary `ReActAgent` with the runtime toolkit/config, runs it, then saves memory
- if no `runtime_id` is provided, it follows the legacy path and creates a temporary per-request agent using the shared global toolkit

When an initialized runtime is reused, dynamic MCP tools are already present because the temporary agent is bound to the runtime-owned toolkit.

This is the key reason dynamic MCP does not need to be visible in the global toolkit: the agent does not ask the process for tools at runtime. It reads its own toolkit.

## Pod Teardown

Application teardown is handled in `src/agentops/api/lifecycle.py`.

The shutdown order is:

1. close all bootstrapped runtime profiles
2. close the configured session backend if needed
3. close the legacy startup MCP clients tracked in `_mcp_clients`

This keeps dynamic runtime-scoped resources separate from the startup-time example MCP path.

## Supported MCP Types and Config Shapes

The current implementation uses AgentScope MCP client types already available in the installed framework.

### `stdio`

Mapped to:

- `StdIOStatefulClient`

Bootstrap config shape:

```json
{
  "name": "time-mcp",
  "type": "stdio",
  "command": "python",
  "args": ["-m", "agentops.resources.mcp_servers.example"],
  "env": {"KEY": "VALUE"},
  "cwd": "/path/to/project"
}
```

Relevant fields currently supported in `src/agentops/config/runtime_models.py`:

- `name`
- `type = "stdio"`
- `command`
- `args`
- `env`
- `cwd`

### `http`

Mapped to:

- `HttpStatefulClient`

Bootstrap config shape:

```json
{
  "name": "remote-mcp",
  "type": "http",
  "transport": "streamable_http",
  "url": "http://example.com/mcp",
  "headers": {"Authorization": "Bearer token"},
  "timeout": 30,
  "sse_read_timeout": 300
}
```

Relevant fields currently supported in `src/agentops/config/runtime_models.py`:

- `name`
- `type = "http"`
- `transport`
- `url`
- `headers`
- `timeout`
- `sse_read_timeout`

### Transport Constraints

For `http`, the transport is limited to:

- `sse`
- `streamable_http`

This is enforced by the bootstrap config schema.

### Not Included in This Design

The current implementation deliberately does **not** include:

- `HttpStatelessClient`
- whitelist policy
- optional/partial MCP bootstrap success
- multi-runtime-per-pod registry

## Session Bootstrap as the Runtime Boundary

Although this document focuses on MCP, the overall runtime boundary is the session bootstrap request.

Conceptually, the bootstrap request is where the client can provide the runtime contract for a session, including:

- model configuration
- tool configuration
- skill configuration
- MCP configuration

In the current implementation, MCP is the primary dynamic capability introduced at bootstrap time. The design keeps the boundary flexible enough for future runtime configuration expansion while avoiding unnecessary changes to the existing `AgentApp` and `/chat` flow.

## Files Involved

Implementation-relevant files in the current codebase:

- `src/agentops/config/runtime_models.py`
- `src/agentops/tools/registry.py`
- `src/agentops/application/runtime_service.py`
- `src/agentops/application/chat_service.py`
- `src/agentops/api/runtime.py`
- `src/agentops/api/lifecycle.py`
- `src/agentops/main.py`
- `tests/test_session_bootstrap.py`
- `scripts/demos/demo_bootstrap_mcp.py`

## Practical Summary

The implemented runtime design can be summarized as:

- bootstrap creates a **session-owned** runtime
- that runtime owns its own toolkit and MCP clients
- `/chat` reuses the runtime's toolkit when `runtime_id` matches
- shutdown and teardown close only the resources that runtime created
- the legacy global toolkit remains available for non-bootstrap callers

This keeps dynamic MCP behavior isolated, reusable, and aligned with the current AgentScope Runtime architecture instead of replacing it.
