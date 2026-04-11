---
phase: 6
slug: json-session-persistence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_session.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_session.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | RES-01 | T-6-01 | session_id validated as UUID format before file I/O | unit | `uv run pytest tests/test_session.py::test_session_persists_to_json -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | RES-03 | — | N/A | unit | `uv run pytest tests/test_session.py::test_session_resume_has_prior_context -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | D-05/D-12 | — | N/A | unit | `uv run pytest tests/test_session.py::test_no_session_id_backward_compatible -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | RES-01, RES-03 | T-6-01 | Path traversal blocked by session_id validation | integration | `uv run pytest tests/test_session.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_session.py` — stubs for RES-01, RES-03, backward compatibility
- [ ] Framework install: none needed — pytest already installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
