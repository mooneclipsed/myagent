# Event Protocol

AgentOps uses a thin platform event protocol so clients, tests, and UAT do not depend on framework-specific stream objects.

## Event Envelope

```json
{
  "event": "message.delta",
  "runtime_id": "rt-001",
  "tenant_id": "tenant-a",
  "session_id": "session-001",
  "request_id": "frontend-request-001",
  "sequence": 1,
  "framework": "agentscope_v2",
  "effective_model": {
    "provider": "openai",
    "model_name": "gpt-4o"
  },
  "prompt_hash": "sha256:...",
  "trace_ref": {
    "provider": "phoenix",
    "trace_id": "...",
    "span_id": "..."
  },
  "payload": {}
}
```

`request_id` and `trace_ref` are optional. Secrets must never appear in events.

## Event Names

| Event | Meaning |
| --- | --- |
| `message.delta` | Incremental assistant text or content part output. |
| `message.completed` | Final assistant message for the request. |
| `tool.started` | A local or native tool call started. |
| `tool.completed` | A local or native tool call completed. |
| `tool.failed` | A local or native tool call failed. |
| `skill.loaded` | A skill was loaded during runtime init. |
| `skill.used` | A skill was used during request execution. |
| `runtime.ready` | Runtime init completed successfully. |
| `request.completed` | Request execution completed successfully. |
| `request.failed` | Request execution failed. |

MCP tool calls can use `tool.*` events with `payload.provider = "mcp"` and `payload.capability_name`.

## Ordering

`sequence` starts at `1` for each chat response stream and increments by one for every emitted event. It is not a durable run identifier.

## Model Metadata

`effective_model` records the resolved model from the active `AgentSpec`. It should include non-secret fields only.

Suggested fields:

- `provider`
- `model_name`
- `base_url_host`

`base_url_host` is optional and must avoid leaking full secret-bearing URLs.

## Prompt Metadata

`prompt_hash` records the hash of the effective system prompt. The raw prompt is not emitted in events unless the API explicitly returns debug metadata in a controlled development mode.

## Trace Reference

`trace_ref` records identifiers produced by AgentScope Studio, Phoenix, or OpenTelemetry when available. Trace systems own their own run, trace, and span IDs.

The platform does not require clients to provide `run_id`.
