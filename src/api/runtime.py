"""HTTP endpoints for runtime lifecycle."""

from fastapi import HTTPException
from agentscope_runtime.engine import AgentApp

from ..config.schemas import (
    RuntimeInitializeRequest,
    RuntimeProfileResponse,
)
from ..application.runtime_service import (
    RuntimeInitializationError,
    SessionRuntimeValidationError,
    initialize_runtime_from_request,
)


def register_runtime_routes(app: AgentApp) -> None:
    """Register runtime lifecycle endpoints on the AgentApp."""

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
        except RuntimeInitializationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return RuntimeProfileResponse(
            runtime_id=runtime.runtime_id,
            tools=runtime.tool_summaries,
            skills=runtime.skill_summaries,
            skill_downloads=runtime.skill_downloads,
            mcp_servers=runtime.mcp_servers,
        )
