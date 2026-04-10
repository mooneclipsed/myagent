---
phase: 1
slug: environment-workflow-baseline
status: draft
nyquist_compliant: false
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
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `uv run pytest -q -x` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q -x`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CORE-04 | T-1-01 | Required env vars are validated at startup and service fails fast on missing keys | unit/integration | `uv run pytest tests/test_settings.py::test_required_env_keys_fail_fast -q -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | CORE-05 | — | `uv` is the canonical dependency and runtime command path | smoke | `uv sync && uv run <entry-command>` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DEV-02 | — | Git history shows phase-aligned commit checkpoints | manual/scripted | `git log --oneline --decorate` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_settings.py` — startup env contract tests for CORE-04
- [ ] `pyproject.toml` pytest config — baseline test invocation settings
- [ ] Canonical service entrypoint and `uv run` command mapping for CORE-05

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Commit milestone visibility | DEV-02 | Human review of commit semantic alignment | Run `git log --oneline --decorate` and confirm Phase 1 checkpoints are explicit |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending