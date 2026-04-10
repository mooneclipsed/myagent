#!/usr/bin/env bash
set -euo pipefail

uv sync
uv run pytest tests/test_settings.py tests/test_startup.py -q -x
git log --oneline --decorate -n 20 | rg "phase 1|01-environment-workflow-baseline|docs\(01\)|feat\(01\)"
