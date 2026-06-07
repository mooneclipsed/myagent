import uvicorn
from fastapi import FastAPI

from .api.lifespan import app_lifespan
from .api.v2 import register_v2_routes
from .config.settings import get_settings

app = FastAPI(
    title="agentops",
    description="AgentScope Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)
register_v2_routes(app)


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host="127.0.0.1", port=settings.port)
