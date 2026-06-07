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

Status: in progress. AgentScope `2.0.0` dependency and construction APIs are verified; runtime wiring, session persistence boundary, Redis storage configuration, focused SSE routes, main app route replacement, and UAT helper refresh are in place. Trace metadata verification is still pending.

- Added initial `agentscope_v2` adapter helpers for agent spec, model, toolkit, MCP client, and skill path construction.
- Added `AgentScopeRuntimeBuilder` for runtime-level Toolkit construction, MCP connection, resource tracking, and MCP teardown.
- Added runtime manager assembly through `create_runtime_manager(framework="agentscope")`, which binds `RuntimeManager` to `AgentScopeRuntimeBuilder`.
- Added `AgentScopeSessionExecutor` for `session_id -> AgentState(session_id=...)` mapping and per-session `reply` / `reply_stream` execution.
- Added `AgentScopeSessionStore` persistence boundary with in-memory and AgentScope app storage-backed implementations.
- Added configured AgentScope v2 session store assembly. `SESSION_BACKEND=redis` creates AgentScope `RedisStorage` from `REDIS_*`; `json` and `memory` use the in-memory v2 store for now.
- Added `PlatformEventMapper` for `ReplyStartEvent`, `TextBlockDeltaEvent`, and `ReplyEndEvent` conversion into platform events.
- Added focused v2 HTTP routes: `POST /v2/runtimes/init` and SSE-first `POST /v2/chat`.
- Replaced the main application entrypoint with FastAPI route wiring for v2 routes only. Legacy `/runtimes/init` and `/chat` are no longer registered by `agentops.main`.
- Attached the v2 runtime API service to `app.state` so application lifespan cleanup closes v2 runtime resources without importing v1 session/runtime modules.
- Refreshed shared UAT helpers to send v2 runtime/chat payloads while keeping old script payload declarations compatible.
- Updated local tool and skill registration helpers for AgentScope v2 `Toolkit`, `FunctionTool`, built-in `Read`/`Write`/`Bash`, and skill loaders.
- Retired v1-only test modules that depend on removed AgentScope v1 APIs. Their active coverage is replaced by v2 API, runtime builder, execution, storage, event mapping, startup, tool, and skill smoke tests.
- Verified v2 replacements for v1 `ReActAgent`, `Toolkit`, MCP client config, app/session/storage, and built-in tools.
- Verified AgentScope app storage APIs for session state: `get_session`, `upsert_session`, and `update_session_state`.
- Verified AgentScope v2 `Agent` is not directly callable; chat execution must use `Agent.reply` or `Agent.reply_stream`.
- Text deltas are emitted as `after_turn` payloads with `status = "streaming"`; no public `message_delta` event is introduced.
- Keep MCP client construction separate from toolkit construction because AgentScope v2 requires stateful MCP clients to be connected before toolkit registration.
- Keep agent construction separate from runtime resource construction until session isolation is wired.
- Replace v1 tracing integration with AgentScope v2-compatible trace metadata behavior.
- Verify trace metadata behavior against Studio or Phoenix.

Validation:

- `uv run python -c 'import agentscope; print(agentscope.__version__)'` returns `2.0.0`.
- `uv run pytest tests/test_refactor_v2_schemas.py tests/test_refactor_v2_runtime_manager.py tests/test_agentscope_v2_adapter.py tests/test_agentscope_v2_runtime_builder.py tests/test_runtime_factory.py tests/test_agentscope_v2_execution.py tests/test_agentscope_v2_event_mapping.py tests/test_v2_api.py tests/test_agentscope_v2_session_store.py tests/test_agentscope_v2_storage.py -q` passes.
- `uv run pytest -q` passes with retired v1 contract tests skipped.
- Full test collection no longer fails on old v1 imports such as `agentscope.memory`, `agentscope.tracing`, `StdIOStatefulClient`, `StatefulClientBase`, `ReActAgent`, and legacy tool helpers.
- Tool, MCP, skill, remote skill, and session UAT helpers target AgentScope v2 contracts. Manual UAT execution against a live service is still required.
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
