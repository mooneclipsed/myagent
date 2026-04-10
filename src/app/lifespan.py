from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.settings import get_settings


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    get_settings()
    yield
