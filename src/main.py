from agentscope_runtime.engine import AgentApp

from . import agent
from .app.lifespan import app_lifespan
from .app.session_routes import register_session_routes
from .core.settings import get_settings

app = AgentApp(
    app_name="agentops",
    app_description="AgentScope Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)
register_session_routes(app)

agent.register_query_handlers(app)

if __name__ == "__main__":
    settings = get_settings()
    app.run(host="127.0.0.1", port=settings.PORT)
