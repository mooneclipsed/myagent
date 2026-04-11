from agentscope_runtime.engine import AgentApp

from src.app.lifespan import app_lifespan

app = AgentApp(
    app_name="agentops",
    app_description="AgentScope Skill/Tool/MCP Validation Platform",
    lifespan=app_lifespan,
)

# Import agent package to trigger @app.query handler registration
import src.agent  # noqa: F401

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
