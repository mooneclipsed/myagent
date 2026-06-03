# Framework Ports

Framework ports define the minimal interface between AgentOps platform code and a concrete agent framework.

## FrameworkRuntimePort

Responsibilities:

- Initialize a framework runtime from a `RuntimeProfile` candidate.
- Close framework resources when the active runtime is replaced.
- Expose framework storage and workspace bindings.
- Report framework capability summaries.
- Return the internal runtime or service handle needed to execute future requests.

Expected operations:

- `initialize_runtime`
- `close_runtime`
- `validate_capabilities`
- `describe_runtime`

`describe_runtime` returns a public-safe runtime description after initialization. It can include framework name, status, loaded capability summaries, workspace reference, storage mode, and tracing mode. It must not expose internal framework handles, API keys, raw prompts, or framework-private session state.

## AgentExecutionPort

Responsibilities:

- Convert platform messages into framework messages.
- Apply `ExecutionConfig`.
- Create or acquire a session-isolated framework execution object from the active `AgentSpec`.
- Execute one chat request.
- Convert framework stream objects into platform events.
- Persist framework-private state through the framework storage layer.

Expected operations:

- `prepare_execution`
- `stream_chat`
- `finalize_execution`

## CapabilityPort

Responsibilities:

- Register local tools.
- Connect and register MCP servers.
- Load local and remote skills.
- Return normalized capability summaries.

Expected operations:

- `register_tool`
- `register_mcp`
- `register_skill`
- `close_capabilities`

## FrameworkSessionPort

Responsibilities:

- Load framework-private session state.
- Save framework-private session state.
- Replay `standard_messages` only if a future optional transcript store is enabled.

Expected operations:

- `load_session`
- `save_session`
- `replay_standard_messages` when optional transcript replay exists.

## ObservabilityPort

Responsibilities:

- Bind tenant, runtime, session, and request metadata.
- Attach effective model and prompt hash to trace metadata when supported.
- Return trace references for platform events.

Expected operations:

- `bind_context`
- `record_execution_metadata`
- `flush`

## AgentScope v2 Adapter

The AgentScope v2 adapter is responsible for mapping platform runtime, workspace, storage, capability, and event concepts to AgentScope v2 APIs.

Implementation must verify:

- RedisStorage support for session and memory persistence.
- Agent Service event stream shape.
- Workspace binding behavior.
- Tool, MCP, and skill registration APIs.
- Trace metadata behavior in AgentScope Studio and Phoenix.

## Microsoft Agent Framework Adapter

The Microsoft Agent Framework adapter is not implemented in the first migration. The design only reserves adapter boundaries so future work does not require changing public platform schemas.
