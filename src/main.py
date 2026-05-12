from agentscope_runtime.engine import AgentApp

from .api.lifecycle import app_lifespan
from .api.runtime import register_runtime_routes
from .application.chat_service import register_query_handlers
from .config.settings import get_settings

app = AgentApp(
    app_name="agentops",
    app_description="AgentScope Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)
register_runtime_routes(app)

register_query_handlers(app)

if __name__ == "__main__":
    settings = get_settings()
    app.run(host="127.0.0.1", port=settings.PORT)
