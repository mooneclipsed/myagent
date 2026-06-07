"""HTTP routes for the refactor-v2 runtime and chat contract."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from agentops.api.schemas import ChatRequest, RuntimeInitRequest, RuntimeInitResponse
from agentops.config.settings import Settings, get_settings
from agentops.frameworks.agentscope_v2 import AgentScopeRuntimeBuilder, AgentScopeSessionExecutor
from agentops.frameworks.agentscope_v2.storage import (
    AgentScopeSessionStoreConfigError,
    AgentScopeSessionStoreProvider,
    create_session_store_provider_from_settings,
)
from agentops.frameworks.registry import UnknownFrameworkError
from agentops.orchestration.events import PlatformEvent
from agentops.orchestration.runtime_manager import RuntimeManager, RuntimeManagerError

ExecutorFactory = Callable[..., AgentScopeSessionExecutor]
SessionStoreProviderFactory = Callable[[Settings], AgentScopeSessionStoreProvider]
RUNTIME_SERVICE_STATE_KEY = "agentops_v2_runtime_service"


class V2RuntimeApiService:
    """Application service for the refactor-v2 HTTP routes."""

    def __init__(
        self,
        *,
        builder: AgentScopeRuntimeBuilder | None = None,
        manager: RuntimeManager | None = None,
        executor_factory: ExecutorFactory | None = None,
        settings: Settings | None = None,
        session_store_provider_factory: SessionStoreProviderFactory | None = None,
    ) -> None:
        """Create a v2 runtime API service."""
        self.builder = builder or AgentScopeRuntimeBuilder()
        self.manager = manager or RuntimeManager(builder=self.builder)
        self.executor_factory = executor_factory or AgentScopeSessionExecutor
        self._settings = settings
        self._session_store_provider_factory = (
            session_store_provider_factory or create_session_store_provider_from_settings
        )
        self._session_store_provider: AgentScopeSessionStoreProvider | None = None
        self._executor: AgentScopeSessionExecutor | None = None
        self._executor_runtime_id: str | None = None

    async def initialize(self, request: RuntimeInitRequest) -> RuntimeInitResponse:
        """Initialize the active v2 runtime."""
        session_store_provider = self._session_store_provider_factory(self._settings or get_settings())
        try:
            await session_store_provider.open()
        except AgentScopeSessionStoreConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AgentScope session storage failed to open: {exc}") from exc

        try:
            result = await self.manager.initialize(request)
        except UnknownFrameworkError as exc:
            await session_store_provider.close()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeManagerError as exc:
            await session_store_provider.close()
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        profile = self.manager.get_active_profile()
        resources = self.builder.get_resources(request.runtime_id)
        if profile is None or resources is None:
            await session_store_provider.close()
            raise HTTPException(status_code=500, detail="Runtime initialized without framework resources.")

        session_store = session_store_provider.create_store(user_id=profile.tenant_id or "default")
        await self._close_session_store_provider()
        self._session_store_provider = session_store_provider
        self._executor = self.executor_factory(profile=profile, resources=resources, session_store=session_store)
        self._executor_runtime_id = profile.runtime_id
        return RuntimeInitResponse.model_validate(result.model_dump())

    async def close(self) -> None:
        """Close v2 runtime API resources."""
        await self.manager.close_active_runtime()
        await self._close_session_store_provider()
        self._executor = None
        self._executor_runtime_id = None

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Stream v2 chat response as SSE data lines."""
        executor = self._get_executor(request.runtime_id)
        async for event in executor.platform_event_stream(
            session_id=request.session_id,
            input=request.input,
            request_id=request.execution_config.request_id,
        ):
            yield _sse_data(event)

    def _get_executor(self, runtime_id: str) -> AgentScopeSessionExecutor:
        profile = self.manager.get_active_profile()
        if profile is None or self._executor is None:
            raise HTTPException(status_code=400, detail="Runtime has not been initialized.")
        if profile.runtime_id != runtime_id or self._executor_runtime_id != runtime_id:
            raise HTTPException(status_code=400, detail="runtime_id does not match the active runtime.")
        return self._executor

    def validate_chat_request(self, request: ChatRequest) -> None:
        """Validate chat request before starting an SSE response."""
        self._get_executor(request.runtime_id)

    async def _close_session_store_provider(self) -> None:
        if self._session_store_provider is None:
            return
        await self._session_store_provider.close()
        self._session_store_provider = None


def register_v2_routes(app, service: V2RuntimeApiService | None = None) -> None:
    """Register refactor-v2 routes on a FastAPI-compatible app."""
    runtime_service = service or V2RuntimeApiService()
    setattr(app.state, RUNTIME_SERVICE_STATE_KEY, runtime_service)

    @app.post(
        "/v2/runtimes/init",
        response_model=RuntimeInitResponse,
        tags=["runtime-api-v2"],
    )
    async def initialize_runtime_profile(request: RuntimeInitRequest) -> RuntimeInitResponse:
        return await runtime_service.initialize(request)

    @app.post("/v2/chat", tags=["chat-api-v2"])
    async def chat(request: ChatRequest) -> StreamingResponse:
        runtime_service.validate_chat_request(request)
        return StreamingResponse(
            runtime_service.stream_chat(request),
            media_type="text/event-stream",
        )


def _sse_data(event: PlatformEvent) -> str:
    data = json.dumps(event.model_dump(mode="json", exclude_none=True), ensure_ascii=False)
    return f"data: {data}\n\n"
