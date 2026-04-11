#!/usr/bin/env bash
set -euo pipefail

uv sync
uv run pytest tests/test_settings.py tests/test_startup.py -q -x
uv run python -c "import os,subprocess,time; env={**os.environ,'MODEL_PROVIDER':'phase1-smoke-provider','MODEL_NAME':'phase1-smoke-model','MODEL_API_KEY':'phase1-smoke-key','MODEL_BASE_URL':'http://127.0.0.1:9999'}; p=subprocess.Popen(['uvicorn','src.main:app','--host','127.0.0.1','--port','8011'], env=env); time.sleep(2); running=(p.poll() is None); p.terminate() if running else None; p.wait(timeout=5) if running else None; raise SystemExit(0 if running else 1)"
if command -v rg >/dev/null 2>&1; then
    rg -n "^uv run uvicorn src\.main:app --host 127\.0\.0\.1 --port 8000$" scripts/run_service.sh
else
    grep -Fnx "uv run uvicorn src.main:app --host 127.0.0.1 --port 8000" scripts/run_service.sh
fi
git log --oneline --decorate -n 20 | grep -E "phase 1|01-environment-workflow-baseline|docs\(01\)|feat\(01\)"
