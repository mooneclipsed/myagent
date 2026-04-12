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

    # Phase 6 D-09 / Phase 7: Ensure session directory exists only for JSON backend
    if settings.SESSION_BACKEND == "json":
        session_dir = settings.SESSION_DIR
        os.makedirs(session_dir, exist_ok=True)
        logger.info("Session directory ready: %s", session_dir)

    # Phase 7 D-09: Redis health check when using Redis session backend
    if settings.SESSION_BACKEND == "redis":
        from src.agent.session import get_session_backend

        backend = get_session_backend()
        redis_client = backend.get_client()
        try:
            await redis_client.ping()
            logger.info("Redis health check passed")
        except Exception as e:
            raise RuntimeError(
                f"Redis health check failed: {e}. "
                f"Ensure Redis is running at {settings.REDIS_HOST}:{settings.REDIS_PORT}"
            ) from e

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

    # Phase 7: Close Redis session backend if active
    from src.agent.session import _session_backend, reset_session_backend

    if _session_backend is not None and hasattr(_session_backend, "close"):
        try:
            await _session_backend.close()
            logger.info("Redis session backend closed")
        except Exception as e:
            logger.warning("Error closing session backend: %s", e)
        reset_session_backend()

    # Shutdown: close MCP clients in LIFO order (framework requirement)
    for client in reversed(_mcp_clients):
        try:
            await client.close(ignore_errors=True)
        except Exception as e:
            logger.warning("Error closing MCP client %s: %s", client.name, e)
    _mcp_clients.clear()
    logger.info("All MCP clients closed")
