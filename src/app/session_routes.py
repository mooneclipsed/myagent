"""Explicit HTTP routes for chat and runtime lifecycle."""

from fastapi import HTTPException
from agentscope_runtime.engine import AgentApp

from ..agent.query import chat_via_agentscope
from ..agent.session import validate_session_id
from ..agent.session_runtime import (
    SessionBootstrapError,
    SessionRuntimeConflictError,
    SessionRuntimeNotFoundError,
    SessionRuntimeValidationError,
    bootstrap_session_runtime,
    shutdown_runtime_profile,
)
from ..core.config import (
    SessionBootstrapRequest,
    SessionBootstrapResponse,
    SessionShutdownResponse,
)


def register_session_routes(app: AgentApp) -> None:
    """Register explicit chat and session lifecycle endpoints on the AgentApp."""

    app.post("/chat")(chat_via_agentscope)

    @app.post(
        "/runtimes/bootstrap",
        response_model=SessionBootstrapResponse,
        tags=["runtime-api"],
    )
    async def bootstrap_session(
        request: SessionBootstrapRequest,
    ) -> SessionBootstrapResponse:
        try:
            runtime, _ = await bootstrap_session_runtime(request)
        except SessionRuntimeValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SessionRuntimeConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SessionBootstrapError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return SessionBootstrapResponse(
            runtime_id=runtime.runtime_id,
            tools=runtime.tool_summaries,
            skills=runtime.skill_summaries,
            mcp_servers=runtime.mcp_servers,
        )

    @app.post(
        "/runtimes/{runtime_id}/shutdown",
        response_model=SessionShutdownResponse,
        tags=["runtime-api"],
    )
    async def shutdown_session(runtime_id: str) -> SessionShutdownResponse:
        if not validate_session_id(runtime_id):
            raise HTTPException(status_code=400, detail="Invalid runtime_id format.")

        try:
            await shutdown_runtime_profile(runtime_id)
        except SessionRuntimeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return SessionShutdownResponse(runtime_id=runtime_id)
