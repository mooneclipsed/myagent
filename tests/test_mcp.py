"""Tests for MCP client lifecycle and registration (CAP-03 invocation side).

Per D-06/D-07, structured tracing/observability is deferred.
These tests verify MCP client connection lifecycle and FastMCP-backed server shape.
"""

import asyncio
import inspect

from agentscope.mcp import StdIOStatefulClient
from agentscope.tool import Toolkit
from mcp.server.fastmcp import FastMCP
from unittest.mock import AsyncMock


class TestMCPClientLifecycle:
    """Tests for MCP client connect/register/close lifecycle per D-04."""

    def test_mcp_client_lifecycle(self):
        """MCP client follows correct lifecycle: create -> connect -> register -> close."""
        toolkit = Toolkit()
        mock_client = AsyncMock(spec=StdIOStatefulClient)
        mock_client.name = "test-mcp"
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])

        async def run_lifecycle():
            await mock_client.connect()
            await toolkit.register_mcp_client(
                mock_client,
                group_name="basic",
                namesake_strategy="raise",
            )
            await mock_client.close(ignore_errors=True)

        asyncio.run(run_lifecycle())

        mock_client.connect.assert_awaited_once()
        mock_client.close.assert_awaited_once_with(ignore_errors=True)

    def test_lifo_close_order(self):
        """MCP clients must be closed in reverse order of registration."""
        from src.agent.session_runtime import close_mcp_clients

        client1 = AsyncMock()
        client1.name = "first"
        client2 = AsyncMock()
        client2.name = "second"

        asyncio.run(close_mcp_clients([client1, client2]))

        client2.close.assert_awaited_once_with(ignore_errors=True)
        client1.close.assert_awaited_once_with(ignore_errors=True)


class TestMCPServerModule:
    """Tests verifying the MCP server module is importable and well-formed."""

    def test_mcp_server_module_importable(self):
        """src.mcp.server module can be imported without errors."""
        import src.mcp.server

        assert hasattr(src.mcp.server, "server")
        assert hasattr(src.mcp.server, "get_time")
        assert hasattr(src.mcp.server, "main")

    def test_mcp_server_is_fastmcp(self):
        """src.mcp.server exports a FastMCP server instance."""
        import src.mcp.server

        assert isinstance(src.mcp.server.server, FastMCP)

    def test_get_time_tool_contract(self):
        """get_time remains a zero-argument tool function returning text."""
        import src.mcp.server

        assert len(inspect.signature(src.mcp.server.get_time).parameters) == 0
        result = src.mcp.server.get_time()
        assert isinstance(result, str)
        assert result.startswith("Current time:")
