# Event Protocol

AgentOps uses a thin platform event protocol so clients, tests, and UAT do not depend on framework-specific stream objects.

## Event Envelope

```json
{
  "event": "before_turn",
  "runtime_id": "rt-001",
  "tenant_id": "tenant-a",
  "session_id": "session-001",
  "request_id": "frontend-request-001",
  "sequence": 1,
  "framework": "agentscope",
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

| Event | Trigger |
| --- | --- |
| `session_start` | Runtime/session execution is ready. |
| `session_restored` | Saved framework session state was restored. |
| `session_end` | Runtime/session execution is closing before teardown. |
| `before_turn` | A new user turn or retry starts. |
| `after_turn` | A turn completes, fails, or is interrupted. |
| `user_input_submit` | User input is submitted before framework execution. |
| `before_tool_call` | A tool or MCP tool is about to execute. |
| `after_tool_call` | A tool or MCP tool completed successfully. |
| `tool_error` | A tool or MCP tool raised an error. |

The first implementation treats these events as observational lifecycle events only. They do not block execution and do not modify input, tool arguments, reminders, or extra context. A future hook system can add blocking and mutation semantics.

These events are not token-level text streaming. Final assistant output should be returned as `after_turn.payload.message`, using the `StandardMessage` schema. Tool call and tool result events should also use `StandardMessage` where a normalized message is needed.

For `/chat`, the first implementation should expose these events over SSE. If AgentScope v2 provides a compatible Agent Service stream, the adapter can use it. Otherwise AgentOps should implement SSE directly and emit the platform event envelope.

MCP tool calls use the same tool events with `payload.provider = "mcp"` and `payload.capability_name`.

Example `before_tool_call` payload:

```json
{
  "tool_call": {
    "type": "tool_call",
    "payload": {
      "id": "call_1",
      "name": "get_weather",
      "provider": "mcp",
      "arguments": {
        "city": "Beijing"
      }
    },
    "metadata": {}
  }
}
```

Example `after_turn` payload:

```json
{
  "status": "completed",
  "message": {
    "type": "assistant_message",
    "payload": {
      "content": [
        {
          "type": "text",
          "text": "The weather in Beijing is clear today."
        }
      ]
    },
    "metadata": {}
  }
}
```

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
