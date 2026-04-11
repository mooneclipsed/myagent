# Quick Task 260411-q3a: Fix Phase 2 UAT Gaps

**Two UAT-diagnosed bugs fixed:**

1. **ReActAgent formatter (blocker)** — Added `OpenAIChatFormatter()` to `ReActAgent` constructor in `src/agent/query.py`. The agentscope `ReActAgent.__init__` requires a `formatter` parameter that was missing, causing all real streaming calls to fail with TypeError.

2. **Test regression (major)** — Added `.env` file isolation to `tests/conftest.py` `configured_env` fixture. The `Settings` class reads from both env vars and `.env` file; `monkeypatch.delenv` only removed the env var, but `.env` still provided the value. Fix: set `env_file: None` in `model_config` during tests.

**Commits:** `6cecaac`
**Test result:** 17/17 pass
