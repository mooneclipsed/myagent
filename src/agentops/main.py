"""AgentOps FastAPI entrypoint for the refactor-v2 API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from .api.v2 import V2RuntimeApiService, register_v2_routes
from .branding import build_startup_banner
from .config.settings import get_settings

logger = logging.getLogger(__name__)
runtime_api_service = V2RuntimeApiService()


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    print(build_startup_banner())
    settings = get_settings()
    if settings.session_backend == "json":
        os.makedirs(settings.session_dir, exist_ok=True)
        logger.info("Session directory ready: %s", settings.session_dir)
    yield
    await runtime_api_service.close()
    logger.info("Application lifespan cleanup complete")


class AgentOpsApp(FastAPI):
    """FastAPI app with the legacy app.run convenience method."""

    def run(self, *, host: str, port: int) -> None:
        uvicorn.run(self, host=host, port=port)


app = AgentOpsApp(
    title="agentops",
    description="AgentScope v2 Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)
register_v2_routes(app, service=runtime_api_service)


if __name__ == "__main__":
    settings = get_settings()
    app.run(host="127.0.0.1", port=settings.port)
