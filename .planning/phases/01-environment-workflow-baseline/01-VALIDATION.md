---
phase: 1
slug: environment-workflow-baseline
status: active
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_settings.py tests/test_startup.py -q -x` |
| **Full suite command** | `uv run pytest tests/test_settings.py tests/test_startup.py -q -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_settings.py tests/test_startup.py -q -x`
- **After every plan wave:** Run `uv run pytest tests/test_settings.py tests/test_startup.py -q -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CORE-04 | T-1-02, T-1-04, T-1-05 | Required env vars are validated at startup and service fails fast on missing keys | unit/integration | `uv run pytest tests/test_settings.py tests/test_startup.py -q -x` | ✅ | ✅ green |
| 1-01-02 | 01 | 1 | CORE-05 | — | `uv` is the canonical dependency and runtime command path | smoke | `uv sync && uv run pytest tests/test_settings.py tests/test_startup.py -q -x` | ✅ | ✅ green |
| 1-01-03 | 01 | 1 | DEV-02 | T-1-03 | Git history shows phase-aligned commit checkpoints | scripted | `git log --oneline --decorate -n 20 | rg "phase 1|01-environment-workflow-baseline|docs\(01\)|feat\(01\)"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_settings.py` — startup env contract tests for CORE-04
- [x] `pyproject.toml` pytest config — baseline test invocation settings
- [x] Canonical service entrypoint and `uv run` command mapping for CORE-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Commit milestone visibility | DEV-02 | Scripted check ensures recent history contains phase-aligned tags | Run `git log --oneline --decorate -n 20 | rg "phase 1|01-environment-workflow-baseline|docs\(01\)|feat\(01\)"` and confirm at least one match |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** phase 1 task automation validated