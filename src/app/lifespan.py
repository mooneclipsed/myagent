"""FastAPI lifespan hook for startup validation and runtime cleanup."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..agent.session_runtime import close_all_session_runtimes
from ..core.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    settings = get_settings()

    if settings.SESSION_BACKEND == "json":
        session_dir = settings.SESSION_DIR
        os.makedirs(session_dir, exist_ok=True)
        logger.info("Session directory ready: %s", session_dir)

    if settings.SESSION_BACKEND == "redis":
        from ..agent.session import get_session_backend

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

    yield

    await close_all_session_runtimes()

    from ..agent.session import _session_backend, reset_session_backend

    if _session_backend is not None and hasattr(_session_backend, "close"):
        try:
            await _session_backend.close()
            logger.info("Redis session backend closed")
        except Exception as e:
            logger.warning("Error closing session backend: %s", e)
        reset_session_backend()

    logger.info("Application lifespan cleanup complete")
