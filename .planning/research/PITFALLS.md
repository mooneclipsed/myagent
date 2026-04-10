# Pitfalls Research

**Domain:** Agent testing platform with streaming chat, tool/skill/MCP integration, resumable sessions
**Researched:** 2026-04-10
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Streaming output is not tied to tool/skill/MCP lifecycle

**What goes wrong:**
The stream shows partial assistant output while tool/skill/MCP calls are still in-flight, leading to incoherent transcripts, missing tool results, or duplicated responses when the chain finishes.

**Why it happens:**
Streaming is implemented as a simple token stream without coordinating with call-chain checkpoints, so the API emits before tool results are available or before the agent has finalized the turn.

**How to avoid:**
Define explicit stream phases (e.g., "assistant_thinking", "tool_call", "tool_result", "assistant_final") and gate output on tool completion. Emit structured events instead of raw text-only streaming.

**Warning signs:**
- Clients see "hanging" tool calls with no results while streaming continues
- Logs show assistant responses finalized before tool/skill/MCP results arrive
- Users report duplicated or contradictory final messages

**Phase to address:**
Phase 1 (Streaming API + call-chain contract)

---

### Pitfall 2: Request-scoped agent creation breaks continuity

**What goes wrong:**
Each request recreates the agent without restoring correct context or state, causing inconsistent behavior and unstable call chains across streamed turns.

**Why it happens:**
The platform treats the agent as stateless while the runtime expects continuity (memory, system prompts, tool registry) to be reconstructed precisely.

**How to avoid:**
Persist a complete, versioned agent config snapshot per session and rehydrate deterministically on each request. Validate that tool/skill/MCP registries match across resumes.

**Warning signs:**
- Same prompt yields different tool/skill selection across identical sessions
- Resume tests pass for one backend (JSON) but fail for Redis
- Hidden config drift between requests

**Phase to address:**
Phase 2 (Agent config persistence + deterministic rehydration)

---

### Pitfall 3: Tool/MCP context is not serialized fully

**What goes wrong:**
Resumed sessions lose tool arguments, MCP connection state, or intermediate reasoning required to complete a chain, causing failures or repeated calls.

**Why it happens:**
Only the chat transcript is persisted; tool call state, partial outputs, or MCP session metadata are ignored.

**How to avoid:**
Define a canonical session state schema that includes tool call queue, tool outputs, MCP session identifiers, and context window state. Verify round-trip serialization for both JSON and Redis backends.

**Warning signs:**
- Resume works for simple chat, fails when tools are used
- Tool calls are re-issued after resume with same arguments
- MCP calls error with "unknown session" or missing context

**Phase to address:**
Phase 3 (Session schema + persistence backends)

---

### Pitfall 4: Streaming backpressure is ignored

**What goes wrong:**
Slow clients or downstream consumers cause memory growth or stalled event loops, leading to timeouts and dropped connections.

**Why it happens:**
Server-side streaming is implemented without flow control or timeouts, and the runtime keeps producing tokens regardless of client read speed.

**How to avoid:**
Implement bounded queues and enforce timeouts; stop generation if the client disconnects. Use FastAPI/Starlette disconnect signals to cancel in-flight tasks.

**Warning signs:**
- Memory grows during long streams
- Many open connections linger in CLOSE_WAIT
- Streaming stalls when client is slow or network is unstable

**Phase to address:**
Phase 1 (Streaming API + cancellation)

---

### Pitfall 5: Tool/skill/MCP errors are surfaced as generic 500s

**What goes wrong:**
Tool failures are opaque, making it impossible to diagnose call-chain stability problems, which is the core purpose of the platform.

**Why it happens:**
Error handling is centralized at the API layer rather than at the call-chain level, losing tool-specific context and structured error metadata.

**How to avoid:**
Define error classes per call step (skill/tool/MCP) and stream structured error events with unique call IDs. Store error metadata in session logs.

**Warning signs:**
- All failures look identical in logs
- No way to correlate tool calls with failure points
- Users must enable debug logs to see anything useful

**Phase to address:**
Phase 2 (Call-chain observability)

---

### Pitfall 6: Mixed backends diverge in behavior

**What goes wrong:**
JSON-file resume and Redis resume behave differently, causing false confidence or wasted debugging time.

**Why it happens:**
Different serialization formats, TTLs, or data models are used per backend, and one backend is treated as the "real" path.

**How to avoid:**
Use a single canonical session schema and test suite for both backends. Run identical fixtures for JSON and Redis and diff results.

**Warning signs:**
- Tests pass only on one backend
- Subtle differences in restored context order or timestamps
- Tool call IDs collide or reset differently

**Phase to address:**
Phase 3 (Persistence parity testing)

---

### Pitfall 7: Context window management is implicit

**What goes wrong:**
Prompt context grows uncontrolled, causing token bloat, inconsistent tool selection, or hard failures from model limits.

**Why it happens:**
No explicit policy exists for truncation, summary, or tool output compaction in the persistence layer.

**How to avoid:**
Define and test context policies (e.g., summarize tool outputs, cap transcript length, store full logs separately). Validate that context serialization respects limits.

**Warning signs:**
- Token usage spikes as sessions grow
- Long sessions fail while short sessions pass
- Tool results dominate the prompt

**Phase to address:**
Phase 3 (Context policy + persistence)

---

### Pitfall 8: MCP capability boundaries are assumed, not verified

**What goes wrong:**
The platform relies on MCP features or behaviors not supported by the runtime, breaking integrations late.

**Why it happens:**
MCP and runtime capabilities are inferred from examples rather than validated against actual protocol behavior.

**How to avoid:**
Build explicit MCP conformance tests for the runtime and validate required capabilities early (connect, list tools, invoke, error handling).

**Warning signs:**
- "Works locally" only for a subset of MCP servers
- Integration breaks on resume or reconnection
- Ambiguous error messages for MCP calls

**Phase to address:**
Phase 2 (MCP conformance tests)

---

### Pitfall 9: Tool/skill side effects are non-idempotent

**What goes wrong:**
Retries or resumed sessions re-run tool calls and produce duplicate side effects, skewing test results.

**Why it happens:**
Tool calls are treated as pure functions, but real tools write state or perform external calls.

**How to avoid:**
Record tool call IDs and results; implement idempotency checks in the tool wrapper and store results in session state.

**Warning signs:**
- Duplicate external actions during resume tests
- Tool results differ between identical resumes
- Retrying a session causes a new side effect

**Phase to address:**
Phase 2 (Tool wrapper + idempotency)

---

### Pitfall 10: Metrics and traces are omitted early

**What goes wrong:**
Call-chain stability cannot be measured objectively, so regressions go unnoticed.

**Why it happens:**
The platform is treated as a quick prototype without minimal telemetry (call counts, latency, failure rates).

**How to avoid:**
Add structured logs and basic metrics (call ID, step type, duration, error code) from day one. Emit logs in both streaming and persisted logs.

**Warning signs:**
- No baseline for "stable" call chain
- Regressions are discovered only by manual testing
- Can't reproduce failures from logs

**Phase to address:**
Phase 1 (Observability baseline)

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing only chat transcript | Faster implementation | Resume fails for tool/MCP chains | Never |
| Single backend-specific schema | Less code | JSON and Redis diverge | Only for a throwaway spike |
| Ignoring disconnect handling | Simpler streaming | Leaked tasks and stuck connections | Never |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| MCP servers | Assuming tool list is static | Re-fetch tool list per session resume and validate IDs |
| Redis | Relying on default TTLs | Explicitly set TTLs and test expiry behavior |
| JSON storage | Using relative paths in runtime | Use explicit storage root and normalize paths |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded streaming buffers | Memory growth, stalled streams | Bounded queues + cancellation | Concurrent long streams |
| Tool calls on event loop | Streaming freezes during tool I/O | Offload tool I/O to worker threads | Moderate concurrency |
| Full transcript on every turn | Token bloat, slow responses | Summarize/compact context | Longer sessions |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging tool outputs with secrets | Secret leakage into logs | Redact sensitive fields in tool output |
| Allowing arbitrary tool configs per request | Remote code or data exposure | Whitelist tool registry and validate config |
| Persisting raw .env contents | Accidental credential exposure | Store only resolved model/provider IDs |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Streaming events are raw text only | Hard to understand tool steps | Use structured events with type and IDs |
| No session resume feedback | Users cannot trust persistence | Surface resume state and backend used |
| Tool errors hidden in final text | Users miss why it failed | Stream explicit error events |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Streaming API:** Often missing disconnect cancellation — verify in-flight tasks are cancelled on client drop
- [ ] **Resume support:** Often missing tool/MCP state — verify tool results survive a restart
- [ ] **Tool invocation:** Often missing idempotency — verify retries do not duplicate side effects
- [ ] **Persistence backends:** Often missing parity tests — verify JSON and Redis produce identical state

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Streaming not tied to lifecycle | MEDIUM | Add structured event phases, replay logs for validation |
| Missing tool/MCP state | HIGH | Introduce canonical session schema and migrate stored sessions |
| Backend divergence | MEDIUM | Create fixture-driven parity tests and normalize schema |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Streaming lifecycle mismatch | Phase 1 | Stream includes tool_call/tool_result events in order |
| No agent continuity | Phase 2 | Same session rehydrate yields identical call chain |
| Missing tool/MCP state | Phase 3 | Resume tests pass with tool usage |
| Backpressure ignored | Phase 1 | Cancel on disconnect; bounded queue tests |
| Opaque errors | Phase 2 | Structured error events with call IDs |
| Backend divergence | Phase 3 | JSON and Redis fixtures match |
| Context bloat | Phase 3 | Context policy tests stay under limit |
| MCP capability assumptions | Phase 2 | MCP conformance tests pass |
| Non-idempotent tools | Phase 2 | Tool wrapper prevents duplicate side effects |
| Missing telemetry | Phase 1 | Metrics/logs include call chain timing |

## Sources

- Personal experience / known issues (no external sources consulted)

---
*Pitfalls research for: AgentScope-based agent testing platforms*
*Researched: 2026-04-10*
