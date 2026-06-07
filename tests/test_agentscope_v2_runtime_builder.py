"""Tests for AgentScope v2 runtime builder."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from agentops.api.schemas import RuntimeInitRequest
from agentops.frameworks.agentscope_v2.runtime import AgentScopeRuntimeBuilder
from agentops.orchestration.models import RuntimeProfile


class FakeMCPClient:
    """Minimal MCP client fake for runtime builder tests."""

    def __init__(self, name: str, *, fail_connect: bool = False) -> None:
        """Create a fake MCP client."""
        self.name = name
        self.is_stateful = True
        self.is_connected = False
        self.fail_connect = fail_connect
        self.close = AsyncMock()

    async def connect(self) -> None:
        """Mark the client as connected or fail."""
        if self.fail_connect:
            raise RuntimeError(f"{self.name} failed")
        self.is_connected = True


def _profile(runtime_id: str) -> RuntimeProfile:
    return RuntimeProfile(
        runtime_id=runtime_id,
        framework="agentscope",
        agent_spec={
            "model_config": {},
            "system_prompt": "prompt",
            "prompt_hash": "sha256:test",
        },
        workspace={"root": "/tmp", "runtime_path": f"/tmp/{runtime_id}"},
        storage={"type": "framework_memory"},
        trace={"enabled": False},
        status="ready",
    )


def test_runtime_builder_builds_resources_without_mcp(tmp_path: Path) -> None:
    builder = AgentScopeRuntimeBuilder()
    request = RuntimeInitRequest(runtime_id="runtime-1")

    with patch("agentops.frameworks.agentscope_v2.runtime.build_mcp_clients", return_value=[]):
        metadata = asyncio.run(builder.build(request, tmp_path))

    assert metadata["adapter"] == "agentscope_v2"
    assert metadata["mcp_clients"] == 0
    assert builder.get_resources("runtime-1") is not None

    asyncio.run(builder.close(_profile("runtime-1")))

    assert builder.get_resources("runtime-1") is None


def test_runtime_builder_connects_and_closes_mcp_clients(tmp_path: Path) -> None:
    builder = AgentScopeRuntimeBuilder()
    request = RuntimeInitRequest(runtime_id="runtime-1")
    mcp_clients = [FakeMCPClient("mcp-1")]

    with patch("agentops.frameworks.agentscope_v2.runtime.build_mcp_clients", return_value=mcp_clients):
        metadata = asyncio.run(builder.build(request, tmp_path))

    assert metadata["adapter"] == "agentscope_v2"
    assert metadata["mcp_clients"] == 1
    assert builder.get_resources("runtime-1") is not None

    asyncio.run(builder.close(_profile("runtime-1")))

    assert builder.get_resources("runtime-1") is None
    for client in mcp_clients:
        client.close.assert_awaited_once_with(ignore_errors=True)


def test_runtime_builder_closes_connected_clients_on_failure(tmp_path: Path) -> None:
    builder = AgentScopeRuntimeBuilder()
    connected = FakeMCPClient("connected")
    failing = FakeMCPClient("failing", fail_connect=True)
    request = RuntimeInitRequest(runtime_id="runtime-1")

    with patch("agentops.frameworks.agentscope_v2.runtime.build_mcp_clients", return_value=[connected, failing]):
        with pytest.raises(RuntimeError, match="failing failed"):
            asyncio.run(builder.build(request, tmp_path))

    connected.close.assert_awaited_once_with(ignore_errors=True)
    failing.close.assert_not_awaited()
    assert builder.get_resources("runtime-1") is None


def test_runtime_builder_closes_mcp_clients_in_lifo_order(tmp_path: Path) -> None:
    builder = AgentScopeRuntimeBuilder()
    request = RuntimeInitRequest(runtime_id="runtime-1")
    close_order: list[str] = []

    first = FakeMCPClient("first")
    second = FakeMCPClient("second")

    async def close_first(*, ignore_errors: bool = True) -> None:
        close_order.append("first")

    async def close_second(*, ignore_errors: bool = True) -> None:
        close_order.append("second")

    first.close = AsyncMock(side_effect=close_first)
    second.close = AsyncMock(side_effect=close_second)

    with patch("agentops.frameworks.agentscope_v2.runtime.build_mcp_clients", return_value=[first, second]):
        asyncio.run(builder.build(request, tmp_path))

    asyncio.run(builder.close(_profile("runtime-1")))

    assert close_order == ["second", "first"]
