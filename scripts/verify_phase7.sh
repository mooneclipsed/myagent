#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 7: Redis Session Persistence ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Verify fakeredis available ---"
uv run python -c "import fakeredis.aioredis; print('OK: fakeredis.aioredis importable')"

echo "--- Step 3: Source checks ---"
grep -q "session_backend" src/agentops/config/settings.py && echo "OK: session_backend field in settings"
grep -q "RedisSession" src/agentops/sessions/backend.py && echo "OK: RedisSession in backend.py"
grep -q "reset_session_backend" src/agentops/sessions/backend.py && echo "OK: reset_session_backend helper exists"
grep -q "ping()" src/agentops/api/lifecycle.py && echo "OK: Redis health check present"
grep -q "close()" src/agentops/api/lifecycle.py && echo "OK: shutdown close present"
grep -q "fakeredis" pyproject.toml && echo "OK: fakeredis dev dependency"

echo "--- Step 4: Run Phase 7 session tests ---"
uv run pytest tests/test_session.py -x -v

echo "--- Step 5: Full regression ---"
uv run pytest tests/ --ignore=tests/test_context.py -x -q

echo "--- Step 6: query.py untouched ---"
count=$(grep -c "RedisSession" src/agentops/application/chat_service.py || true)
if [[ "$count" -eq 0 ]]; then
    echo "OK: chat_service.py has zero RedisSession references"
else
    echo "FAIL: chat_service.py has $count RedisSession references (should be 0)"
    exit 1
fi

echo "--- Step 7: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "07-|redis|Redis" || echo "(no phase 7 commits found)"

echo "=== Phase 7 verification complete ==="
