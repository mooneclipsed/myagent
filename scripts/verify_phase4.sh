#!/usr/bin/env bash
set -euo pipefail

echo "=== Phase 4: Capability Invocation Tracing Verification ==="

echo "--- Step 1: Dependency sync ---"
uv sync

echo "--- Step 2: Run full test suite ---"
uv run pytest tests/ -x -q

echo "--- Step 3: Service boot check (with MCP client) ---"
uv run python -c "
import os, subprocess, time, sys
env = {**os.environ,
    'MODEL_PROVIDER': 'phase4-smoke-provider',
    'MODEL_NAME': 'phase4-smoke-model',
    'MODEL_API_KEY': 'phase4-smoke-key',
    'MODEL_BASE_URL': 'http://127.0.0.1:9999'}
p = subprocess.Popen(
    ['uv', 'run', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', '8014'],
    env=env)
time.sleep(4)
running = (p.poll() is None)
if running:
    p.terminate()
    p.wait(timeout=5)
sys.exit(0 if running else 1)
"

echo "--- Step 4: Module content validation ---"
grep -q 'toolkit = Toolkit()' src/tools/__init__.py && echo "OK: toolkit singleton"
grep -q 'def get_weather' src/tools/examples.py && echo "OK: get_weather tool"
grep -q 'def calculate' src/tools/examples.py && echo "OK: calculate tool"
grep -q 'Server("example-mcp")' src/mcp/server.py && echo "OK: MCP server"
grep -q 'register_mcp_client' src/app/lifespan.py && echo "OK: MCP registration in lifespan"
grep -q 'toolkit=toolkit' src/agent/query.py && echo "OK: toolkit passed to ReActAgent"

echo "--- Step 5: Phase traceability ---"
git log --oneline --decorate -n 20 | grep -E "phase.4|04-|docs\(04\)|feat\(04\)|test\(04\)" || echo "(no phase 4 commits yet -- this is expected during first execution)"

echo "=== Phase 4 verification complete ==="
