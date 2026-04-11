"""FastAPI lifespan hook for startup validation and MCP client lifecycle."""

import logging
import os
from contextlib import asynccontextmanager

from agentscope.mcp import StdIOStatefulClient
from fastapi import FastAPI

from src.core.settings import get_settings
from src.tools import _mcp_clients, toolkit

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    # Existing: validate settings at startup (fail-fast)
    settings = get_settings()

    # Phase 6 D-09: Ensure session directory exists at startup
    session_dir = settings.SESSION_DIR
    os.makedirs(session_dir, exist_ok=True)
    logger.info("Session directory ready: %s", session_dir)

    # Phase 4 D-05: Connect local MCP server at startup
    mcp_client = StdIOStatefulClient(
        name="example-mcp",
        command="python",
        args=["-m", "src.mcp.server"],
    )
    await mcp_client.connect()
    await toolkit.register_mcp_client(
        mcp_client,
        group_name="basic",
        namesake_strategy="raise",
    )
    _mcp_clients.append(mcp_client)
    logger.info("MCP client connected and registered: example-mcp")

    yield

    # Shutdown: close MCP clients in LIFO order (framework requirement)
    for client in reversed(_mcp_clients):
        try:
            await client.close(ignore_errors=True)
        except Exception as e:
            logger.warning("Error closing MCP client %s: %s", client.name, e)
    _mcp_clients.clear()
    logger.info("All MCP clients closed")
