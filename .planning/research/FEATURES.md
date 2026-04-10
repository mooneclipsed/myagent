# Feature Research

**Domain:** agent testing platform for tool/skill/MCP/context validation with resumable sessions
**Researched:** 2026-04-10
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Streaming chat endpoint (SSE/websocket) | Agent testing requires live, incremental outputs | MEDIUM | Must surface partial model tokens and tool/skill/MCP events in-order; include request-scoped agent creation per session. |
| Deterministic run capture (inputs, config, timestamps) | Validation needs reproducible runs | MEDIUM | Store model config, tool registry, agent config, and seed where supported; tie to session/run IDs. |
| Tool/skill invocation tracing | Core purpose is verifying call chains | MEDIUM | Log each invocation with args/result, success/error, latency; include correlation IDs. |
| MCP call visibility | MCP is explicitly in scope | MEDIUM | Record MCP server/endpoint, tool name, schema version, request/response payloads. |
| Context state inspection | Validate context management behavior | MEDIUM | Provide snapshot of context before/after each step; distinguish system vs session vs tool-added context. |
| Session persistence + resume (JSON + Redis) | Required to validate resumability | HIGH | Must rehydrate agent state reliably and resume streaming; compare backend behavior. |
| Minimal auth / access control | Even local testing needs guardrails | LOW | API key or local-only binding; avoid multi-user auth complexity in v1. |
| Error surface with actionable diagnostics | Validation depends on failure clarity | MEDIUM | Structured error objects with stage (model/tool/MCP/persistence) and retry guidance. |
| Config-driven agent instantiation | Explicit project requirement | MEDIUM | Accept config file path or JSON payload; validate schema and return defaults used. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Call-chain stability score (pass/fail + reason) | Makes validation objective and repeatable | MEDIUM | Define invariants: ordering, required steps, timeouts, idempotency; emit summary report. |
| Step-by-step replay (deterministic re-run) | Enables precise debugging of flaky chains | HIGH | Requires full capture of prompts, tool outputs, MCP responses, and seeded randomness support. |
| Backend comparison harness (JSON vs Redis) | Directly validates persistence assumptions | MEDIUM | One request runs both backends and diffs resume behavior. |
| Contract tests for tool/MCP schemas | Catches breaking changes early | MEDIUM | Validate inputs/outputs against schemas; fail fast before runtime. |
| Context diff visualizer | Highlights unintended context drift | MEDIUM | Show delta after each step, including token counts and source attribution. |
| Scenario runner (YAML test cases) | Batch validation without manual chat | HIGH | Define cases with expected tool/MCP events; integrates with CI later. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multi-agent orchestration | Sounds powerful for testing | Blurs single-agent call-chain focus; increases nondeterminism | Keep single-agent in v1; add multi-agent later once invariants are stable. |
| GUI-heavy dashboard | Easier browsing of runs | High effort, slows core validation; duplicates CLIs/log viewers | Provide JSON/HTML reports and lightweight CLI summaries. |
| Full user management | Feels like a real product | Overkill for personal R&D; adds auth complexity | Use API key or localhost-only binding. |
| Real-time collaboration | Multiple testers at once | Requires concurrency controls and audit trails | Defer until multi-user needs are proven. |

## Feature Dependencies

```
Streaming chat endpoint
    └──requires──> Config-driven agent instantiation
                       └──requires──> Tool/skill registry

Tool/skill invocation tracing
    └──requires──> Deterministic run capture

MCP call visibility
    └──requires──> MCP client integration

Session persistence + resume
    └──requires──> Context state inspection
                       └──requires──> Deterministic run capture

Call-chain stability score
    └──requires──> Tool/skill invocation tracing
                       └──requires──> MCP call visibility

Step-by-step replay
    └──requires──> Deterministic run capture
                       └──requires──> Session persistence + resume

Backend comparison harness
    └──requires──> Session persistence + resume
```

### Dependency Notes

- **Streaming chat endpoint requires config-driven agent instantiation:** each request must create a consistent agent from config to make comparisons meaningful.
- **Session persistence requires context state inspection:** resume must reconstruct context accurately; snapshots are the only reliable verification.
- **Call-chain stability score requires tracing:** scoring depends on ordered, correlated tool/MCP events.
- **Step-by-step replay requires deterministic capture:** without full capture, replay cannot be trusted for root-cause analysis.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Streaming chat endpoint with request-scoped agent — core interaction surface for validation.
- [ ] Tool/skill/MCP invocation tracing — primary evidence for stable call chains.
- [ ] Context state inspection + persistence/resume (JSON + Redis) — validates resumable sessions and backend differences.
- [ ] Deterministic run capture + structured errors — makes failures reproducible and actionable.
- [ ] Config-driven agent instantiation — required to test agentscope-runtime behavior.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Call-chain stability score — add when baseline traces are reliable.
- [ ] Backend comparison harness — once resume is stable for both backends.
- [ ] Context diff visualizer — after snapshots are correct and complete.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Scenario runner (YAML test cases) — add when manual runs converge and repetition is a bottleneck.
- [ ] Step-by-step replay — depends on deterministic capture across all providers.
- [ ] Multi-agent orchestration — only after single-agent invariants are solved.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Streaming chat endpoint | HIGH | MEDIUM | P1 |
| Tool/skill/MCP invocation tracing | HIGH | MEDIUM | P1 |
| Session persistence + resume (JSON + Redis) | HIGH | HIGH | P1 |
| Context state inspection | HIGH | MEDIUM | P1 |
| Deterministic run capture | HIGH | MEDIUM | P1 |
| Structured error diagnostics | MEDIUM | MEDIUM | P1 |
| Call-chain stability score | MEDIUM | MEDIUM | P2 |
| Backend comparison harness | MEDIUM | MEDIUM | P2 |
| Context diff visualizer | MEDIUM | MEDIUM | P2 |
| Scenario runner (YAML) | MEDIUM | HIGH | P3 |
| Step-by-step replay | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Tool/skill tracing | LangSmith: per-run traces, tool calls | OpenAI Traces: step tracing, tool call spans | Minimal but complete trace with correlation IDs and payload capture. |
| Session replay | LangSmith: replay from traces | None/limited in basic eval tools | Defer to v2; focus on deterministic capture in v1. |
| Scenario/eval runner | OpenAI Evals / LM Evaluation Harness | Promptfoo test cases | Defer; keep manual runs + JSON exports in v1. |

## Sources

- Project context and requirements in `/Users/chengtong/OpenSource/myagent/.planning/PROJECT.md`
- Domain knowledge of common LLM testing tools (LOW confidence without external verification)

---
*Feature research for: agent testing platform focused on tool/skill/MCP/context validation*
*Researched: 2026-04-10*
