# Migration Roadmap

This roadmap keeps the refactor staged so each phase has a concrete validation point.

## Phase 1: Documentation And Contracts

Status: completed.

- Finalize data model docs.
- Finalize event protocol docs.
- Finalize framework port docs.
- Identify v1 objects that must not leak into new platform schemas.

Validation:

- Design docs describe every current core capability.
- No implementation changes are required in this phase.

## Phase 2: Platform Schemas

Status: completed.

- Added Pydantic models for `RuntimeProfile`, `AgentSpec`, `ExecutionConfig`, `StandardMessage`, capability envelope, workspace refs, and platform events.
- Kept schemas framework-neutral.
- Added unit tests for validation rules.

Validation:

- Unknown capability types fail validation.
- Secrets are excluded from events and `StandardMessage`.
- `session_id` is required for chat schemas.
- Chat request uses `input` for the current user input and does not require full history.

## Phase 3: Runtime And Workspace Lifecycle

Status: completed.

- Added framework-neutral `RuntimeManager`.
- Added runtime-scoped workspace staging, promotion, replacement, and cleanup.
- Treat workspace as an AgentOps-managed temporary artifact directory, not as the security boundary for agent permissions.
- Default local workspace root is `.agentops/workspaces`; Pod deployments can override it with `AGENTOPS_WORKSPACE_ROOT=/app/workspace`.
- Workspace deletion requires an AgentOps marker file so unmanaged directories are never removed with bare `rmtree`.
- Kept init all-or-nothing: failed framework build removes staging workspace and does not publish a runtime.
- Kept this phase independent from the old v1 `application.runtime_service`; API wiring moves with the AgentScope v2 adapter work.

Validation:

- Repeated init closes the previous runtime and replaces workspace contents.
- Repeated init with the same `runtime_id` closes previous framework resources while keeping the new workspace.
- Failed capability init does not publish a runtime.
- Closing the active runtime removes its workspace.
- Unmanaged workspace directories are preserved and cause initialization to fail.
- `uv run pytest tests/test_refactor_v2_schemas.py tests/test_refactor_v2_runtime_manager.py -q` passes.

## Phase 4: AgentScope v2 Adapter

Status: in progress. AgentScope `2.0.0` dependency and construction APIs are verified; runtime wiring, session persistence, and streaming are still pending.

- Added initial `agentscope_v2` adapter helpers for agent spec, model, toolkit, MCP client, and skill path construction.
- Added `AgentScopeRuntimeBuilder` for runtime-level Toolkit construction, MCP connection, resource tracking, and MCP teardown.
- Added runtime manager assembly through `create_runtime_manager(framework="agentscope")`, which binds `RuntimeManager` to `AgentScopeRuntimeBuilder`.
- Added `AgentScopeSessionExecutor` for `session_id -> AgentState(session_id=...)` mapping and per-session `reply` / `reply_stream` execution.
- Added `AgentScopeSessionStore` persistence boundary with in-memory and AgentScope app storage-backed implementations.
- Added `PlatformEventMapper` for `ReplyStartEvent`, `TextBlockDeltaEvent`, and `ReplyEndEvent` conversion into platform events.
- Added focused v2 HTTP routes: `POST /v2/runtimes/init` and SSE-first `POST /v2/chat`.
- Verified v2 replacements for v1 `ReActAgent`, `Toolkit`, MCP client config, app/session/storage, and built-in tools.
- Verified AgentScope app storage APIs for session state: `get_session`, `upsert_session`, and `update_session_state`.
- Verified AgentScope v2 `Agent` is not directly callable; chat execution must use `Agent.reply` or `Agent.reply_stream`.
- Text deltas are emitted as `after_turn` payloads with `status = "streaming"`; no public `message_delta` event is introduced.
- Keep MCP client construction separate from toolkit construction because AgentScope v2 requires stateful MCP clients to be connected before toolkit registration.
- Keep agent construction separate from runtime resource construction until session isolation is wired.
- Replace v1 `AgentApp`, `ReActAgent`, `Toolkit`, session, MCP, and tracing integration with AgentScope v2 equivalents.
- Use AgentScope v2 RedisStorage for framework session and memory state when storage configuration is wired.
- Map AgentScope v2 stream objects into platform events.
- Verify AgentScope v2 session id mapping before implementing storage behavior.
- Verify whether AgentScope v2 native service/streaming can satisfy `/chat` SSE; otherwise implement FastAPI SSE in AgentOps.

Validation:

- `uv run python -c 'import agentscope; print(agentscope.__version__)'` returns `2.0.0`.
- `uv run pytest tests/test_refactor_v2_schemas.py tests/test_refactor_v2_runtime_manager.py tests/test_agentscope_v2_adapter.py tests/test_agentscope_v2_runtime_builder.py tests/test_runtime_factory.py tests/test_agentscope_v2_execution.py tests/test_agentscope_v2_event_mapping.py tests/test_v2_api.py tests/test_agentscope_v2_session_store.py -q` passes.
- Full test collection currently fails on old v1 imports such as `agentscope.memory`, `agentscope.tracing`, `StdIOStatefulClient`, `StatefulClientBase`, `ReActAgent`, and legacy tool helpers. These failures belong to this adapter migration phase.
- Tool, MCP, skill, remote skill, and session UATs pass on AgentScope v2.
- Effective model and prompt hash appear in streamed events.
- Trace metadata behavior is verified against Studio or Phoenix.

## Phase 5: Optional Transcript Replay

- Keep `StandardMessage` as the platform message format.
- Add persistence only if cross-framework replay becomes a concrete requirement.
- Do not replay `standard_messages` in the first implementation.
- Keep framework-private state as the preferred same-framework recovery path.

Validation:

- Same tenant/session can continue after runtime replacement.
- Same-framework replay works from framework-private session state. Missing or incompatible state creates a fresh framework session. Optional cross-framework replay is explicitly deferred.

## Phase 6: API And UAT Refresh

- Replace old `/runtimes/init` and `/chat` contracts with v2 contracts.
- Update UAT scripts and docs.
- Remove v1 compatibility paths unless explicitly needed.

Validation:

- API docs match implementation.
- UAT covers local tools, MCP stdio, local skills, remote skills, sessions, and tracing.

## Phase 7: Future Framework Preparation

- Add Microsoft Agent Framework adapter notes or placeholder package only after AgentScope v2 is stable.
- Use the same platform contracts and event protocol.

Validation:

- No public schema changes are needed to add a second framework adapter.
