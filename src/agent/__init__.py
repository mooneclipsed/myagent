"""Agent package bootstrap helpers."""

from agentscope_runtime.engine import AgentApp


def register_query_handlers(app: AgentApp) -> None:
    """Register AgentScope-managed query handlers on the app."""
    from src.agent.query import register_query_handlers as register_query_routes

    register_query_routes(app)
