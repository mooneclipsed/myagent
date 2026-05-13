"""HTTP endpoints for chat and runtime lifecycle."""

from fastapi import HTTPException
from agentscope_runtime.engine import AgentApp

from ..application.chat_service import chat_via_agentscope
from ..config.schemas import (
    RuntimeInitializeRequest,
    RuntimeProfileResponse,
    SessionShutdownResponse,
)
from ..application.runtime_service import (
    RuntimeInitializationError,
    SessionRuntimeConflictError,
    SessionRuntimeNotFoundError,
    SessionRuntimeValidationError,
    initialize_runtime_from_request,
    shutdown_runtime_profile,
)
from ..sessions.backend import validate_session_id


def register_runtime_routes(app: AgentApp) -> None:
    """Register chat and runtime lifecycle endpoints on the AgentApp."""

    app.post("/chat")(chat_via_agentscope)

    @app.post(
        "/runtimes/init",
        response_model=RuntimeProfileResponse,
        tags=["runtime-api"],
    )
    async def initialize_runtime_profile(
        request: RuntimeInitializeRequest,
    ) -> RuntimeProfileResponse:
        try:
            runtime, _ = await initialize_runtime_from_request(request)
        except SessionRuntimeValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SessionRuntimeConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RuntimeInitializationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return RuntimeProfileResponse(
            runtime_id=runtime.runtime_id,
            tools=runtime.tool_summaries,
            skills=runtime.skill_summaries,
            skill_downloads=runtime.skill_downloads,
            mcp_servers=runtime.mcp_servers,
        )

    @app.post(
        "/runtimes/{runtime_id}/shutdown",
        response_model=SessionShutdownResponse,
        tags=["runtime-api"],
    )
    async def shutdown_runtime(runtime_id: str) -> SessionShutdownResponse:
        if not validate_session_id(runtime_id):
            raise HTTPException(status_code=400, detail="Invalid runtime_id format.")

        try:
            await shutdown_runtime_profile(runtime_id)
        except SessionRuntimeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return SessionShutdownResponse(runtime_id=runtime_id)
