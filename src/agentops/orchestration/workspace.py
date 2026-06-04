"""Workspace path helpers for runtime-scoped workspaces."""

from __future__ import annotations

import json
import os
import shutil
from json import JSONDecodeError
from pathlib import Path

DEFAULT_WORKSPACE_ROOT = ".agentops/workspaces"
WORKSPACE_MARKER = ".agentops_workspace.json"
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


def create_runtime_workspace(runtime_id: str, *, root: Path | str | None = None) -> Path:
    """Create an empty workspace directory for a runtime."""
    workspace_path = build_runtime_workspace_path(runtime_id, root=root)
    if workspace_path.exists():
        remove_runtime_workspace(runtime_id, root=root)
    workspace_path.mkdir(parents=True)
    _write_workspace_marker(workspace_path, runtime_id)
    return workspace_path


def remove_runtime_workspace(runtime_id: str, *, root: Path | str | None = None) -> None:
    """Remove a runtime workspace directory if it exists."""
    workspace_path = build_runtime_workspace_path(runtime_id, root=root)
    if not workspace_path.exists():
        return
    _validate_workspace_marker(workspace_path, runtime_id)
    shutil.rmtree(workspace_path)


def promote_runtime_workspace(
    staging_runtime_id: str,
    runtime_id: str,
    *,
    root: Path | str | None = None,
) -> Path:
    """Replace a runtime workspace with a prepared staging workspace."""
    staging_path = build_runtime_workspace_path(staging_runtime_id, root=root)
    runtime_path = build_runtime_workspace_path(runtime_id, root=root)
    _validate_workspace_marker(staging_path, staging_runtime_id)
    if runtime_path.exists():
        remove_runtime_workspace(runtime_id, root=root)
    _write_workspace_marker(staging_path, runtime_id)
    staging_path.rename(runtime_path)
    return runtime_path


def _write_workspace_marker(workspace_path: Path, runtime_id: str) -> None:
    marker_path = workspace_path / WORKSPACE_MARKER
    marker_path.write_text(
        json.dumps({"managed_by": "agentops", "runtime_id": runtime_id}, sort_keys=True),
        encoding="utf-8",
    )


def _validate_workspace_marker(workspace_path: Path, runtime_id: str) -> None:
    marker_path = workspace_path / WORKSPACE_MARKER
    if not marker_path.exists():
        raise ValueError(f"Workspace is not managed by AgentOps: {workspace_path}")

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(f"Workspace marker is invalid: {workspace_path}") from exc

    if marker != {"managed_by": "agentops", "runtime_id": runtime_id}:
        raise ValueError(f"Workspace marker does not match runtime_id: {workspace_path}")
