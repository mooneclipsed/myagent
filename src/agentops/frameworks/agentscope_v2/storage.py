"""Configured AgentScope v2 session store assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentscope.app.storage import RedisStorage

from agentops.config.settings import Settings

from .session_store import AgentScopeAppSessionStore, AgentScopeSessionStore, InMemoryAgentScopeSessionStore

SessionStoreBackend = Literal["json", "memory", "redis"]


class AgentScopeSessionStoreConfigError(ValueError):
    """Raised when AgentScope v2 session storage configuration is invalid."""


@dataclass
class AgentScopeSessionStoreProvider:
    """Create AgentScope session stores from one configured storage backend."""

    backend: SessionStoreBackend
    redis_storage: RedisStorage | None = None
    _is_open: bool = False

    async def open(self) -> None:
        """Open backend resources required before chat execution."""
        if self.backend != "redis" or self._is_open:
            return
        if self.redis_storage is None:
            raise AgentScopeSessionStoreConfigError("Redis session store requires RedisStorage.")
        await self.redis_storage.__aenter__()
        self._is_open = True

    async def close(self) -> None:
        """Close backend resources owned by the provider."""
        if self.backend != "redis" or not self._is_open:
            return
        if self.redis_storage is not None:
            await self.redis_storage.__aexit__(None, None, None)
        self._is_open = False

    def create_store(self, *, user_id: str = "default") -> AgentScopeSessionStore:
        """Create a session store for one runtime owner."""
        if self.backend == "redis":
            if self.redis_storage is None or not self._is_open:
                raise AgentScopeSessionStoreConfigError("Redis session store has not been opened.")
            return AgentScopeAppSessionStore(storage=self.redis_storage, user_id=user_id)
        return InMemoryAgentScopeSessionStore()


def create_session_store_provider_from_settings(settings: Settings) -> AgentScopeSessionStoreProvider:
    """Create an AgentScope v2 session store provider from app settings."""
    backend = settings.session_backend.lower()
    if backend in {"json", "memory"}:
        return AgentScopeSessionStoreProvider(backend=backend)
    if backend == "redis":
        return AgentScopeSessionStoreProvider(
            backend="redis",
            redis_storage=RedisStorage(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
            ),
        )
    raise AgentScopeSessionStoreConfigError(f"Unsupported SESSION_BACKEND for AgentScope v2: {settings.session_backend}")
