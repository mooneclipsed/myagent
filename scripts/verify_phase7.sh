#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 7: Redis Session Persistence ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Verify fakeredis available ---"
uv run python -c "import fakeredis.aioredis; print('OK: fakeredis.aioredis importable')"

echo "--- Step 3: Source checks ---"
grep -q "SESSION_BACKEND" src/core/settings.py && echo "OK: SESSION_BACKEND field in settings"
grep -q "RedisSession" src/agent/session.py && echo "OK: RedisSession in session.py"
grep -q "reset_session_backend" src/agent/session.py && echo "OK: reset_session_backend helper exists"
grep -q "ping()" src/app/lifespan.py && echo "OK: Redis health check present"
grep -q "close()" src/app/lifespan.py && echo "OK: shutdown close present"
grep -q "fakeredis" pyproject.toml && echo "OK: fakeredis dev dependency"

echo "--- Step 4: Run Phase 7 session tests ---"
uv run pytest tests/test_session.py -x -v

echo "--- Step 5: Full regression ---"
uv run pytest tests/ --ignore=tests/test_context.py -x -q

echo "--- Step 6: query.py untouched ---"
count=$(grep -c "RedisSession" src/agent/query.py || true)
if [[ "$count" -eq 0 ]]; then
    echo "OK: query.py has zero RedisSession references (untouched)"
else
    echo "FAIL: query.py has $count RedisSession references (should be 0)"
    exit 1
fi

echo "--- Step 7: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "07-|redis|Redis" || echo "(no phase 7 commits found)"

echo "=== Phase 7 verification complete ==="
