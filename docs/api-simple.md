# Simple API Reference

Base URL: `http://127.0.0.1:8000`

This document lists only the business APIs, with a short purpose, the main input fields, and the main output shape.

## POST `/runtimes/init`

**Purpose**  
Recreate the pod runtime profile with optional tools, local skills, remote skill downloads, MCP servers, and model overrides.

**Input**  
`application/json`

Main fields:
- `tenant_id` — optional tenant identifier used for trace project grouping. Use a trusted server-side value in production.
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
  "tenant_id": "1",
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

Tenant trace behavior:
- When Studio tracing is enabled, `tenant_id` is mapped into the AgentScope Studio project name.
- With `tenant_id="1"`, initialization configures tracing for project `agentops-1`.
- Runtime initialization does not register a runtime-level Studio run; chat registers a session-level run after `session_id` is known.
- If `tenant_id` is omitted, the project falls back to `agentops`.

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
- `tenant_id` — optional. When present, must match the active runtime's `tenant_id`.
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

Tenant/session behavior:
- Same-`session_id` chat streams are serialized with an in-process lock.
- Session memory is persisted directly under the provided `session_id`.
- With `tenant_id="1"` and `session_id="test-trace"`, the persisted session key is `test-trace`.
- With the same values, chat trace context is:
  - project: `agentops-1`
  - run id: `test-trace`
  - name: `test-trace`
- Chat registers a Studio run with id/name `test-trace`, so AgentScope Studio Data View can join chat spans back to the selected session run.

**Bruno test example**

1. Initialize the runtime:

```http
POST http://127.0.0.1:8000/runtimes/init
Content-Type: application/json
```

```json
{
  "tenant_id": "1",
  "skills": [],
  "mcp_servers": []
}
```

Expected response:

```json
{
  "status": "ready"
}
```

The response can include non-empty `tools`, `skills`, `skill_downloads`, or `mcp_servers` depending on the runtime config.

2. Send a chat request:

```http
POST http://127.0.0.1:8000/chat
Content-Type: application/json
Accept: text/event-stream
```

```json
{
  "tenant_id": "1",
  "session_id": "test-trace",
  "input": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Reply with one short sentence for trace validation."
        }
      ]
    }
  ]
}
```

Expected stream:
- At least one lifecycle event with `status` such as `created` or `in_progress`.
- A final event with `status` = `completed` for a successful model call, or `failed` with `error.message` if the model/backend call fails.
- Events should include `session_id` = `test-trace`.

3. Check AgentScope Studio:
- Open `http://127.0.0.1:3000`.
- Look for project `agentops-1`.
- The run list should contain a run named `test-trace`.
- The center message panel should show AgentScope printed assistant messages for the selected run.
- The Data View trace panel for run `test-trace` should show the chat spans.
- If only the initialization trace is visible, verify that `STUDIO_ENABLED=true` and `STUDIO_URL=http://127.0.0.1:3000` were present when the agent process started.

Equivalent curl commands:

```bash
curl -X POST 'http://127.0.0.1:8000/runtimes/init' \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id": "1",
    "skills": [],
    "mcp_servers": []
  }'
```

```bash
curl -N -X POST 'http://127.0.0.1:8000/chat' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{
    "tenant_id": "1",
    "session_id": "test-trace",
    "input": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Reply with one short sentence for trace validation."
          }
        ]
      }
    ]
  }'
```

## POST `/process`

**Purpose**  
Compatibility and comparison endpoint backed by the AgentScope runtime query handler. It uses the same active runtime profile as `/chat`, but lets `agentscope_runtime` serialize the streamed `Msg` objects into SSE.

**Input**  
`application/json`

Main fields:
- `input` — required list of chat messages
  - `role`
  - `content` — usually a list like `[{"type": "text", "text": "Hello"}]`
- `tenant_id` — optional. When present, must match the active runtime's `tenant_id`.
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
