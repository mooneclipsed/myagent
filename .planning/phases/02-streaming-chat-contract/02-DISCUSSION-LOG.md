# Phase 2: Streaming Chat Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11T07:38:00Z
**Phase:** 02-streaming-chat-contract
**Areas discussed:** Request Contract, Streaming Event Model, Verification Strategy, Error Semantics

---

## Request Contract

| Option | Description | Selected |
|--------|-------------|----------|
| `messages` array | Future-friendly for later phases and multi-turn flows while staying simple in Phase 2. | ✓ |
| Single `message` string | Fastest now, but likely requires a breaking contract change later. | |
| Custom expanded body | More flexible immediately, but adds unnecessary Phase 2 design weight. | |
| Claude decides | Delegate the decision to Claude. | |

**User's choice:** `messages` array
**Notes:** Keep the Phase 2 body minimal; don't prematurely add later-phase fields.

---

## Streaming Event Model

| Option | Description | Selected |
|--------|-------------|----------|
| Typed SSE events | Explicit lifecycle such as start / delta / complete. Easier to verify and extend later. | ✓ |
| Raw content chunks | Minimal implementation, but weaker semantics for later tracing and validation. | |
| Full-text snapshots | Simple client rendering, but more wasteful and less representative of streaming. | |
| Claude decides | Delegate the decision to Claude. | |

**User's choice:** Typed SSE events
**Notes:** The stream lifecycle should be explicit and testable.

---

## Verification Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| `pytest` + smoke script | Reproducible automated checks plus a runnable script entrypoint. | ✓ |
| `pytest` only | Strong automation, but no direct operator/demo flow. | |
| Manual/script-first | Faster initial delivery, but weaker regression protection. | |
| Claude decides | Delegate the decision to Claude. | |

**User's choice:** `pytest` + smoke script
**Notes:** Repeated calls only need to prove stream lifecycle stability and completion, not identical text output.

---

## Error Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP + SSE mixed | Pre-stream request errors use HTTP; post-start runtime errors use SSE error events. | ✓ |
| All SSE errors | Uniform transport, but more awkward for invalid requests. | |
| All HTTP errors | Simpler pre-stream handling, but poor semantics for mid-stream failures. | |
| Claude decides | Delegate the decision to Claude. | |

**User's choice:** HTTP + SSE mixed
**Notes:** Runtime failures after stream start should terminate the stream cleanly after an SSE error event.

## Claude's Discretion

- Endpoint path naming.
- Event field naming.
- Internal module layout and verification script shape.

## Deferred Ideas

- Request-scoped agent payloads and config switching — Phase 3.
- Tracing events for skill/tool/MCP — Phase 4.
- Multi-turn continuity guarantees — Phase 5.
- Resume and persistence behavior — Phases 6-8.
