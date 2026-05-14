"""AgentApp chat endpoint registration."""

from agentscope_runtime.engine import AgentApp

from ..application.chat_service import chat_service


def register_chat_query(app: AgentApp) -> None:
    """Register the AgentScope chat query endpoint."""
    app.query(framework="agentscope")(chat_service)
