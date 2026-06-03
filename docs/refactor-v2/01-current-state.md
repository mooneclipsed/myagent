# Current State

The current project is a compact AgentScope v1 runtime shell. It is useful, but framework-specific concepts are spread through the API, application service, adapter, session, tools, and tracing layers.

## Current Runtime Shape

- `src/agentops/main.py` creates an `agentscope_runtime.engine.AgentApp`.
- `/chat` is registered through `AgentApp.query(framework="agentscope")`.
- `/runtimes/init` creates one process-wide active runtime profile.
- Chat requests use the active runtime profile and build a request-scoped `ReActAgent`.
- Same-session chat streams are serialized with an in-process lock.

## Current Framework Coupling

The strongest AgentScope v1 coupling is in:

- `src/agentops/adapters/agentscope/agent_factory.py`
- `src/agentops/adapters/agentscope/runtime.py`
- `src/agentops/adapters/agentscope/mcp_runtime.py`
- `src/agentops/adapters/agentscope/session_memory.py`
- `src/agentops/adapters/agentscope/tracing.py`
- `src/agentops/sessions/backend.py`
- `src/agentops/tools/registry.py`
- `src/agentops/runtime/skill_runtime.py`

These modules use v1 objects such as `ReActAgent`, `Toolkit`, `Msg`, `ToolResponse`, `InMemoryMemory`, `JSONSession`, and `RedisSession`.

## Current Data Shape

- Runtime init receives separate `tools`, `skills`, `skill_downloads`, and `mcp_servers` lists.
- Model config is resolved during init and stored in the active runtime profile.
- Chat rejects model overrides once a runtime has been initialized.
- Session persistence uses AgentScope v1 memory state through JSON or Redis session backends.
- Tracing binds tenant/session into AgentScope run context and forwards messages to Studio.

## Migration Pressure

The v2 refactor should remove these constraints:

- Runtime profile should not be tied to one model config.
- Session history should not rely only on one framework-private memory format.
- Framework-private objects should not leak into API or platform data structures.
- Workspace lifecycle should be explicit because skills, tools, generated files, and MCP work all need a clear resource boundary.
- Event output should be framework-neutral so UAT and frontend code do not branch on AgentScope-specific stream objects.

## Risks

- AgentScope v2 session and memory behavior must be verified during implementation, especially RedisStorage behavior and event streaming shape.
- Cross-framework session replay will need `standard_messages`, but the first implementation should avoid persisting a duplicate transcript unless the replay requirement becomes concrete.
- Init-level model and prompt configuration keeps runtime behavior easier to reason about, but the implementation must avoid sharing mutable agent memory across sessions.
