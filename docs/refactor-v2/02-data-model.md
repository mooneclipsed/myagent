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
- `framework`: selected agent framework. Public value `agentscope` means AgentScope v2.
- `agent_spec`: immutable agent configuration prepared during init.
- `capabilities`: configured tools, MCP servers, and skills.
- `workspace`: runtime-scoped workspace reference.
- `storage`: framework storage reference.
- `trace`: tracing destination reference.
- `status`: runtime status such as `initializing`, `ready`, `failed`, or `closed`.

`RuntimeProfile` is a serializable Pydantic model. It stores immutable agent configuration, but it must not store a mutable cross-session agent memory object or framework handle. The in-memory active runtime state can hold the private framework runtime, service, factory, or resource handle alongside the `RuntimeProfile`.

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

## Chat Input

Chat requests contain the current user `input`, not full conversation history.

First implementation fields:

- `runtime_id`
- `session_id`
- `input`: current user input, initially a string.
- `execution_config`: optional request-scoped config such as `request_id`.

Future versions can widen `input` from string to content parts or `StandardMessage` when multimodal input is needed.

## Session Reference

AgentOps does not maintain an independent session entity. The frontend service owns session creation, session lookup, and session lifecycle. AgentOps accepts `session_id` as an external reference and uses it to load framework-private session state.

`standard_messages` are the platform's framework-neutral message format. In the first implementation they are used for API validation, adapter conversion, and event output, but are not persisted by default. Chat requests contain only the current user input; conversation history is loaded from framework-private memory by `session_id`.

## StandardMessage

`StandardMessage` represents a normalized message that is independent from AgentScope v2 or any future framework message type.

Suggested fields:

- `type`: `user_message`, `assistant_message`, `tool_call`, `tool_result`, or `error`.
- `payload`: type-specific payload.
- `metadata`: optional message metadata.

`user_message.payload` and `assistant_message.payload` fields:

- `content`: list of content parts.

Initial content part types for user and assistant messages:

- `text`
- `file_ref`
- `image_ref`

`tool_call.payload` fields:

- `id`: framework or platform tool call id when available.
- `name`: tool name.
- `provider`: `local`, `mcp`, or `skill`.
- `arguments`: sanitized tool arguments.

`tool_result.payload` fields:

- `tool_call_id`: id of the tool call this result belongs to.
- `name`: tool name.
- `provider`: `local`, `mcp`, or `skill`.
- `status`: `success` or `failed`.
- `content`: list of content parts.

`error.payload` fields:

- `code`: stable error code when available.
- `message`: safe user-facing message.
- `details`: optional non-secret details.

Additional content part types can be added when the platform needs richer multimodal or workspace behavior.

## Capability

Capabilities use one envelope with strict per-type config schemas.

Suggested fields:

- `type`: `tool`, `mcp`, or `skill`.
- `name`: unique name within the runtime profile.
- `enabled`: defaults to `true`.
- `config`: type-specific configuration.

`tool` config describes local or native tool selection.

`mcp` config describes stdio or HTTP MCP server configuration.

`skill` config uses one project skill root: `.skills/`. Remote skills are downloaded during init into `.skills/` and then treated as local skills by the capability layer. The first implementation does not need multiple independent skill root directories.

Capability init is all-or-nothing. If any configured tool, MCP server, or skill fails to load, the runtime is not published.

Example capability declarations:

```json
[
  {
    "type": "tool",
    "name": "calculate",
    "config": {
      "tool_name": "calculate"
    }
  },
  {
    "type": "mcp",
    "name": "weather",
    "config": {
      "transport": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "agentops.resources.mcp_servers.example"],
      "env": {},
      "cwd": null
    }
  },
  {
    "type": "skill",
    "name": "project_skills",
    "config": {
      "path": ".skills/"
    }
  }
]
```

These examples preserve the intent of the current v1 capability structure. The AgentScope v2 adapter must verify the exact v2 registration APIs for tools, MCP, and skills before implementation.

## Runtime Init Response

Successful runtime init returns a public-safe description.

Suggested fields:

- `runtime_id`
- `framework`
- `status`
- `capabilities`: loaded capability summaries.
- `workspace`: public workspace reference.
- `storage`: storage mode and non-secret connection summary.
- `tracing`: tracing mode and provider summary.

The response must not include `AgentSpec.api_key`, raw system prompt, framework-private session state, or framework runtime handles.

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

- `session_start`
- `session_restored`
- `session_end`
- `before_turn`
- `after_turn`
- `user_input_submit`
- `before_tool_call`
- `after_tool_call`
- `tool_error`

`sequence` orders events within one streamed response. `trace_ref` points to AgentScope Studio, Phoenix, or OpenTelemetry identifiers when available.
