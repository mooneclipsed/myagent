"""AgentScope v2 runtime resource builder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentscope.mcp import MCPClient
from agentscope.tool import Toolkit

from agentops.api.schemas import RuntimeInitRequest
from agentops.orchestration.models import RuntimeProfile

from .adapter import build_mcp_clients, build_toolkit


@dataclass
class AgentScopeRuntimeResources:
    """Framework resources owned by one runtime."""

    toolkit: Toolkit
    mcp_clients: list[MCPClient]
    workspace_path: Path


class AgentScopeRuntimeBuilder:
    """Build and close AgentScope v2 runtime-level resources."""

    def __init__(self) -> None:
        """Create an AgentScope v2 runtime builder."""
        self._resources_by_runtime_id: dict[str, AgentScopeRuntimeResources] = {}

    async def build(self, request: RuntimeInitRequest, workspace_path: Path) -> dict[str, str | int]:
        """Build runtime resources and connect stateful MCP clients."""
        toolkit = build_toolkit(request, workspace_path)
        mcp_clients = build_mcp_clients(request)
        connected_clients = []
        try:
            for client in mcp_clients:
                await client.connect()
                connected_clients.append(client)

            if connected_clients:
                toolkit = Toolkit(
                    tools=toolkit.tool_groups[0].tools,
                    skills_or_loaders=toolkit.tool_groups[0].skills_or_loaders,
                    mcps=connected_clients,
                )

            self._resources_by_runtime_id[request.runtime_id] = AgentScopeRuntimeResources(
                toolkit=toolkit,
                mcp_clients=connected_clients,
                workspace_path=workspace_path,
            )
            return {
                "adapter": "agentscope_v2",
                "mcp_clients": len(connected_clients),
            }
        except Exception:
            await _close_mcp_clients(connected_clients)
            raise

    async def close(self, profile: RuntimeProfile) -> None:
        """Close AgentScope v2 runtime resources."""
        resources = self._resources_by_runtime_id.pop(profile.runtime_id, None)
        if resources is None:
            return
        await _close_mcp_clients(resources.mcp_clients)

    def get_resources(self, runtime_id: str) -> AgentScopeRuntimeResources | None:
        """Return runtime resources for tests and future execution wiring."""
        return self._resources_by_runtime_id.get(runtime_id)


async def _close_mcp_clients(clients: list[MCPClient]) -> None:
    for client in reversed(clients):
        await client.close(ignore_errors=True)
