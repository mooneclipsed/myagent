# Dynamic MCP Runtime Design

## Purpose

This document explains the runtime design used for dynamic MCP bootstrap in the current codebase. The design is implementation-oriented and describes how session-scoped MCP resources are created, reused, and cleaned up without mutating the process-wide shared toolkit.

The focus here is the MCP runtime path. Session bootstrap can conceptually receive model, tool, skill, and MCP configuration together, but this document only covers the MCP-related runtime design.

## Chosen Model

The implemented model is:

- **single active session runtime per pod**
- **session-owned toolkit**
- **legacy global toolkit retained for non-bootstrap callers**

This means the process can hold one active bootstrapped session runtime in memory at a time. That runtime owns its own `Toolkit`, `ReActAgent`, memory instance, and MCP client list.

The session-scoped runtime is implemented in `src/agent/session_runtime.py`.

## Why Dynamic MCP Is Not Written Into the Global Toolkit

The codebase already has a module-level shared toolkit in `src/tools/__init__.py`. That shared toolkit is useful for:

- built-in deterministic tools
- bundled example skills
- the legacy `/process` path
- the startup-time example MCP server used for backward compatibility

Dynamic MCP configuration is not added to that global toolkit because bootstrap-time MCP servers are session-owned resources rather than process defaults.

Using a session-owned toolkit has several advantages:

1. **Isolation**
   - Dynamic MCP registrations belong only to the active session runtime.
   - They do not leak into unrelated requests.

2. **Clear ownership**
   - The same runtime object owns the toolkit, the agent, and the MCP clients.
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

### 2. Session Runtime Registry

`src/agent/session_runtime.py` owns the in-memory runtime state.

Important elements:

- `SessionRuntime`
  - `session_id`
  - `toolkit`
  - `agent`
  - `memory`
  - `mcp_clients`
  - `resolved_config`
  - `mcp_servers`

- single active runtime storage
  - `_active_runtime`
  - `_runtime_lock`

- lifecycle helpers
  - `bootstrap_session_runtime(...)`
  - `shutdown_session_runtime(...)`
  - `close_all_session_runtimes()`
  - `get_session_runtime(...)`

This is intentionally a **single-active-session** implementation. It matches the current runtime assumption of one active session per pod.

### 3. Session Routes

`src/app/session_routes.py` adds two APIs:

- `POST /sessions/bootstrap`
- `POST /sessions/{session_id}/shutdown`

These routes are registered from `src/main.py` and live alongside the existing `/process` endpoint.

### 4. Query Reuse Path

`src/agent/query.py` keeps the existing `@app.query` handler but adds a runtime lookup step.

Behavior:

- if `session_id` matches an active bootstrapped runtime, use the prebuilt `runtime.agent`
- otherwise, fall back to the legacy per-request path

This preserves backward compatibility while enabling a reusable bootstrapped runtime for dynamic MCP sessions.

## End-to-End Flow

## Bootstrap

`POST /sessions/bootstrap`

Input:

- optional `session_id`
- optional `agent_config`
- `mcp_servers`

The bootstrap handler does the following:

1. Validate the requested `session_id`
2. Enforce the single-active-session rule
3. Resolve the effective model configuration
4. Load saved session memory from the configured session backend
5. Build a fresh session-owned toolkit via `create_base_toolkit()`
6. Create MCP clients from request configuration
7. Connect each MCP client
8. Register MCP tools into the session-owned toolkit
9. Create a `ReActAgent` bound to that toolkit and memory
10. Publish the runtime only after all MCP initialization steps succeed

If any MCP server fails during connect or registration:

- already connected clients are closed in reverse order
- the runtime is not published
- bootstrap returns a clear error

This is a fail-fast bootstrap design.

## Process

`POST /process`

When a request includes `session_id`:

- the handler checks whether that `session_id` maps to the active session runtime
- if yes, it reuses the bootstrapped `ReActAgent`
- if no, it follows the legacy path and creates a temporary per-request agent using the shared global toolkit

When a bootstrapped runtime is reused, dynamic MCP tools are already present because the reused agent is bound to the session-owned toolkit.

This is the key reason dynamic MCP does not need to be visible in the global toolkit: the agent does not ask the process for tools at runtime. It reads its own toolkit.

## Shutdown

`POST /sessions/{session_id}/shutdown`

Shutdown closes the active runtime for that session by:

1. validating the session id
2. locating the active runtime
3. closing all runtime-owned MCP clients in LIFO order
4. clearing the active runtime from memory

Unknown session ids return `404`.

## Pod Teardown

Application teardown is handled in `src/app/lifespan.py`.

The shutdown order is:

1. close all bootstrapped session runtimes
2. close the configured session backend if needed
3. close the legacy startup MCP clients tracked in `_mcp_clients`

This keeps dynamic session-scoped resources separate from the startup-time example MCP path.

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
