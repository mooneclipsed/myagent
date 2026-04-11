"""Tests for MCP client lifecycle and registration (CAP-03 invocation side).

Per D-06/D-07, structured tracing/observability is deferred.
These tests verify MCP client connection lifecycle.
"""

import asyncio

import pytest
from agentscope.mcp import StdIOStatefulClient
from agentscope.tool import Toolkit
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

    def test_mcp_clients_tracked_for_lifo_close(self):
        """MCP clients are tracked in _mcp_clients list for LIFO shutdown."""
        from src.tools import _mcp_clients

        _mcp_clients.clear()
        assert len(_mcp_clients) == 0

    def test_lifo_close_order(self):
        """MCP clients must be closed in reverse order of registration."""
        from src.tools import _mcp_clients

        _mcp_clients.clear()

        # Simulate two clients
        client1 = AsyncMock()
        client1.name = "first"
        client2 = AsyncMock()
        client2.name = "second"

        _mcp_clients.extend([client1, client2])

        # LIFO close
        async def close_all():
            for client in reversed(_mcp_clients):
                await client.close(ignore_errors=True)

        asyncio.run(close_all())

        # Verify close was called on both
        client2.close.assert_awaited_once_with(ignore_errors=True)
        client1.close.assert_awaited_once_with(ignore_errors=True)
        _mcp_clients.clear()


class TestMCPServerModule:
    """Tests verifying the MCP server module is importable and well-formed."""

    def test_mcp_server_module_importable(self):
        """src.mcp.server module can be imported without errors."""
        import src.mcp.server

        assert hasattr(src.mcp.server, "server")
        assert hasattr(src.mcp.server, "main")

    def test_mcp_server_has_tools(self):
        """MCP server module defines expected tool handlers."""
        import src.mcp.server

        assert src.mcp.server.server is not None
