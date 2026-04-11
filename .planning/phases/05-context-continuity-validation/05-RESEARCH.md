# Phase 5: Context Continuity Validation - Research

**Researched:** 2026-04-12
**Domain:** agentscope-runtime multi-turn message handling / ReActAgent context passing
**Confidence:** HIGH

## Summary

Phase 5 validates that multi-turn context stays consistent within a single session where the client manages full conversation history. The research confirms that agentscope-runtime natively supports multi-turn message arrays: when `ReActAgent.reply(msg)` receives a `list[Msg]`, the agent calls `self.memory.add(msgs)` which stores every message, then `_reasoning()` formats all memory contents into the model prompt. This means the current code in `src/agent/query.py` already supports multi-turn context -- the `msgs` parameter passed to `agent(msgs)` flows through `AgentBase.__call__` to `ReActAgent.reply()`, which adds all messages to `InMemoryMemory` before generating a response.

**Primary recommendation:** No code changes to the agent handler are needed. Phase 5 is purely a testing and validation phase: write tests that send multi-turn message arrays via the `/process` endpoint and assert the full history reaches the model. Use the existing mock handler pattern from `tests/test_chat_stream.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Client manages full conversation history. Each request carries the complete messages array (all prior turns + new message). No server-side session state or session_id is introduced in this phase.
- **D-02:** Server remains near-stateless -- each request still creates a fresh agent. Context continuity comes from the client passing full history, not from server-side session storage.
- **D-03:** Pass the complete messages array directly to the agent via `agent(msgs)`. Rely on agentscope-runtime's native multi-turn message handling. Do not pre-populate InMemoryMemory manually.
- **D-04:** The client's messages array format follows the existing Phase 2 contract (role + content objects). No new message format is introduced.
- **D-05:** Primary tests use mocked LLM calls. Tests assert that the message array passed to the model contains the full multi-turn history. This is deterministic, repeatable, and consistent with Phase 2-4 mock patterns.
- **D-06:** Smoke script (optional) can demonstrate end-to-end multi-turn flow with a real LLM, but automated CI tests rely on mocks only.
- **D-07:** Success criteria tests: (1) a multi-turn request (3+ messages) results in the agent receiving all prior messages, (2) a single-turn request (1 message) behaves identically to current Phase 4 behavior (backward compatibility).

### Claude's Discretion
- Exact test structure and assertions, as long as they verify full message history is passed to the agent.
- Whether to add any helper/utilities for multi-turn message construction in tests.
- Internal module layout changes (if any) to support context continuity testing.

### Deferred Ideas (OUT OF SCOPE)
- Server-side session state management -- Phase 6/7 introduce session persistence.
- Session ID / session identifier -- not needed when client manages history.
- Pre-populating InMemoryMemory manually -- deferred unless research shows direct msgs passing is insufficient.
- Context window limits / truncation strategies -- deferred to future work.
- Multi-user session isolation -- v1 is for personal R&D validation.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAP-04 | User can verify context continuity across multi-turn chat within a session. | Verified via source code analysis: `ReActAgent.reply()` accepts `list[Msg]`, stores all via `memory.add()`, formats full history into model prompt. The Runner converts `request.input` to `list[Msg]` via `message_to_agentscope_msg()` and passes as `msgs`. Multi-turn arrays pass through intact. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| agentscope-runtime | 1.1.3 | Agent runtime with ReActAgent | Project framework under test; handles multi-turn natively via `reply(msgs)` |
| pytest | 9.0.3 | Test runner | Established from Phase 1-4; all existing tests use pytest |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi.testclient | (via FastAPI) | HTTP-level testing | Use TestClient for SSE endpoint tests (existing pattern) |
| unittest.mock | (stdlib) | Mocking LLM calls | Use patch/AsyncMock to avoid real LLM calls (D-05) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TestClient (sync) | httpx.AsyncClient | Async client would be more realistic but adds complexity; TestClient is the established pattern |
| Mock handler at query_handler | Mock at model level | Model-level mock tests framework internals; handler-level mock tests the contract (preferred per D-05) |

**Installation:**
No new packages needed. Phase 5 uses existing test infrastructure.

## Architecture Patterns

### Verified Data Flow: Multi-Turn Messages

```
Client POST /process
  body.input: [
    {role: "user", content: [{type: "text", text: "Hello"}]},
    {role: "assistant", content: [{type: "text", text: "Hi!"}]},
    {role: "user", content: [{type: "text", text: "What did I say?"}]}
  ]
      |
      v
AgentApp._stream_generator()
      |
      v
Runner.stream_query(request)
  request = AgentRequest(**request)        [runner.py:222]
  msgs = message_to_agentscope_msg(request.input)  [runner.py:259]
  # Returns list[Msg] preserving all items  [message.py:361-389]
      |
      v
Runner._call_handler_streaming(query_handler, msgs=msgs, ...)
  # query_handler = chat_query bound method
      |
      v
chat_query(self, msgs, request=None, ...)
  agent = ReActAgent(..., memory=InMemoryMemory())  [query.py:45-57]
  async for msg, last in stream_printing_messages(
      agents=[agent],
      coroutine_task=agent(msgs),    # msgs = list[Msg] of all turns
  ):
      |
      v
AgentBase.__call__(msgs)             [_agent_base.py:448]
  await self.reply(msgs)             [_agent_base.py:455]
      |
      v
ReActAgent.reply(msg)               [_react_agent.py:376]
  await self.memory.add(msg)         [_react_agent.py:396]
  # InMemoryMemory.add() accepts list[Msg]:
  #   if isinstance(memories, Msg): memories = [memories]
  #   for msg in memories: self.content.append((deepcopy(msg), marks))
  # All messages stored, no truncation                 [_in_memory_memory.py:93-135]
      |
      v
ReActAgent._reasoning()             [_react_agent.py:540]
  prompt = await self.formatter.format(
      msgs=[
          Msg("system", self.sys_prompt, "system"),
          *await self.memory.get_memory(...)   # Returns ALL stored messages
      ],
  )
  # Model receives system prompt + ALL prior turns + new message
```

**Key finding:** The framework natively handles multi-turn `list[Msg]` input. When `memory.add()` receives a list, it stores every message individually. When `_reasoning()` formats the prompt, it includes all messages from memory. No special handling needed. [VERIFIED: source code analysis of agentscope/_react_agent.py, _agent_base.py, _in_memory_memory.py]

### Recommended Project Structure
```
tests/
├── conftest.py           # Existing fixtures (extend with multi-turn payload)
├── test_chat_stream.py   # Existing SSE lifecycle tests (preserve)
├── test_context.py       # NEW: Phase 5 multi-turn context tests
└── ...
```

### Pattern 1: Multi-Turn Mock Handler Test
**What:** Test that sends a multi-turn message array and verifies the handler receives all messages.
**When to use:** For every multi-turn scenario in Phase 5.
**Example:**
```python
# Pattern: Capture msgs received by the handler
captured_msgs = []

async def _capturing_handler(msgs, request=None, response=None, **kwargs):
    """Handler that captures the msgs parameter for assertion."""
    captured_msgs.extend(msgs if isinstance(msgs, list) else [msgs])
    # Yield a response to complete the SSE lifecycle
    from agentscope.message import Msg
    msg = Msg(name="agentops", content=[{"type": "text", "text": "Response"}], role="assistant")
    yield msg, True

# In test:
from src.main import app
with patch.object(app._runner, "query_handler", _capturing_handler):
    response = client.post("/process", json=multi_turn_payload)

assert len(captured_msgs) == 3  # All 3 messages received
```

### Pattern 2: Model-Level Mock for Full Chain Validation
**What:** Mock the OpenAIChatModel to verify the prompt contains full history.
**When to use:** When testing the complete chain from request to model invocation.
**Example:**
```python
# Pattern: Mock the model to capture formatted prompt
async def _mock_model_call(prompt, **kwargs):
    """Mock model that captures the prompt for inspection."""
    _mock_model_call.captured_prompt = prompt
    # Return an async generator or response object matching expected interface
    ...

# Inspect prompt to verify all prior messages are present
assert any("first message text" in str(block) for block in _mock_model_call.captured_prompt)
```

### Anti-Patterns to Avoid
- **Testing with real LLM calls in CI:** Non-deterministic, slow, requires API keys. Use mocks per D-05.
- **Pre-populating InMemoryMemory manually:** The framework handles this via `reply(msgs)`. Manual pre-population duplicates logic and can cause double-counting of messages. [VERIFIED: ReActAgent.reply() line 396 calls `memory.add(msg)` automatically]
- **Creating server-side session state in this phase:** Explicitly deferred to Phase 6/7 per CONTEXT.md.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-turn message parsing | Custom message history parser | `message_to_agentscope_msg()` in the Runner | The framework already converts `request.input` list to `list[Msg]` with proper grouping by original_id [VERIFIED: agentscope_runtime/adapters/agentscope/message.py:361-389] |
| Memory management for multi-turn | Manual InMemoryMemory.add() calls before agent() | Just pass `msgs` to `agent(msgs)` | `ReActAgent.reply()` automatically adds input messages to memory via `self.memory.add(msg)` at line 396 [VERIFIED: _react_agent.py] |
| Message format conversion | Custom Msg construction from request dicts | `message_to_agentscope_msg()` handles role mapping, content block conversion, and id grouping | Complex conversion logic including ToolUseBlock, ToolResultBlock, ThinkingBlock, ImageBlock etc. [VERIFIED: message.py full file] |

**Key insight:** The entire multi-turn context flow is handled by agentscope-runtime internally. The project code just needs to pass `msgs` to `agent(msgs)` -- which it already does in `query.py:63`. Phase 5 is validation-only.

## Common Pitfalls

### Pitfall 1: Message deduplication in InMemoryMemory.add()
**What goes wrong:** `InMemoryMemory.add()` has `allow_duplicates=False` by default and checks `existing_ids = {msg.id for msg, _ in self.content}`. If the same message object (same `id`) is added twice, the second addition is silently dropped.
**Why it happens:** Each `Msg` object gets a unique `id` via `shortuuid.uuid()` at creation time. When `message_to_agentscope_msg()` processes the request input, it preserves original IDs from metadata or assigns IDs. If the client re-sends the same messages with the same IDs across requests, deduplication is correct behavior.
**How to avoid:** Ensure test payloads use distinct messages. The framework assigns unique IDs during `message_to_agentscope_msg()` conversion, so this should not be an issue for well-formed multi-turn arrays.
**Warning signs:** Messages appear "missing" from memory after adding a multi-turn array.

### Pitfall 2: Deep copy in memory.add() adds overhead
**What goes wrong:** `InMemoryMemory.add()` does `self.content.append((deepcopy(msg), deepcopy(marks)))` for each message. For very long conversation histories, this creates significant memory overhead.
**Why it happens:** The framework defensively deep-copies to prevent mutation. This is by design.
**How to avoid:** Not a concern for Phase 5 validation (small test payloads). Noted for future context window / truncation work (deferred per CONTEXT.md).

### Pitfall 3: Mock handler signature mismatch
**What goes wrong:** The mock handler in tests does not match the actual `chat_query` signature `(self, msgs, request=None, **kwargs)`. When using `patch.object(app._runner, "query_handler", mock_handler)`, the mock receives `(msgs, request=..., response=...)` -- note `self` is NOT passed because the handler is already a bound method.
**Why it happens:** The runner binds the query handler as `types.MethodType(handler, self._runner)`, so when the mock replaces the bound method, it receives positional args without `self`.
**How to avoid:** Follow the existing pattern from `test_chat_stream.py`: `_handler(msgs, request=None, response=None, **kwargs)`. Do NOT include `self` in the mock signature.
**Warning signs:** TypeError about unexpected keyword argument or missing positional argument.

### Pitfall 4: Assuming memory persists across requests
**What goes wrong:** Writing tests that expect a second request to "remember" the first request's context without re-sending the full history.
**Why it happens:** Each request creates a fresh `ReActAgent` with a fresh `InMemoryMemory()` (query.py:55). Memory is request-scoped, not session-scoped.
**How to avoid:** Each test request must include the FULL conversation history in the `input` array. This is the design per D-01/D-02. Server-side session persistence is Phase 6/7.
**Warning signs:** Tests pass with single-turn but fail with multi-turn when the second request omits prior history.

### Pitfall 5: SSE event parsing fragility
**What goes wrong:** Tests that parse SSE events break when the framework changes event structure.
**Why it happens:** The existing `_parse_sse_events()` helper in `test_chat_stream.py` strips empty lines and `[DONE]`, then JSON-parses. This is adequate but brittle.
**How to avoid:** Reuse the existing `_parse_sse_events()` helper from `test_chat_stream.py`. Do not re-implement SSE parsing.

## Code Examples

Verified patterns from source code analysis:

### Multi-Turn Request Payload (3 messages)
```python
# Source: agentscope_runtime AgentRequest schema + message_to_agentscope_msg conversion
multi_turn_payload = {
    "input": [
        {
            "role": "user",
            "content": [{"type": "text", "text": "My name is Alice."}],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello Alice!"}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": "What is my name?"}],
        },
    ]
}
```

### InMemoryMemory.add() Handles list[Msg]
```python
# Source: agentscope/memory/_working_memory/_in_memory_memory.py:93-135
# VERIFIED: add() accepts Msg, list[Msg], or None
async def add(self, memories: Msg | list[Msg] | None, ...):
    if memories is None:
        return
    if isinstance(memories, Msg):
        memories = [memories]
    # ... stores each message individually
    for msg in memories:
        self.content.append((deepcopy(msg), deepcopy(marks)))
```

### ReActAgent.reply() Adds All Messages to Memory
```python
# Source: agentscope/agent/_react_agent.py:376-396
async def reply(self, msg: Msg | list[Msg] | None = None, ...):
    # Record the input message(s) in the memory
    await self.memory.add(msg)  # msg can be list[Msg] -- all stored
    # ... then _reasoning() uses self.memory.get_memory() for full history
```

### ReActAgent._reasoning() Formats Full History
```python
# Source: agentscope/agent/_react_agent.py:540-568
prompt = await self.formatter.format(
    msgs=[
        Msg("system", self.sys_prompt, "system"),
        *await self.memory.get_memory(exclude_mark=...),
    ],
)
# ALL messages from memory are included in the model prompt
```

### Existing Mock Handler Pattern (from test_chat_stream.py)
```python
# Source: tests/test_chat_stream.py:15-33
def _make_mock_handler(text_chunks):
    async def _handler(msgs, request=None, response=None, **kwargs):
        for i, text in enumerate(text_chunks):
            is_last = i == len(text_chunks) - 1
            msg = Msg(name="agentops", content=[{"type": "text", "text": text}], role="assistant")
            yield msg, is_last
    return _handler

# Usage:
mock_handler = _make_mock_handler(["Response text"])
from src.main import app
with patch.object(app._runner, "query_handler", mock_handler):
    response = client.post("/process", json=payload)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pre-populate memory before agent call | Pass msgs directly to agent(msgs) | agentscope-runtime 1.x | Memory population is automatic inside reply() |
| Session state on server | Client-managed history | agentscope-runtime architecture | Request-scoped agents with client-managed context |

**Deprecated/outdated:**
- Manual `memory.add()` before calling agent: Not needed since `reply()` does it automatically at line 396 of `_react_agent.py`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `message_to_agentscope_msg()` function preserves all messages in the input array without filtering or truncation. | Architecture Patterns | Multi-turn context would be lost; would need custom message handling. Mitigated by source code verification showing list comprehension preserves all items. |
| A2 | The mock handler pattern (patching `app._runner.query_handler`) works correctly for multi-turn payloads the same way it works for single-turn. | Code Examples | Tests would not accurately validate multi-turn flow. Mitigated by the pattern being framework-level (Runner passes msgs as kwarg regardless of length). |

**Note:** All other claims in this research were verified via direct source code analysis. The two assumed claims above are HIGH confidence based on code inspection but tagged because they were not tested at runtime during research.

## Open Questions

1. **Message ID stability across re-sends**
   - What we know: `message_to_agentscope_msg()` preserves original IDs from `message.id` or falls back to `msg.id`. `InMemoryMemory.add()` deduplicates by `msg.id`.
   - What's unclear: Whether the deduplication causes issues when a client re-sends the same assistant response (same ID) along with prior messages.
   - Recommendation: In tests, use fresh payloads without reusing message IDs across turns. This matches the real-world pattern where each new request includes fresh message objects. The risk is LOW because in practice, the framework generates unique IDs.

2. **Exact SSE event structure for multi-turn**
   - What we know: The SSE lifecycle (created -> in_progress -> content chunks -> completed) is the same regardless of input message count. The Runner wraps events uniformly.
   - What's unclear: Whether multi-turn inputs with prior assistant messages trigger any special behavior in the stream adapter.
   - Recommendation: Tests should verify the SSE lifecycle completes successfully for multi-turn payloads, using the existing `_parse_sse_events()` helper. No special handling expected.

## Environment Availability

Step 2.6: SKIPPED (no new external dependencies -- Phase 5 uses existing test infrastructure and project code only).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | None (defaults) |
| Quick run command | `uv run pytest tests/test_context.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAP-04 | Multi-turn request (3+ messages) passes all messages to agent | unit | `uv run pytest tests/test_context.py::test_multi_turn_passes_full_history -x` | Wave 0 |
| CAP-04 | Single-turn request behaves identically to Phase 4 (backward compat) | unit | `uv run pytest tests/test_context.py::test_single_turn_backward_compatible -x` | Wave 0 |
| CAP-04 | SSE lifecycle completes for multi-turn payload | integration | `uv run pytest tests/test_context.py::test_multi_turn_sse_lifecycle -x` | Wave 0 |
| CAP-04 | Agent receives prior assistant messages as context | unit | `uv run pytest tests/test_context.py::test_prior_assistant_messages_in_context -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_context.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_context.py` -- covers CAP-04 multi-turn context validation (all 4 tests above)
- [ ] Multi-turn payload fixture in `tests/conftest.py` -- extends existing fixtures

*(Existing test infrastructure covers framework, fixtures, and SSE parsing utilities. Only new test file and fixtures needed.)*

## Security Domain

> This phase introduces no new endpoints, no user input beyond the existing `/process` contract, and no data persistence. Security posture is unchanged from Phase 4.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A -- no auth changes |
| V3 Session Management | no | N/A -- no server-side sessions |
| V4 Access Control | no | N/A -- no authorization changes |
| V5 Input Validation | yes | Pydantic AgentRequest schema validates message structure (existing) |
| V6 Cryptography | no | N/A -- no crypto changes |

### Known Threat Patterns for Context Continuity

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Message injection via crafted input array | Tampering | AgentRequest schema validates role/content structure; agentscope Msg objects enforce types |
| Excessive payload size (DoS via large history) | Denial of Service | Deferred to context window / truncation work (per CONTEXT.md); current phase is validation only |

## Sources

### Primary (HIGH confidence)
- agentscope/agent/_react_agent.py -- ReActAgent.reply() and _reasoning() source code (verified multi-turn message handling)
- agentscope/agent/_agent_base.py -- AgentBase.__call__() source code (verified msg forwarding to reply())
- agentscope/memory/_working_memory/_in_memory_memory.py -- InMemoryMemory.add() source code (verified list[Msg] handling)
- agentscope/memory/_working_memory/_base.py -- MemoryBase abstract interface
- agentscope_runtime/engine/runner.py -- Runner.stream_query() source code (verified message_to_agentscope_msg conversion)
- agentscope_runtime/engine/app/agent_app.py -- AgentApp query decorator and stream generator
- agentscope_runtime/adapters/agentscope/message.py -- message_to_agentscope_msg() source code (verified list conversion preserves all messages)
- agentscope/pipeline/_functional.py -- stream_printing_messages() source code (verified async generator flow)

### Secondary (MEDIUM confidence)
- tests/test_chat_stream.py -- established mock handler pattern for SSE testing
- tests/conftest.py -- shared fixtures (configured_env, client, valid_payload)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new packages, using existing verified infrastructure
- Architecture: HIGH - full source code trace from HTTP request to model prompt verified
- Pitfalls: HIGH - derived from source code analysis and existing test patterns

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable -- no fast-moving dependencies)
