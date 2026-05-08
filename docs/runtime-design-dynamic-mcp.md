# Dynamic MCP Runtime Design

## Purpose

This document explains the runtime design used for dynamic MCP bootstrap in the current codebase. The design is implementation-oriented and describes how runtime-scoped MCP resources are created, reused, and cleaned up without mutating the process-wide shared toolkit.

The focus here is the MCP runtime path. Runtime bootstrap can conceptually receive model, tool, skill, and MCP configuration together, but this document only covers the MCP-related runtime design.

## Chosen Model

The implemented model is:

- **single active runtime profile per pod**
- **runtime-owned toolkit**
- **legacy global toolkit retained for non-bootstrap callers**

This means the process can hold one active bootstrapped runtime profile in memory at a time. That runtime owns its own `Toolkit` and MCP client list. Each `/process` request builds a temporary agent with conversation memory keyed by `session_id`.

The runtime-scoped profile is implemented in `src/agent/session_runtime.py`.

## Why Dynamic MCP Is Not Written Into the Global Toolkit

The codebase already has a module-level shared toolkit in `src/tools/__init__.py`. That shared toolkit is useful for:

- built-in deterministic tools
- bundled example skills
- the legacy `/process` path
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
   - The original shared toolkit remains available for callers that still use `/process` without first bootstrapping a session.

The helper `create_base_toolkit()` in `src/tools/__init__.py` is the bridge between the two worlds:

- the legacy path still uses the module-level `toolkit`
- the bootstrap path creates a fresh toolkit by calling `create_base_toolkit()`

## How This Reuses AgentScope Runtime

This design does not replace `agentscope-runtime`. It reuses the existing framework structure and only adds a bootstrap lifecycle around it.

The following existing framework pieces are still central:

- `AgentApp` from `agentscope_runtime.engine`
- `@app.query` for the `/process` chat entrypoint
- `ReActAgent` from AgentScope
- `Toolkit.register_mcp_client(...)`
- `stream_printing_messages(...)`

The codebase continues to rely on `AgentApp` as the HTTP/SSE shell:

- `src/main.py`
- `src/agent/query.py`
- `src/app/lifespan.py`

The main change is not the transport layer. The main change is **when and how the `ReActAgent` is created**:

- legacy path: create an agent inside `/process`
- bootstrap path: create the agent once during session bootstrap, then reuse it on later `/process` calls

## Runtime Components

### 1. Base Toolkit Helpers

`src/tools/__init__.py` now provides:

- `register_default_tools(target_toolkit)`
- `register_default_skills(target_toolkit)`
- `create_base_toolkit()`

This allows the bootstrap path to reuse the same default tool and skill registration logic without writing session-scoped MCP configuration into the global singleton.

### 2. Runtime Profile Registry

`src/agent/session_runtime.py` owns the in-memory runtime state.

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
  - `bootstrap_session_runtime(...)`
  - `shutdown_runtime_profile(...)`
  - `close_all_session_runtimes()`
  - `get_runtime_profile(...)`

This is intentionally a **single-active-runtime** implementation. It matches the deployment assumption of one `runtime_id` per pod.

### 3. Runtime Routes

`src/app/session_routes.py` adds two APIs:

- `POST /runtimes/bootstrap`
- `POST /runtimes/{runtime_id}/shutdown`

These routes are registered from `src/main.py` and live alongside the existing `/process` endpoint.

### 4. Query Reuse Path

`src/agent/query.py` keeps the existing `@app.query` handler but adds a runtime lookup step.

Behavior:

- if `runtime_id` matches the active bootstrapped runtime, build a temporary agent from the runtime profile and the request `session_id` memory
- otherwise, fall back to the legacy per-request path

This preserves backward compatibility while enabling reusable runtime-level config and isolated conversation memory.

## End-to-End Flow

## Bootstrap

`POST /runtimes/bootstrap`

Input:

- required `runtime_id`
- optional `agent_config`
- `mcp_servers`

The bootstrap handler does the following:

1. Validate the requested `runtime_id`
2. Enforce the single-active-runtime-per-pod rule
3. Resolve the effective model configuration
4. Build a fresh runtime-owned toolkit
5. Create MCP clients from request configuration
6. Connect each MCP client
7. Register MCP tools into the runtime-owned toolkit
8. Publish the runtime profile only after all MCP initialization steps succeed

If any MCP server fails during connect or registration:

- already connected clients are closed in reverse order
- the runtime is not published
- bootstrap returns a clear error

This is a fail-fast bootstrap design.

## Process

`POST /process`

When a request includes `session_id`:

- the handler uses it as the conversation memory key
- same-`session_id` requests are serialized to avoid memory lost updates

When a request includes `runtime_id`:

- the handler checks whether that `runtime_id` maps to the active pod runtime
- if yes, it loads memory by `session_id`, builds a temporary `ReActAgent` with the runtime toolkit/config, runs it, then saves memory
- if no `runtime_id` is provided, it follows the legacy path and creates a temporary per-request agent using the shared global toolkit

When a bootstrapped runtime is reused, dynamic MCP tools are already present because the temporary agent is bound to the runtime-owned toolkit.

This is the key reason dynamic MCP does not need to be visible in the global toolkit: the agent does not ask the process for tools at runtime. It reads its own toolkit.

## Shutdown

`POST /runtimes/{runtime_id}/shutdown`

Shutdown closes the active runtime profile by:

1. validating the runtime id
2. locating the active runtime
3. closing all runtime-owned MCP clients in LIFO order
4. clearing the active runtime from memory

Unknown runtime ids return `404`.

## Pod Teardown

Application teardown is handled in `src/app/lifespan.py`.

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
  "args": ["-m", "src.mcp.server"],
  "env": {"KEY": "VALUE"},
  "cwd": "/path/to/project"
}
```

Relevant fields currently supported in `src/core/config.py`:

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

Relevant fields currently supported in `src/core/config.py`:

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
- dynamic skill loading implementation

## Session Bootstrap as the Runtime Boundary

Although this document focuses on MCP, the overall runtime boundary is the session bootstrap request.

Conceptually, the bootstrap request is where the client can provide the runtime contract for a session, including:

- model configuration
- tool configuration
- skill configuration
- MCP configuration

In the current implementation, MCP is the primary dynamic capability introduced at bootstrap time. The design keeps the boundary flexible enough for future runtime configuration expansion while avoiding unnecessary changes to the existing `AgentApp` and `/process` flow.

## Files Involved

Implementation-relevant files in the current codebase:

- `src/core/config.py`
- `src/tools/__init__.py`
- `src/agent/session_runtime.py`
- `src/agent/query.py`
- `src/app/session_routes.py`
- `src/app/lifespan.py`
- `src/main.py`
- `tests/test_session_bootstrap.py`
- `scripts/demos/demo_bootstrap_mcp.py`

## Practical Summary

The implemented runtime design can be summarized as:

- bootstrap creates a **session-owned** runtime
- that runtime owns its own toolkit and MCP clients
- `/process` reuses the runtime's agent when `session_id` matches
- shutdown and teardown close only the resources that runtime created
- the legacy global toolkit remains available for non-bootstrap callers

This keeps dynamic MCP behavior isolated, reusable, and aligned with the current AgentScope Runtime architecture instead of replacing it.
