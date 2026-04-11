#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 3: Request-Scoped Agent & Stateless Runtime Verification ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Run full test suite ---"
uv run pytest tests/ -x -q

echo "--- Step 3: Streaming endpoint boot check ---"
uv run python -c "
import os, subprocess, time, sys
env = {**os.environ,
    'MODEL_PROVIDER': 'phase3-smoke-provider',
    'MODEL_NAME': 'phase3-smoke-model',
    'MODEL_API_KEY': 'phase3-smoke-key',
    'MODEL_BASE_URL': 'http://127.0.0.1:9999'}
p = subprocess.Popen(
    ['uv', 'run', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', '8013'],
    env=env)
time.sleep(3)
running = (p.poll() is None)
if running:
    p.terminate()
    p.wait(timeout=5)
sys.exit(0 if running else 1)
"

echo "--- Step 4: Verify config resolution module ---"
uv run python -c "
from src.core.config import AgentConfig, resolve_effective_config
cfg = AgentConfig(model_name='test-model')
assert cfg.model_name == 'test-model'
assert cfg.api_key is None
result = resolve_effective_config(None)
assert 'model_name' in result
assert 'api_key' in result
assert 'base_url' in result
from pydantic import ValidationError
try:
    AgentConfig(model_name='x', unknown='bad')
    raise AssertionError('Should have raised ValidationError')
except ValidationError:
    pass
print('PASS: config resolution module verified')
"

echo "--- Step 5: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "phase.3|03-request|docs\(03\)|feat\(03\)|test\(03\)" || echo "(no phase 3 commits yet -- this is expected during first execution)"

echo "=== Phase 3 verification complete ==="
