"""Tests for runtime manager assembly."""

import asyncio
from pathlib import Path

import pytest

from agentops.api.schemas import RuntimeInitRequest
from agentops.frameworks.registry import UnknownFrameworkError
from agentops.orchestration.runtime_factory import create_runtime_manager


def test_create_runtime_manager_rejects_unknown_framework() -> None:
    with pytest.raises(UnknownFrameworkError, match="Framework 'missing' does not exist."):
        create_runtime_manager(framework="missing")


def test_create_runtime_manager_uses_agentscope_builder(tmp_path: Path) -> None:
    manager = create_runtime_manager(workspace_root=tmp_path)

    result = asyncio.run(manager.initialize(RuntimeInitRequest(runtime_id="runtime-1")))

    assert result.framework == "agentscope"
    assert result.status == "ready"
    assert result.workspace.runtime_path == str(tmp_path / "runtime-1")
    assert manager.get_active_profile().agent_spec.metadata["adapter"] == "agentscope_v2"
