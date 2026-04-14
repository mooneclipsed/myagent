"""Session bootstrap and shutdown routes for dynamic MCP runtimes."""

from fastapi import HTTPException
from agentscope_runtime.engine import AgentApp

from src.agent.session import validate_session_id
from src.agent.session_runtime import (
    SessionBootstrapError,
    SessionRuntimeConflictError,
    SessionRuntimeNotFoundError,
    SessionRuntimeValidationError,
    bootstrap_session_runtime,
    shutdown_session_runtime,
)
from src.core.config import (
    SessionBootstrapRequest,
    SessionBootstrapResponse,
    SessionShutdownResponse,
)


def register_session_routes(app: AgentApp) -> None:
    """Register bootstrap and shutdown endpoints on the AgentApp."""

    @app.post(
        "/sessions/bootstrap",
        response_model=SessionBootstrapResponse,
        tags=["session-api"],
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
            session_id=runtime.session_id,
            tools=runtime.tool_summaries,
            skills=runtime.skill_summaries,
            mcp_servers=runtime.mcp_servers,
        )

    @app.post(
        "/sessions/{session_id}/shutdown",
        response_model=SessionShutdownResponse,
        tags=["session-api"],
    )
    async def shutdown_session(session_id: str) -> SessionShutdownResponse:
        if not validate_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session_id format.")

        try:
            await shutdown_session_runtime(session_id)
        except SessionRuntimeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return SessionShutdownResponse(session_id=session_id)
