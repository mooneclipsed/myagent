# Simple API Reference

Base URL: `http://127.0.0.1:8000`

This document lists only the business APIs, with a short purpose, the main input fields, and the main output shape.

## POST `/runtimes/bootstrap`

**Purpose**  
Create or reload the pod runtime profile with optional tools, local skills, remote skill downloads, MCP servers, and model overrides.

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
- `skills_download_url` — optional remote skill service base URL; falls back to `SKILLS_DOWNLOAD_URL`
- `skill_downloads` — optional list of remote skills to download and load
  - `skill_id`
  - `version_id`
- `mcp_servers` — optional list of MCP servers
  - stdio server: `type`, `name`, `command`, `args`, `env`, `cwd`
  - http server: `type`, `name`, `transport`, `url`, `headers`, `timeout`, `sse_read_timeout`

**Output**  
- `200 application/json`
  - `runtime_id`
  - `status` = `ready`
  - `tools` — enabled tool summaries
  - `skills` — loaded skill summaries
  - `skill_downloads` — per-skill remote install results with `installed`, `kept`, `failed`, or `removed`
  - `mcp_servers` — MCP server summaries
- `422 application/json`
  - Validation error payload

**Example**

```json
{
  "runtime_id": "runtime-001",
  "skills_download_url": "https://skills.example.com",
  "skill_downloads": [
    {
      "skill_id": 1,
      "version_id": 3
    }
  ],
  "skills": [
    {
      "skill_dir": "skills/local_skill"
    }
  ],
  "mcp_servers": []
}
```

Example response:

```json
{
  "runtime_id": "runtime-001",
  "status": "ready",
  "tools": [],
  "skills": [
    {
      "name": "local-skill",
      "structured_tools": []
    },
    {
      "name": "remote-skill",
      "structured_tools": []
    }
  ],
  "skill_downloads": [
    {
      "skill_id": 1,
      "version_id": 3,
      "status": "installed",
      "skill_dir": "skills/.managed/skill_1_v3",
      "zip_path": "skills/.downloads/skill_1_v3.zip",
      "error": null
    }
  ],
  "mcp_servers": []
}
```

Remote skill behavior:
- `skill_downloads` is a desired-state list. Calling bootstrap while a runtime is already active reloads the runtime.
- On reload, unchanged remote skills are kept, new remote skills are downloaded, and removed remote skills are deleted after the new runtime is ready.
- A single remote skill download or extraction failure does not fail the whole bootstrap. The failed item is returned with `status = failed`, and successfully installed or local skills still load.
- Managed remote skills are stored under `skills/.managed/`; downloaded ZIP files are stored under `skills/.downloads/`.

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
