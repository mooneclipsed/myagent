#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 6: JSON Session Persistence ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Run Phase 6 session tests ---"
uv run pytest tests/test_session.py -x -v

echo "--- Step 3: Run full test suite ---"
uv run pytest tests/ -x -q --ignore=tests/test_context.py

echo "--- Step 4: Verify session module exists ---"
test -f src/agent/session.py && echo "OK: src/agent/session.py exists"

echo "--- Step 5: Verify SESSION_DIR in settings ---"
grep -q "SESSION_DIR" src/core/settings.py && echo "OK: SESSION_DIR field found in settings"

echo "--- Step 6: Verify session load/save in query handler ---"
grep -q "load_session_state" src/agent/query.py && echo "OK: load_session_state wired"
grep -q "save_session_state" src/agent/query.py && echo "OK: save_session_state wired"

echo "--- Step 7: Verify session dir creation in lifespan ---"
grep -q "makedirs" src/app/lifespan.py && echo "OK: session directory creation at startup"

echo "--- Step 8: Verify test file exists ---"
test -f tests/test_session.py && echo "OK: tests/test_session.py exists"

echo "--- Step 9: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "06-|session|Session" || echo "(no phase 6 commits found)"

echo "=== Phase 6 verification complete ==="
