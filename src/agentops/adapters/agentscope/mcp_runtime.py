"""AgentScope MCP client lifecycle helpers."""

from __future__ import annotations

import logging

from agentscope.mcp import HttpStatefulClient, StatefulClientBase, StdIOStatefulClient
from agentscope.tool import Toolkit

from ...capabilities.models import (
    HttpMCPServerConfig,
    MCPServerConfig,
    MCPServerSummary,
    StdioMCPServerConfig,
)

logger = logging.getLogger(__name__)


class MCPClientInitializationError(RuntimeError):
    """Raised when MCP client initialization cannot complete."""


class MCPClientManager:
    """Connect and register MCP clients for a runtime-owned toolkit."""

    async def connect_all(
        self,
        toolkit: Toolkit,
        configs: list[MCPServerConfig],
    ) -> tuple[list[StatefulClientBase], list[MCPServerSummary]]:
        """Connect configured MCP clients and register them on the toolkit."""
        clients: list[StatefulClientBase] = []
        summaries: list[MCPServerSummary] = []
        current_summary: MCPServerSummary | None = None

        try:
            for config in configs:
                current_summary = summarize_mcp_server(config)
                client = create_mcp_client(config)
                await client.connect()
                await toolkit.register_mcp_client(
                    client,
                    group_name="basic",
                    namesake_strategy="raise",
                )
                clients.append(client)
                summaries.append(current_summary)
        except Exception as exc:
            await close_mcp_clients(clients)
            detail = format_initialization_error(current_summary)
            raise MCPClientInitializationError(detail) from exc

        return clients, summaries


def summarize_mcp_server(mcp_server: MCPServerConfig) -> MCPServerSummary:
    """Build a normalized summary for the configured MCP server."""
    if isinstance(mcp_server, StdioMCPServerConfig):
        return MCPServerSummary(name=mcp_server.name, type="stdio")
    return MCPServerSummary(
        name=mcp_server.name,
        type="http",
        transport=mcp_server.transport,
    )


def create_mcp_client(mcp_server: MCPServerConfig) -> StatefulClientBase:
    """Instantiate the appropriate stateful MCP client for the server config."""
    if isinstance(mcp_server, StdioMCPServerConfig):
        return StdIOStatefulClient(
            name=mcp_server.name,
            command=mcp_server.command,
            args=mcp_server.args,
            env=mcp_server.env,
            cwd=mcp_server.cwd,
        )

    if isinstance(mcp_server, HttpMCPServerConfig):
        return HttpStatefulClient(
            name=mcp_server.name,
            transport=mcp_server.transport,
            url=mcp_server.url,
            headers=mcp_server.headers,
            timeout=mcp_server.timeout,
            sse_read_timeout=mcp_server.sse_read_timeout,
        )

    raise MCPClientInitializationError("Unsupported MCP server configuration.")


def format_initialization_error(summary: MCPServerSummary | None) -> str:
    """Return a redacted initialization error message."""
    if summary is None:
        return "Failed to initialize one or more MCP servers."
    if summary.transport:
        return (
            f"Failed to initialize MCP server '{summary.name}' "
            f"({summary.type}/{summary.transport})."
        )
    return f"Failed to initialize MCP server '{summary.name}' ({summary.type})."


async def close_mcp_clients(mcp_clients: list[StatefulClientBase]) -> None:
    """Close MCP clients in reverse order, ignoring cleanup errors."""
    for client in reversed(mcp_clients):
        try:
            await client.close(ignore_errors=True)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Error closing initialized MCP client %s: %s", client.name, exc)
