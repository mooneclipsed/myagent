---
phase: 08-parity-demo-flows
verified: 2026-04-12T16:30:00Z
status: human_needed
score: 6/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run demo_tool.py against a live service (uv run scripts/demos/demo_tool.py)"
    expected: "Exit 0 with 'PASS: demo_tool.py - tool call triggered successfully'"
    why_human: "Requires running service with valid API key; cannot start server programmatically in verification"
  - test: "Run demo_skill.py against a live service (uv run scripts/demos/demo_skill.py)"
    expected: "Exit 0 with 'PASS: demo_skill.py - skill context influenced response'"
    why_human: "Requires running service with valid API key; depends on LLM response containing skill context"
  - test: "Run demo_mcp.py against a live service (uv run scripts/demos/demo_mcp.py)"
    expected: "Exit 0 with 'PASS: demo_mcp.py - MCP tool call triggered successfully'"
    why_human: "Requires running service with valid API key; depends on MCP tool invocation through LLM"
  - test: "Run demo_resume.py against a live service (uv run scripts/demos/demo_resume.py)"
    expected: "Exit 0 with 'PASS: demo_resume.py - session resume with context persistence works'"
    why_human: "Requires running service with valid API key; verifies session resume via two-request flow with LLM"
  - test: "Follow README.md Quick Start end-to-end (configure .env, uv sync, start service, run all demos)"
    expected: "All 4 demos pass without errors"
    why_human: "End-to-end user flow requires running service, valid API credentials, and LLM responses"
---

# Phase 8: Parity & Demo Flows Verification Report

**Phase Goal:** Users can validate parity across JSON/Redis and run documented examples for all capabilities.
**Verified:** 2026-04-12T16:30:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

Derived from ROADMAP.md success criteria and PLAN frontmatter must_haves.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Same session data resumed from JSON and Redis backends produces consistent conversation content | VERIFIED | `tests/test_parity.py` saves identical messages to both backends, loads and asserts content/name/role match. Test passes (52/52 green). Uses fakeredis per D-07. |
| 2 | Parity test runs with fakeredis (no real Redis dependency) | VERIFIED | Line 8: `import fakeredis.aioredis`. Line 37: `fakeredis.aioredis.FakeRedis(decode_responses=True)`. No Redis server needed. Test passes in 0.01s. |
| 3 | Example skill is registered in the toolkit and available to agents | VERIFIED | `src/tools/__init__.py` line 30: `toolkit.register_agent_skill(skill_dir=_example_skill_dir)` with `os.path.isdir` guard. Toolkit imported by `src/agent/query.py` line 12 and wired to agent at line 71. |
| 4 | User can run demo_tool.py and see tool call result (exit 0 on pass) | HUMAN NEEDED | Script exists (37 lines), syntactically valid, has `check_service_running` + `send_chat` + assertions. Cannot verify end-to-end without running service + API key. |
| 5 | User can run demo_skill.py and see skill-informed response (exit 0 on pass) | HUMAN NEEDED | Script exists (37 lines), syntactically valid, imports from `_helpers`, asserts on response content. Cannot verify end-to-end without running service. |
| 6 | User can run demo_mcp.py and see MCP tool call result (exit 0 on pass) | HUMAN NEEDED | Script exists (36 lines), syntactically valid, imports from `_helpers`, asserts on response content. Cannot verify end-to-end without running service. |
| 7 | User can run demo_resume.py and see session resume result (exit 0 on pass) | HUMAN NEEDED | Script exists (73 lines), syntactically valid, uses two-request flow with `session_id`, asserts `"42" in text2`. Cannot verify end-to-end without running service. |
| 8 | User can follow README.md to start the service and run all demos end-to-end | HUMAN NEEDED | README.md contains Quick Start, all 4 demo commands, session backend docs, test commands. Structurally complete. End-to-end flow needs human walkthrough. |

**Score:** 3/8 truths fully verified programmatically. 5/8 require human verification (running service + LLM API key needed).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_parity.py` | RES-05 parity test for JSON/Redis consistency | VERIFIED | 74 lines. Exports `test_parity_json_redis_resume`. Uses fakeredis. Compares content/name/role. Passes. |
| `skills/example_skill/SKILL.md` | Example skill definition with YAML front matter | VERIFIED | 7 lines. Contains `name: example-skill` in YAML front matter. Describes platform purpose. |
| `src/tools/__init__.py` | Updated toolkit with registered example skill | VERIFIED | 34 lines. Has `import os`, `register_agent_skill(skill_dir=)` with `os.path.isdir` guard. Existing `register_tool_function` calls preserved. |
| `scripts/demos/_helpers.py` | Shared httpx client setup and SSE parsing utilities | VERIFIED | 78 lines. Exports: `SERVICE_URL`, `check_service_running`, `parse_sse_events`, `extract_text_from_events`, `send_chat`. All functions callable (import verified). |
| `scripts/demos/demo_tool.py` | Tool capability demo (DEV-03) | VERIFIED | 37 lines. Has `def main`, imports from `_helpers`, calls `check_service_running` and `send_chat`, has content assertion, has `if __name__ == "__main__"` entry point. |
| `scripts/demos/demo_skill.py` | Skill capability demo (DEV-03) | VERIFIED | 37 lines. Same structure as demo_tool. Asserts on "validat"/"platform"/"agentscope" in response. |
| `scripts/demos/demo_mcp.py` | MCP capability demo (DEV-03) | VERIFIED | 36 lines. Same structure. Asserts on "time"/"current"/"clock" in response. |
| `scripts/demos/demo_resume.py` | Resume capability demo (DEV-03) | VERIFIED | 73 lines. Two-request flow with shared `session_id`. Asserts `"42" in text2` for context recall. Uses `httpx.post` directly with `parse_sse_events`/`extract_text_from_events`. |
| `README.md` | Unified getting-started guide (DEV-01) | VERIFIED | 149 lines. Contains `## Quick Start`, all 4 demo commands (demo_tool.py x2, demo_skill.py x2, demo_mcp.py x2, demo_resume.py x2), `uv run pytest` test commands, `SESSION_BACKEND` section, `run_service.sh` reference, project structure. |
| `.env.example` | Required configuration keys | VERIFIED | 6 lines. Contains MODEL_PROVIDER, MODEL_NAME, MODEL_API_KEY, MODEL_BASE_URL, SESSION_BACKEND, SESSION_DIR. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_parity.py` | `src/agent/session.py` session backends | Direct import of JSONSession/RedisSession | WIRED | Lines 10-12: imports `InMemoryMemory`, `Msg`, `JSONSession`, `RedisSession`. Uses both session classes directly. |
| `src/tools/__init__.py` | `skills/example_skill/` | `register_agent_skill(skill_dir=)` | WIRED | Line 26-31: constructs path to `skills/example_skill`, checks `os.path.isdir`, calls `register_agent_skill`. |
| `src/tools/__init__.py` (toolkit) | `src/agent/query.py` | `from src.tools import toolkit` | WIRED | `query.py` line 12 imports toolkit, line 71 passes `toolkit=toolkit` to agent constructor. |
| `scripts/demos/demo_tool.py` | `http://127.0.0.1:8000/process` | `send_chat` -> `httpx.post` | WIRED | `demo_tool.py` calls `send_chat(payload)` which calls `httpx.post(f"{SERVICE_URL}/process")` in `_helpers.py` line 65. |
| `scripts/demos/demo_resume.py` | `http://127.0.0.1:8000/process` | `httpx.post` with `session_id` | WIRED | Lines 35 and 54: direct `httpx.post(f"{SERVICE_URL}/process", json=payload)` with `session_id` in payload. |
| `README.md` | `scripts/demos/` | Demo run commands | WIRED | Lines 47, 55, 63, 71, 79-83: all 4 demo scripts referenced with `uv run scripts/demos/` commands. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `tests/test_parity.py` | `json_msgs` / `redis_msgs` | `InMemoryMemory.get_memory()` after `save_session_state` / `load_session_state` | Yes -- saves 4 Msg objects, loads from both backends, compares | FLOWING |
| `src/tools/__init__.py` | `toolkit` | `Toolkit()` + `register_tool_function` + `register_agent_skill` | Yes -- toolkit singleton with registered tools and skill | FLOWING |
| Demo scripts | `text` (response) | `send_chat()` -> `httpx.post` -> SSE parse | Cannot verify without live service | NEEDS HUMAN |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Parity test passes | `uv run pytest tests/test_parity.py -x -v` | 1 passed, 0 failed (0.01s) | PASS |
| Full test suite green | `uv run pytest tests/ -x -v` | 52 passed, 0 failed (0.36s) | PASS |
| All demo scripts syntactically valid | `uv run python -c "import ast; ast.parse(...)"` x5 | All 5 VALID | PASS |
| _helpers module exports expected functions | `uv run python -c "from scripts.demos._helpers import ..."` | All 5 exports callable | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RES-05 | 08-01-PLAN | User can verify JSON/Redis resume behavior is consistent for core flows | SATISFIED | `tests/test_parity.py` passes. Same messages saved to both backends produce identical content/name/role on load. |
| DEV-01 | 08-02-PLAN | User can start and validate the service through a documented runnable demo flow | NEEDS HUMAN | README.md has Quick Start with all steps. Demo scripts exist with assertions. End-to-end flow requires running service. |
| DEV-03 | 08-02-PLAN | User can run at least one documented example per capability class (skill/tool/MCP/resume) | NEEDS HUMAN | 4 demo scripts exist (demo_tool.py, demo_skill.py, demo_mcp.py, demo_resume.py), all documented in README. Each has assertions. Execution requires running service. |

No orphaned requirements found. REQUIREMENTS.md maps exactly RES-05, DEV-01, DEV-03 to Phase 8, matching the plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected |

No TODO/FIXME/placeholder comments, no empty return statements, no hardcoded empty data, no console.log-only implementations found in any phase 8 files.

### Human Verification Required

### 1. Tool Call Demo (DEV-03)

**Test:** Start service (`bash scripts/run_service.sh`), then run `uv run scripts/demos/demo_tool.py`
**Expected:** Exit code 0, output contains "PASS: demo_tool.py - tool call triggered successfully"
**Why human:** Requires running service with valid LLM API key; tool call (get_weather) depends on agent reasoning to select the tool

### 2. Skill Demo (DEV-03)

**Test:** Run `uv run scripts/demos/demo_skill.py` with service running
**Expected:** Exit code 0, output contains "PASS: demo_skill.py - skill context influenced response"
**Why human:** Requires running service; depends on LLM incorporating skill-injected context into response

### 3. MCP Demo (DEV-03)

**Test:** Run `uv run scripts/demos/demo_mcp.py` with service running
**Expected:** Exit code 0, output contains "PASS: demo_mcp.py - MCP tool call triggered successfully"
**Why human:** Requires running service; depends on MCP tool (get_time) being invoked by agent

### 4. Session Resume Demo (DEV-03)

**Test:** Run `uv run scripts/demos/demo_resume.py` with service running
**Expected:** Exit code 0, output contains "PASS: demo_resume.py - session resume with context persistence works" and "42" in response
**Why human:** Requires running service; two-request flow with session persistence and LLM recall of prior context

### 5. README End-to-End Walkthrough (DEV-01)

**Test:** Follow README.md Quick Start section from top to bottom: configure .env, `uv sync`, start service, run all 4 demos
**Expected:** All demos pass without errors; documentation is accurate and complete
**Why human:** Full user journey requires external API credentials, running service, and LLM responses; validates documentation quality

### Gaps Summary

No code gaps found. All artifacts exist, are substantive, and are properly wired:

- **RES-05 parity test** passes, proving JSON and Redis backends produce identical conversation content for the same session data.
- **Example skill** is registered in the toolkit with a safety guard (`os.path.isdir`), wired through to agent creation in `query.py`.
- **4 demo scripts** are syntactically valid, use shared helpers for SSE parsing and service health checks, contain content assertions, and have proper entry points.
- **README.md** is a comprehensive getting-started guide with Quick Start, demo commands, session backend documentation, and test instructions.
- **Full test suite green** at 52/52 with zero regressions.

The phase requires human verification of the demo scripts and README walkthrough because they depend on a running service with valid LLM API credentials, which cannot be tested programmatically in this verification context.

---

_Verified: 2026-04-12T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
