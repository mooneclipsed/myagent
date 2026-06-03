# Data Model

The platform data model separates stable AgentOps concepts from framework-private objects. Framework adapters convert platform objects into AgentScope v2 or future Microsoft Agent Framework objects.

Public and platform-facing data structures should be Pydantic models, not Python dataclasses. Dataclasses may still be used for private in-memory helper state, but request schemas, response schemas, messages, capabilities, and events should use Pydantic so validation, serialization, and OpenAPI generation stay consistent.

## Identity Model

```text
Tenant
  └── RuntimeProfile(runtime_id)
        ├── FrameworkRuntime(internal only)
        ├── Workspace(runtime_id scoped)
        └── Chat requests(session_id, request_id optional)
```

`runtime_id` identifies one initialized runtime profile. A Pod has only one active runtime profile, but the ID is still required so the frontend service, Pod, Redis data, workspace, traces, and UAT records can be correlated.

`session_id` identifies a conversation history owned by the frontend service. It is required for chat and is scoped by tenant, not by runtime, so a tenant can reuse the same session across runtime replacements. When no explicit tenant is provided, the platform should use a default tenant namespace.

`request_id` is optional and supplied by callers that need frontend-side correlation. The platform does not expose a required `run_id`.

## RuntimeProfile

`RuntimeProfile` represents the immutable result of an init request.

Suggested fields:

- `runtime_id`: frontend-supplied runtime identifier.
- `tenant_id`: optional tenant scope.
- `framework`: selected framework, initially `agentscope_v2`.
- `agent_spec`: immutable agent configuration prepared during init.
- `capabilities`: configured tools, MCP servers, and skills.
- `workspace`: runtime-scoped workspace reference.
- `storage`: framework storage reference.
- `trace`: tracing destination reference.
- `framework_runtime`: internal framework runtime, service, factory, or resource reference.
- `status`: runtime status such as `initializing`, `ready`, `failed`, or `closed`.

`RuntimeProfile` stores immutable agent configuration, but it must not store a mutable cross-session agent memory object. The chat path creates or acquires a session-isolated execution object from the profile's `agent_spec` and `framework_runtime`.

## AgentSpec

`AgentSpec` is resolved during runtime init and belongs to the immutable runtime profile.

Suggested fields:

- `model_config`: model name, API key, and base URL.
- `system_prompt`: runtime-level system prompt.
- `prompt_hash`: hash of the effective system prompt.
- `metadata`: optional non-secret agent metadata.

If `model_config` is missing from init, environment defaults are used. If no effective model can be resolved, init fails. API keys and base URLs are used in memory only and are not written to logs, events, `standard_messages`, or traces.

## ExecutionConfig

`ExecutionConfig` is provided on chat requests and contains request-scoped options only.

Suggested fields:

- `request_id`: optional client correlation ID.
- `metadata`: optional non-secret caller metadata.

## Session Reference

AgentOps does not maintain an independent session entity. The frontend service owns session creation, session lookup, and session lifecycle. AgentOps accepts `session_id` as an external reference and uses it to load framework-private session state.

`standard_messages` are the platform's framework-neutral message format. In the first implementation they are used for API validation, adapter conversion, and event output, but are not persisted by default. A future optional transcript store can persist them for cross-framework replay. That replay would not promise exact restoration of framework-private memory, tool intermediate state, or model cache.

## Message

Messages use OpenAI-like content parts.

Suggested fields:

- `role`: `system`, `user`, `assistant`, or `tool`.
- `content`: list of content parts.
- `metadata`: optional message metadata.

Initial content part types:

- `text`
- `file_ref`
- `image_ref`

Additional types can be added when the platform needs richer multimodal or workspace behavior.

## Capability

Capabilities use one envelope with strict per-type config schemas.

Suggested fields:

- `type`: `tool`, `mcp`, or `skill`.
- `name`: unique name within the runtime profile.
- `enabled`: defaults to `true`.
- `config`: type-specific configuration.

`tool` config describes local or native tool selection.

`mcp` config describes stdio or HTTP MCP server configuration.

`skill` config describes local skill bundles and remote skill downloads. Remote skill files are downloaded into the runtime workspace and cleaned up when the runtime is replaced.

Capability init is all-or-nothing. If any configured tool, MCP server, or skill fails to load, the runtime is not published.

## Event

Events use a thin platform protocol and are streamed to callers. They are not stored as a platform event log.

Suggested fields:

- `event`: event name.
- `runtime_id`
- `tenant_id`
- `session_id`
- `request_id`
- `sequence`
- `framework`
- `effective_model`
- `prompt_hash`
- `trace_ref`
- `payload`

Initial event names:

- `message.delta`
- `message.completed`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `skill.loaded`
- `skill.used`
- `runtime.ready`
- `request.completed`
- `request.failed`

`sequence` orders events within one streamed response. `trace_ref` points to AgentScope Studio, Phoenix, or OpenTelemetry identifiers when available.
