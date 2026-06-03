# Target Architecture

The target architecture separates platform orchestration from framework execution. AgentScope v2 becomes the first framework adapter, not the shape of the whole application.

## Architecture Principles

- Platform data structures are framework-neutral.
- Framework adapters own framework-private conversion and lifecycle details.
- Runtime init prepares agent configuration, capabilities, workspace, storage, and framework services.
- Chat execution creates or acquires a session-isolated agent execution object from the immutable runtime profile.
- Frontend-owned session IDs are usable across runtime replacements within the same tenant.
- Cross-framework replay can use `standard_messages` in a future optional transcript store, but the first implementation should rely on framework-private session state.

## Runtime Lifecycle

```text
init(runtime_id)
  -> close active runtime if present
  -> delete runtime workspace
  -> create runtime workspace
  -> resolve model_config from request or environment
  -> resolve system_prompt and prompt_hash
  -> validate capabilities
  -> download runtime-scoped skills
  -> connect MCP servers
  -> create framework runtime/service resources
  -> publish RuntimeProfile
```

Every init replaces the active runtime, even when the same `runtime_id` is used. This matches the current Pod behavior and avoids partial mutation of active agents.

### Framework Runtime Resources

`create framework runtime/service resources` means preparing framework-level resources that are safe to share across sessions because they do not contain one session's mutable conversation state.

For AgentScope v2 this may include:

- framework initialization and tracing setup.
- framework storage client such as RedisStorage.
- workspace binding for the runtime workspace.
- model/client factory built from `AgentSpec`.
- capability registry or toolkit equivalent for tools, MCP, and skills.
- connected MCP clients owned by the runtime.
- loaded skill metadata and runtime-local skill files.
- an agent service, agent factory, or lightweight agent template if the framework supports per-session isolation.

It must not include one shared mutable agent memory object used by all sessions. If a framework agent instance stores conversation memory internally, it must be created per session or per request, or the framework service must prove session isolation through `session_id`.

## Chat Lifecycle

```text
chat(runtime_id, session_id, execution_config, messages)
  -> validate active runtime_id
  -> read AgentSpec from active RuntimeProfile
  -> load or create framework session state
  -> optionally replay standard_messages if a future transcript store is enabled
  -> create or acquire session-isolated framework agent execution
  -> run framework agent/service
  -> stream platform events
  -> optionally record standard_messages if a future transcript store is enabled
  -> let framework storage persist private memory/state
```

Chat requires `session_id`. Optional `request_id` is returned in every streamed event when provided. If no tenant is provided, the session belongs to the default tenant namespace.

## Storage Boundary

Framework-private storage is the primary storage boundary for the first implementation.

Framework-private storage owns the data needed by one framework to resume its own agent execution. For AgentScope v2, RedisStorage is the preferred storage for AgentScope memory, session state, and any framework-private agent state. These records should be treated as opaque by the platform and accessed through the framework adapter.

`standard_messages` are not persisted by default because that would duplicate framework memory. A future optional transcript store can persist `standard_messages` for cross-framework replay if that requirement becomes concrete.

The normal same-framework path should load conversation history from framework-private session state. `standard_messages` must not be injected again when framework memory already contains the relevant history.

When a runtime changes, the adapter should check whether framework-private state is compatible with the active runtime profile. Compatibility can start with `framework`, `prompt_hash`, and relevant capability or agent spec fingerprints. If compatible, use framework-private state. If missing or incompatible, the first implementation should fail clearly or start from empty history unless optional transcript replay has been implemented.

This avoids storing the same conversation twice while leaving a clear extension point for future cross-framework replay.

## Workspace Boundary

The workspace is runtime-scoped and keyed by `runtime_id`. It contains runtime-local skill files, generated artifacts, and tool-visible files.

Chat requests can reference the active workspace, but they do not own it. Reinitializing the runtime deletes and rebuilds the workspace.

## Observability Boundary

Observability is split into platform events, framework traces, and application logs.

Platform events are the API-facing stream returned to callers. They should include correlation metadata that AgentOps controls:

- `runtime_id`
- `tenant_id`
- `session_id`
- optional `request_id`
- `framework`
- `effective_model` from the active `AgentSpec`
- `prompt_hash` from the active `AgentSpec`
- `sequence`
- optional `trace_ref`

Framework traces are owned by AgentScope Studio, Phoenix, or OpenTelemetry. Those systems keep their own run, span, and trace identifiers. AgentOps should not require clients to provide a public `run_id`. Instead, framework adapters bind platform metadata to the framework trace context when supported and return `trace_ref` when identifiers are available.

Application logs are for service diagnostics only. Logs may include non-secret correlation metadata such as `runtime_id`, `session_id`, `request_id`, `framework`, and `model_name`. Logs must not include API keys, full secret-bearing URLs, raw system prompts, or full message payloads by default.

The adapter is responsible for flushing framework traces at the end of a request when the framework exposes that capability.
