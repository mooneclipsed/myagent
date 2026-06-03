# AgentOps v2 Refactor Overview

This document set defines the planned v2 refactor for AgentOps. The goal is to move from the current AgentScope v1-oriented implementation to a cleaner developer validation platform built around AgentScope v2 first, while keeping framework boundaries open for Microsoft Agent Framework later.

## Goals

- Upgrade the default framework implementation to AgentScope v2.
- Keep AgentOps focused on validating agents, tools, MCP servers, skills, sessions, and tracing.
- Support destructive API and structure changes where they make the system clearer.
- Preserve all current functional areas: tools, MCP, local skills, remote skill download, session history, tracing, and UAT workflows.
- Design framework-neutral platform data structures before restructuring source code.

## Non-Goals

- Do not keep v1 API compatibility by default.
- Do not implement Microsoft Agent Framework in the first migration.
- Do not preserve the current JSON/Redis session backend as the primary session implementation.
- Do not build a full event store in the platform layer.
- Do not expose framework-private agent handles through the public API.

## Confirmed Decisions

- AgentScope v2 is the first complete framework implementation.
- Microsoft Agent Framework is the second framework target for architecture planning.
- Each Pod has one active runtime profile. A new init request replaces the previous active runtime.
- `runtime_id` is supplied by the frontend service and identifies the active runtime profile.
- `session_id` is required for chat requests and can be reused across runtimes under the same tenant.
- Public API does not require a `run_id`; optional `request_id` is used for client correlation.
- Runtime init owns `model_config` and `system_prompt` through an immutable `AgentSpec`.
- AgentScope v2 RedisStorage is the preferred framework storage for AgentScope sessions and memory.
- The platform uses frontend-supplied `session_id` as the session reference. `standard_messages` are the platform message format, but they are not persisted by default in the first implementation.

## Reference Material

- AgentScope v2 docs: <https://docs.agentscope.io/v2>
- Current architecture notes: `docs/architecture.md`
- Current API notes: `docs/api-simple.md`
- Current Phoenix notes: `docs/phoenix.md`
