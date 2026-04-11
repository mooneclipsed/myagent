---
phase: 03
slug: request-scoped-agent-stateless-runtime
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | CORE-02 | — | N/A | unit | `uv run pytest tests/test_agent_config.py::test_config_override -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | CORE-02 | — | N/A | unit | `uv run pytest tests/test_agent_config.py::test_config_fallback -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | CORE-02 | — | N/A | unit | `uv run pytest tests/test_agent_config.py::test_partial_override -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | CORE-03 | T-03-01 | api_key not logged | unit | `uv run pytest tests/test_agent_config.py::test_config_trace_logging -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | CORE-03 | — | N/A | unit | `uv run pytest tests/test_agent_config.py::test_instance_isolation -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | CORE-02/CORE-03 | — | N/A | regression | `uv run pytest tests/test_chat_stream.py -x` | ✅ | ⬜ pending |
| 03-02-02 | 02 | 1 | CORE-02/CORE-03 | — | N/A | regression | `uv run pytest tests/test_settings.py tests/test_startup.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_agent_config.py` — stubs for CORE-02 and CORE-03 config override/fallback/isolation/logging tests
- [ ] `scripts/verify_phase3.sh` — follows established pattern from verify_phase2.sh
- [ ] No new framework install needed — pytest already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end request with real LLM API and custom config | CORE-02 | Requires valid API credentials and running server | `bash scripts/run_service.sh` then `curl -N -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"input":[{"role":"user","content":[{"type":"text","text":"Hello"}]}], "agent_config":{"model_name":"gpt-4o"}}'` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
