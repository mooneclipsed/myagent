"""FastAPI application lifespan hook for startup validation and runtime cleanup."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..branding import build_startup_banner
from ..config.settings import get_settings
from .v2 import RUNTIME_SERVICE_STATE_KEY
logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    print(build_startup_banner())

    settings = get_settings()

    if settings.session_backend == "json":
        session_dir = settings.session_dir
        os.makedirs(session_dir, exist_ok=True)
        logger.info("Session directory ready: %s", session_dir)

    if settings.session_backend == "redis":
        from ..sessions.backend import get_session_backend

        backend = get_session_backend()
        redis_client = backend.get_client()
        try:
            await redis_client.ping()
            logger.info("Redis health check passed")
        except Exception as e:
            raise RuntimeError(
                f"Redis health check failed: {e}. "
                f"Ensure Redis is running at {settings.redis_host}:{settings.redis_port}"
            ) from e

    yield

    runtime_service = getattr(app.state, RUNTIME_SERVICE_STATE_KEY, None)
    if runtime_service is not None:
        await runtime_service.close()

    logger.info("Application lifespan cleanup complete")
