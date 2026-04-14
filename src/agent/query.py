"""Streaming query handler for the AgentApp /process endpoint."""

from agentscope.memory import InMemoryMemory
from agentscope.pipeline import stream_printing_messages

from src.agent.session import get_session_backend, validate_session_id
from src.agent.session_runtime import build_react_agent, get_session_runtime
from src.core.config import AgentConfig, resolve_effective_config
from src.main import app
from src.tools import toolkit


@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    """Handle chat queries with SSE streaming and optional session persistence."""
    session_backend = get_session_backend()
    session_id = None
    runtime = None

    if request and hasattr(request, "session_id") and request.session_id:
        raw_session_id = request.session_id
        if validate_session_id(raw_session_id):
            session_id = raw_session_id
            runtime = get_session_runtime(session_id)

    if runtime is not None:
        if request and hasattr(request, "agent_config") and request.agent_config:
            raise RuntimeError(
                "Bootstrapped sessions do not accept agent_config on /process. Re-bootstrap the session instead.",
            )
        agent = runtime.agent
    else:
        agent_config = None
        if request and hasattr(request, "agent_config") and request.agent_config:
            agent_config = AgentConfig(**request.agent_config)
        config = resolve_effective_config(agent_config)

        memory = InMemoryMemory()
        if session_id:
            await session_backend.load_session_state(
                session_id=session_id,
                memory=memory,
            )

        agent = build_react_agent(
            resolved_config=config,
            memory=memory,
            toolkit=toolkit,
        )

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

    if session_id:
        await session_backend.save_session_state(
            session_id=session_id,
            memory=agent.memory,
        )
