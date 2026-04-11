"""Streaming query handler for the AgentApp /process endpoint."""

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.pipeline import stream_printing_messages

from src.core.settings import get_settings
from src.main import app


@app.query(framework="agentscope")
async def chat_query(self, msgs, request=None, **kwargs):
    """Handle chat queries with SSE streaming via agentscope-runtime.

    Creates a fresh agent per request using settings from .env.
    The @app.query decorator wraps this async generator into SSE events
    automatically, producing the lifecycle:
      response(created) -> response(in_progress) -> message(in_progress)
      -> content(in_progress) x N -> message(completed) -> response(completed)
      -> [DONE]

    Args:
        self: The AgentApp instance (passed by the decorator).
        msgs: The input messages from the request body (messages array per D-01).
        request: The raw AgentRequest object (optional, not used in this phase).
        **kwargs: Additional keyword arguments from the framework.

    Yields:
        Tuple of (msg, last) where msg is the response chunk and last indicates
        if this is the final chunk in the stream.
    """
    settings = get_settings()

    agent = ReActAgent(
        name="agentops",
        model=OpenAIChatModel(
            model_name=settings.MODEL_NAME,
            api_key=settings.MODEL_API_KEY,
            client_kwargs={"base_url": settings.MODEL_BASE_URL},
            stream=True,
        ),
        sys_prompt="You are a helpful assistant.",
        formatter=OpenAIChatFormatter(),
        memory=InMemoryMemory(),
    )
    agent.set_console_output_enabled(enabled=False)

    async for msg, last in stream_printing_messages(
        agents=[agent],
        coroutine_task=agent(msgs),
    ):
        yield msg, last
