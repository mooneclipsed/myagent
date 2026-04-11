"""Streaming query handler for the AgentApp /process endpoint."""

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.pipeline import stream_printing_messages

from src.agent.session import get_session_backend, validate_session_id
from src.core.config import AgentConfig, resolve_effective_config
from src.main import app
from src.tools import toolkit


@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    """Handle chat queries with SSE streaming and optional session persistence.

    Creates a fresh agent per request (D-07). When session_id is present,
    loads prior memory state before agent creation and saves updated memory
    after streaming completes (D-08). When session_id is absent, behavior
    is identical to Phase 5 (backward compatible, D-05).

    The @app.query decorator wraps this async generator into SSE events
    automatically, producing the lifecycle:
      response(created) -> response(in_progress) -> message(in_progress)
      -> content(in_progress) x N -> message(completed) -> response(completed)
      -> [DONE]

    Args:
        self: The AgentApp instance (passed by the decorator).
        msgs: The input messages from the request body (messages array per D-01).
        request: The raw AgentRequest object (optional, may carry agent_config).
        **kwargs: Additional keyword arguments from the framework.

    Yields:
        Tuple of (msg, last) where msg is the response chunk and last indicates
        if this is the final chunk in the stream.
    """
    # Extract per-request config override (D-01, D-04)
    agent_config = None
    if request and hasattr(request, "agent_config") and request.agent_config:
        agent_config = AgentConfig(**request.agent_config)
    config = resolve_effective_config(agent_config)

    # Session-aware memory (D-01, D-04, D-07)
    session_backend = get_session_backend()
    memory = InMemoryMemory()
    session_id = None

    if request and hasattr(request, "session_id") and request.session_id:
        raw_session_id = request.session_id
        if validate_session_id(raw_session_id):
            session_id = raw_session_id
            await session_backend.load_session_state(
                session_id=session_id,
                memory=memory,
            )

    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=config["model_name"],
            api_key=config["api_key"],
            client_kwargs={"base_url": config["base_url"]},
            stream=True,
        ),
        sys_prompt="You are a helpful assistant.",
        formatter=OpenAIChatFormatter(),
        memory=memory,
        toolkit=toolkit,  # Phase 4 D-01/D-02: shared toolkit with registered tools + MCP
    )
    agent.set_console_output_enabled(enabled=False)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last

    # Save updated memory after streaming completes (D-08)
    if session_id:
        await session_backend.save_session_state(
            session_id=session_id,
            memory=agent.memory,
        )
