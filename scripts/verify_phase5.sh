#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 5: Context Continuity Validation ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Run Phase 5 context tests ---"
uv run pytest tests/test_context.py -x -v

echo "--- Step 3: Run full test suite ---"
uv run pytest tests/ -x -q

echo "--- Step 4: Verify test file exists ---"
test -f tests/test_context.py && echo "OK: tests/test_context.py exists"

echo "--- Step 5: Verify multi_turn_payload fixture ---"
grep -q "multi_turn_payload" tests/conftest.py && echo "OK: multi_turn_payload fixture found"

echo "--- Step 6: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "phase.5|05-|docs\(05\)|feat\(05\)|test\(05\)" || echo "(no phase 5 commits yet -- this is expected during first execution)"

echo "=== Phase 5 verification complete ==="
