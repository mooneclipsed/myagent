#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 2: Streaming Chat Contract Verification ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Run full test suite ---"
uv run pytest tests/ -x -q

echo "--- Step 3: Streaming endpoint boot check ---"
uv run python -c "
import os, subprocess, time, sys
env = {**os.environ,
    'MODEL_PROVIDER': 'phase2-smoke-provider',
    'MODEL_NAME': 'phase2-smoke-model',
    'MODEL_API_KEY': 'phase2-smoke-key',
    'MODEL_BASE_URL': 'http://127.0.0.1:9999'}
p = subprocess.Popen(
    ['uv', 'run', 'uvicorn', 'agentops.main:app', '--host', '127.0.0.1', '--port', '8012'],
    env=env)
time.sleep(3)
running = (p.poll() is None)
if running:
    p.terminate()
    p.wait(timeout=5)
sys.exit(0 if running else 1)
"

echo "--- Step 4: Verify /chat endpoint registered ---"
uv run python -c "
from agentops.main import app
routes = [r.path for r in app.routes]
assert '/chat' in routes, f'/chat not in {routes}'
print('PASS: /chat endpoint is registered')
"

echo "--- Step 5: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "phase.2|02-streaming|docs\(02\)|feat\(02\)|test\(02\)" || echo "(no phase 2 commits yet -- this is expected during first execution)"

echo "=== Phase 2 verification complete ==="
