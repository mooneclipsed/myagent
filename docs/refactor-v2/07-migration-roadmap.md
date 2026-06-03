# Migration Roadmap

This roadmap keeps the refactor staged so each phase has a concrete validation point.

## Phase 1: Documentation And Contracts

- Finalize data model docs.
- Finalize event protocol docs.
- Finalize framework port docs.
- Identify v1 objects that must not leak into new platform schemas.

Validation:

- Design docs describe every current core capability.
- No implementation changes are required in this phase.

## Phase 2: Platform Schemas

- Add Pydantic models for `RuntimeProfile`, `AgentSpec`, `ExecutionConfig`, `standard_messages`, capability envelope, workspace refs, and platform events.
- Keep schemas framework-neutral.
- Add unit tests for validation rules.

Validation:

- Unknown capability types fail validation.
- Secrets are excluded from events and `standard_messages`.
- `session_id` is required for chat schemas.

## Phase 3: Runtime And Workspace Lifecycle

- Implement Pod-local active runtime replacement around `runtime_id`.
- Implement runtime-scoped workspace creation and cleanup.
- Keep capability init all-or-nothing.

Validation:

- Repeated init closes the previous runtime and replaces workspace contents.
- Failed capability init does not publish a runtime.

## Phase 4: AgentScope v2 Adapter

- Replace v1 `AgentApp`, `ReActAgent`, `Toolkit`, session, MCP, and tracing integration with AgentScope v2 equivalents.
- Use AgentScope v2 RedisStorage for framework session and memory state.
- Map AgentScope v2 stream objects into platform events.

Validation:

- Tool, MCP, skill, remote skill, and session UATs pass on AgentScope v2.
- Effective model and prompt hash appear in streamed events.
- Trace metadata behavior is verified against Studio or Phoenix.

## Phase 5: Optional Transcript Replay

- Keep `standard_messages` as the platform message format.
- Add persistence only if cross-framework replay becomes a concrete requirement.
- Replay `standard_messages` only when the optional transcript store exists and framework-private session state is missing or incompatible.
- Keep framework-private state as the preferred same-framework recovery path.

Validation:

- Same tenant/session can continue after runtime replacement.
- Same-framework replay works from framework-private session state. Optional cross-framework replay is explicitly deferred.

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
