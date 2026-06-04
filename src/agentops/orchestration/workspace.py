"""Workspace path helpers for runtime-scoped workspaces."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_WORKSPACE_ROOT = "/app/workspaces"
WORKSPACE_ROOT_ENV = "AGENTOPS_WORKSPACE_ROOT"


def get_workspace_root() -> Path:
    """Return the configured workspace root."""
    return Path(os.getenv(WORKSPACE_ROOT_ENV, DEFAULT_WORKSPACE_ROOT))


def build_runtime_workspace_path(runtime_id: str, *, root: Path | str | None = None) -> Path:
    """Build the workspace path for a runtime id."""
    if not runtime_id or "/" in runtime_id or "\\" in runtime_id or runtime_id.strip() != runtime_id:
        raise ValueError("Invalid runtime_id for workspace path.")
    base = Path(root) if root is not None else get_workspace_root()
    return base / runtime_id
