# Simple API Reference

Base URL: `http://127.0.0.1:8000`

This document lists only the business APIs, with a short purpose, the main input fields, and the main output shape.

## POST `/runtimes/bootstrap`

**Purpose**  
Create the pod runtime profile with optional tools, skills, MCP servers, and model overrides.

**Input**  
`application/json`

Main fields:
- `runtime_id` — required runtime identifier supplied by the caller
- `agent_config` — optional model settings
  - `model_name`
  - `api_key`
  - `base_url`
- `memory_compression` — optional runtime-level AgentScope memory compression settings
  - `enabled`
  - `trigger_tokens`
  - `keep_recent`
- `tools` — optional list of tools to enable
  - `name`
- `skills` — optional list of skills to load
  - `skill_dir`
  - `activation_mode`
  - `expose_structured_tools`
- `mcp_servers` — optional list of MCP servers
  - stdio server: `type`, `name`, `command`, `args`, `env`, `cwd`
  - http server: `type`, `name`, `transport`, `url`, `headers`, `timeout`, `sse_read_timeout`

**Output**  
- `200 application/json`
  - `runtime_id`
  - `status` = `ready`
  - `tools` — enabled tool summaries
  - `skills` — loaded skill summaries
  - `mcp_servers` — MCP server summaries
- `422 application/json`
  - Validation error payload

## POST `/runtimes/{runtime_id}/shutdown`

**Purpose**  
Close the existing bootstrapped runtime profile.

**Input**  
Path parameter:
- `runtime_id`

No request body.

**Output**  
- `200 application/json`
  - `runtime_id`
  - `status` = `closed`
- `422 application/json`
  - Validation error payload

## POST `/process`

**Purpose**  
Send a runtime-hosted agent request. This is the main AgentScope-compatible processing endpoint.

**Input**  
`application/json`

Main fields:
- `input` — required list of messages
- `stream` — whether to stream responses
- `runtime_id` — optional runtime profile identifier
- `session_id` — optional conversation identifier used for memory persistence; AgentScope Runtime generates one when omitted
- `user_id` — optional user identifier
- `model` — optional model name
- `temperature`, `top_p`, `max_tokens`, `stop`, `seed` — optional generation settings
- `tools` — optional tool definitions

**Output**  
- `200 application/json`
- Agent runtime response payload
- `422 application/json`
  - Validation error payload

## POST `/chat`

**Purpose**  
Send a direct chat request and receive Server-Sent Events (SSE) for lifecycle and message updates.

**Input**  
`application/json`

Main fields:
- `input` — required list of chat messages
  - `role`
  - `content` — usually a list like `[{"type": "text", "text": "Hello"}]`
- `runtime_id` — optional runtime profile identifier
- `session_id` — optional conversation identifier used for memory persistence
- `agent_config` — optional model settings
  - `model_name`
  - `api_key`
  - `base_url`

**Output**  
- `200 text/event-stream`
- Streamed event objects with fields such as:
  - `status` — `created`, `in_progress`, `completed`, or `failed`
  - `session_id`
  - `object`, `role`, `name`
  - `content`
  - `text`
  - `delta.text`
  - `error.message`
- `200 application/json`
  - Documented schema equivalent for tooling compatibility

## Notes

- The formal machine-readable schema is in `docs/openapi.json`.
- The interactive docs are available at `http://127.0.0.1:8000/docs` after the service starts.
