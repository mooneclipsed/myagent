# Simple API Reference

Base URL: `http://127.0.0.1:8000`

This document lists only the business APIs, with a short purpose, the main input fields, and the main output shape.

## POST `/runtimes/init`

**Purpose**  
Recreate the pod runtime profile with optional tools, local skills, remote skill downloads, MCP servers, and model overrides.

**Input**  
`application/json`

Main fields:
- `model_config` — optional runtime-level model settings
  - `model_name`
  - `api_key`
  - `base_url`
- `memory_compression` — optional runtime-level AgentScope memory compression settings
  - `enabled`
  - `trigger_tokens`
  - `keep_recent`
- `system_prompt` — optional runtime-level system prompt. When omitted or blank, the service uses its built-in default prompt.
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
  - `status` = `ready`
  - `tools` — enabled tool summaries
  - `skills` — loaded skill summaries
  - `skill_downloads` — per-skill remote install results with `installed`
  - `mcp_servers` — MCP server summaries
- `422 application/json`
  - Validation error payload

**Example**

```json
{
  "system_prompt": "You are a concise assistant. Prefer direct answers and actionable steps.",
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
- `skill_downloads` is the remote skill list for the new runtime. Calling initialize while a runtime is already active closes the old runtime first.
- Reinitialization deletes old managed remote skills before downloading the requested remote skills again, so user-edited managed skill files are refreshed.
- Any remote skill download or extraction failure fails the whole initialization.
- Managed remote skills are stored under `skills/.managed/`; downloaded ZIP files are stored under `skills/.downloads/`.

## POST `/chat`

**Purpose**  
Send a direct chat request and receive Server-Sent Events (SSE) for lifecycle and message updates.
The service uses the single active runtime profile created by `/runtimes/init`; chat fails if no runtime has been initialized.

**Input**  
`application/json`

Main fields:
- `input` — required list of chat messages
  - `role`
  - `content` — usually a list like `[{"type": "text", "text": "Hello"}]`
- `session_id` — optional conversation identifier used for memory persistence
- `model_config` — rejected for initialized runtime chats; reinitialize the runtime to change model settings.
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
  - `delta.text` — incremental text delta. If the underlying AgentScope stream emits cumulative text, `/chat` converts it to only the newly added text.
  - `error.message`
- `200 application/json`
  - Documented schema equivalent for tooling compatibility

## POST `/process`

**Purpose**  
Compatibility and comparison endpoint backed by the AgentScope runtime query handler. It uses the same active runtime profile as `/chat`, but lets `agentscope_runtime` serialize the streamed `Msg` objects into SSE.

**Input**  
`application/json`

Main fields:
- `input` — required list of chat messages
  - `role`
  - `content` — usually a list like `[{"type": "text", "text": "Hello"}]`
- `session_id` — optional conversation identifier used for memory persistence. When omitted, the runtime framework may assign a generated session identifier.
- `model_config` — rejected for initialized runtime chats
  - `model_name`
  - `api_key`
  - `base_url`

**Output**  
- `200 text/event-stream`
- Streamed SSE events produced by `agentscope_runtime` from the yielded AgentScope `Msg` stream.

Notes:
- `/chat` and `/process` both call `AgentScopeRuntime.stream_chat`.
- `/chat` owns its SSE JSON shape and normalizes cumulative text into incremental `delta.text`.
- `/process` is useful for comparing the framework-provided stream serialization with the explicit `/chat` SSE contract.

## Notes

- The formal machine-readable schema is in `docs/openapi.json`.
- The interactive docs are available at `http://127.0.0.1:8000/docs` after the service starts.
