# AgentScope v2 Adapter

This package is reserved for the AgentScope v2 adapter.

Public framework value `agentscope` resolves to this package through
`agentops.frameworks.registry`.

Verified AgentScope v2 API surface:

- Agent: `agentscope.agent.Agent`
- State: `agentscope.state.AgentState`
- Models: `agentscope.model.OpenAIChatModel`, `agentscope.model.DashScopeChatModel`
- Credentials: `agentscope.credential.OpenAICredential`, `agentscope.credential.DashScopeCredential`
- Toolkit: `agentscope.tool.Toolkit`
- Built-in tools: `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`
- MCP: `agentscope.mcp.MCPClient`, `StdioMCPConfig`, `HttpMCPConfig`
- App/session/storage: `agentscope.app.create_app`, `SessionManager`, `SessionConfig`, `RedisStorage`, `LocalWorkspaceManager`

Important implementation notes:

- `Toolkit` requires stateful MCP clients to be connected before registration.
- MCP client construction and toolkit construction are intentionally separate.
- Skills are passed as local paths. Remote skills must be downloaded into the runtime workspace before adapter construction.
- Runtime-level resources are built by `AgentScopeRuntimeBuilder`.
- `AgentScopeRuntimeBuilder.close` closes connected MCP clients in reverse order.
- Agent construction for chat is still separate from runtime-level resource construction so one mutable agent state is not shared across sessions.
- `agentops.orchestration.runtime_factory.create_runtime_manager()` assembles `RuntimeManager` with `AgentScopeRuntimeBuilder` for `framework="agentscope"`.
- AgentScope v2 `Agent` is not callable. Chat execution uses `Agent.reply` for completed turns and `Agent.reply_stream` for framework events.
- Frontend `session_id` maps to `AgentState(session_id=...)` in `AgentScopeSessionExecutor`.
