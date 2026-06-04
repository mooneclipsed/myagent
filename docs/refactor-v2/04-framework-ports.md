# Framework Ports

Framework ports define the minimal interface between AgentOps orchestration code and a concrete agent framework.

Framework selection is explicit. Init requests provide a framework value such as `agentscope`; in this design, `agentscope` means AgentScope v2. `frameworks/registry.py` resolves that value to the concrete AgentScope v2 adapter. The first implementation should not use dynamic plugin discovery.

Unknown framework values must fail validation with a clear message such as `Framework '<name>' does not exist.`

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
- Load skills. Remote skills are downloaded during init and passed to the adapter as local runtime workspace paths.
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
- Create fresh framework session state when saved state is missing or incompatible.

Expected operations:

- `load_session`
- `save_session`
- `create_session`

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
- Mapping of frontend `session_id` into AgentScope v2 session, user, agent, or service identifiers.
- Agent Service event stream shape.
- Whether AgentScope v2 native service/stream support can satisfy AgentOps `/chat` SSE; otherwise AgentOps owns FastAPI SSE conversion.
- Workspace binding behavior.
- Tool, MCP, and skill registration APIs.
- Trace metadata behavior in AgentScope Studio and Phoenix.

## Microsoft Agent Framework Adapter

The Microsoft Agent Framework adapter is not implemented in the first migration. The design only reserves adapter boundaries so future work does not require changing public platform schemas.
