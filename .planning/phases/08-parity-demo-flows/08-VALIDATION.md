---
phase: 08
slug: parity-demo-flows
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_parity.py -x -v` |
| **Full suite command** | `uv run pytest tests/ -x -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_parity.py -x -v`
- **After every plan wave:** Run `uv run pytest tests/ -x -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | RES-05 | T-08-03 | `os.path.isdir()` guard on skill registration | unit | `grep -q "register_agent_skill" src/tools/__init__.py` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | RES-05 | T-08-01 | Hardcoded session_id in test scope | unit | `uv run pytest tests/test_parity.py -x -v` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | DEV-03 | T-08-04 | JSON parse with try/except in SSE | smoke | `test -f scripts/demos/demo_tool.py` + grep chain | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | DEV-01,DEV-03 | T-08-05 | `.env.example` placeholder values only | smoke | `grep -q "## Quick Start" README.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_parity.py` — stubs for RES-05 (Plan 01 Task 2)
- [x] `scripts/demos/` — directory with 4 demo script stubs (Plan 02 Task 1-2)
- [x] `skills/example_skill/SKILL.md` — skill definition file (Plan 01 Task 1)
- [x] `README.md` — update with getting-started guide structure (Plan 02 Task 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Demo scripts require live service + .env | DEV-01 | Service must be running with valid API key | Start service, run each demo script, verify output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
