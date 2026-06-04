"""Tests for refactor-v2 runtime manager."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agentops.api.schemas import RuntimeInitRequest
from agentops.frameworks.registry import UnknownFrameworkError
from agentops.orchestration.runtime_manager import (
    RuntimeManager,
    RuntimeManagerError,
)
from agentops.orchestration.models import RuntimeProfile
from agentops.orchestration.workspace import WORKSPACE_MARKER


class RecordingBuilder:
    """Runtime builder that records build and close calls."""

    def __init__(self, *, fail: bool = False) -> None:
        """Create a recording builder."""
        self.fail = fail
        self.built_paths: list[Path] = []
        self.closed_runtime_ids: list[str] = []

    async def build(self, request: RuntimeInitRequest, workspace_path: Path) -> dict[str, str]:
        """Record a build call and optionally fail."""
        self.built_paths.append(workspace_path)
        marker = workspace_path / "marker.txt"
        marker.write_text(request.runtime_id, encoding="utf-8")
        if self.fail:
            raise RuntimeError("builder failed")
        return {"builder": "recording"}

    async def close(self, profile: RuntimeProfile) -> None:
        """Record a close call."""
        self.closed_runtime_ids.append(profile.runtime_id)


def test_initialize_creates_runtime_workspace(tmp_path: Path) -> None:
    builder = RecordingBuilder()
    manager = RuntimeManager(workspace_root=tmp_path, builder=builder)

    result = asyncio.run(
        manager.initialize(
            RuntimeInitRequest(
                runtime_id="runtime-1",
                model_config={"model_name": "test-model"},
            ),
        ),
    )

    assert result.status == "ready"
    assert result.framework == "agentscope"
    assert Path(result.workspace.runtime_path).exists()
    assert Path(result.workspace.runtime_path, "marker.txt").read_text(encoding="utf-8") == "runtime-1"
    workspace_marker = json.loads(Path(result.workspace.runtime_path, WORKSPACE_MARKER).read_text(encoding="utf-8"))
    assert workspace_marker == {"managed_by": "agentops", "runtime_id": "runtime-1"}
    assert manager.get_active_profile().runtime_id == "runtime-1"


def test_repeated_initialize_replaces_active_runtime(tmp_path: Path) -> None:
    builder = RecordingBuilder()
    manager = RuntimeManager(workspace_root=tmp_path, builder=builder)

    asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))
    asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-2")))

    assert manager.get_active_profile().runtime_id == "runtime-2"
    assert builder.closed_runtime_ids == ["runtime-1"]
    assert not Path(tmp_path, "runtime-1").exists()
    assert Path(tmp_path, "runtime-2").exists()


def test_failed_initialize_does_not_publish_runtime(tmp_path: Path) -> None:
    builder = RecordingBuilder(fail=True)
    manager = RuntimeManager(workspace_root=tmp_path, builder=builder)

    with pytest.raises(RuntimeManagerError, match="builder failed"):
        asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))

    assert manager.get_active_profile() is None
    assert not Path(tmp_path, "runtime-1").exists()
    assert not Path(tmp_path, ".runtime-1.staging").exists()


def test_initialize_does_not_overwrite_unmanaged_workspace(tmp_path: Path) -> None:
    builder = RecordingBuilder()
    manager = RuntimeManager(workspace_root=tmp_path, builder=builder)
    unmanaged_workspace = tmp_path / "runtime-1"
    unmanaged_workspace.mkdir()
    (unmanaged_workspace / "user-file.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeManagerError, match="not managed by AgentOps"):
        asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))

    assert manager.get_active_profile() is None
    assert (unmanaged_workspace / "user-file.txt").exists()


def test_reinitialize_same_runtime_id_closes_previous_resources(tmp_path: Path) -> None:
    builder = RecordingBuilder()
    manager = RuntimeManager(workspace_root=tmp_path, builder=builder)

    asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))
    asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))

    assert manager.get_active_profile().runtime_id == "runtime-1"
    assert builder.closed_runtime_ids == ["runtime-1"]
    assert Path(tmp_path, "runtime-1").exists()


def test_close_active_runtime_removes_workspace(tmp_path: Path) -> None:
    builder = RecordingBuilder()
    manager = RuntimeManager(workspace_root=tmp_path, builder=builder)

    asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))
    asyncio.run(manager.close_active_runtime())

    assert manager.get_active_profile() is None
    assert builder.closed_runtime_ids == ["runtime-1"]
    assert not Path(tmp_path, "runtime-1").exists()


def test_unknown_framework_uses_registry_error(tmp_path: Path) -> None:
    manager = RuntimeManager(workspace_root=tmp_path)

    with pytest.raises(UnknownFrameworkError, match="Framework 'missing' does not exist."):
        asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1", framework="missing")))
