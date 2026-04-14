"""Agent package bootstrap helpers."""


def register_query_handlers() -> None:
    """Import query handlers to trigger AgentApp route registration."""
    import src.agent.query  # noqa: F401
