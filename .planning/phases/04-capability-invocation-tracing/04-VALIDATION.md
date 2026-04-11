---
phase: 04
slug: capability-invocation-tracing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_tools.py tests/test_mcp.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_tools.py tests/test_mcp.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CAP-02 | — | Tool function returns ToolResponse, no arbitrary code execution | unit | `uv run pytest tests/test_tools.py::test_tool_registration -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CAP-02 | — | Tool response format validated by framework schema | unit | `uv run pytest tests/test_tools.py::test_tool_response_format -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | CAP-03 | — | MCP client lifecycle (connect/register/close) follows LIFO order | unit | `uv run pytest tests/test_mcp.py::test_mcp_client_lifecycle -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | CAP-02 | — | Toolkit shared across requests, read-only during handling | integration | `uv run pytest tests/test_tools.py::test_toolkit_shared -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | CAP-02 | — | Agent invokes registered tool through streaming chat | integration | `uv run pytest tests/test_tools.py::test_tool_call_in_chat -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | CAP-03 | — | Agent invokes MCP tool through streaming chat | integration | `uv run pytest tests/test_mcp.py::test_mcp_tool_in_chat -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | CAP-02, CAP-03 | — | SSE stream includes tool call results without breaking lifecycle | integration | `uv run pytest tests/test_tools.py::test_tool_sse_lifecycle -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tools.py` — stubs for CAP-02 tool registration, invocation, response format
- [ ] `tests/test_mcp.py` — stubs for CAP-03 MCP client lifecycle and tool invocation
- [ ] `scripts/smoke_04.sh` — Phase 4 smoke verification script following Phase 1/2/3 pattern

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end tool call visible in agent response | CAP-02 | Requires real LLM that supports tool calling | Start service, send chat message asking for weather, verify tool call appears in streamed response |
| End-to-end MCP call visible in agent response | CAP-03 | Requires real LLM + running MCP server subprocess | Start service with MCP server, send chat asking for time, verify MCP call appears in streamed response |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
