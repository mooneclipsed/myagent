"""AgentScope v2 session execution helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field

from agentscope.agent import Agent
from agentscope.event import AgentEvent
from agentscope.message import Msg, UserMsg
from agentscope.state import AgentState

from agentops.orchestration.models import RuntimeProfile

from .adapter import build_agent
from .runtime import AgentScopeRuntimeResources

AgentFactory = Callable[[RuntimeProfile, AgentScopeRuntimeResources, AgentState], Agent]


@dataclass
class AgentScopeSessionExecutor:
    """Execute AgentScope v2 chat turns with frontend-owned session ids."""

    profile: RuntimeProfile
    resources: AgentScopeRuntimeResources
    agent_factory: AgentFactory | None = None
    _states_by_session_id: dict[str, AgentState] = field(default_factory=dict)

    def get_state(self, session_id: str) -> AgentState:
        """Return or create AgentScope state for a frontend session id."""
        state = self._states_by_session_id.get(session_id)
        if state is None:
            state = AgentState(session_id=session_id)
            self._states_by_session_id[session_id] = state
        return state

    async def reply(self, *, session_id: str, input: str) -> Msg:
        """Execute one chat turn and return the final AgentScope message."""
        agent = self._create_agent(session_id)
        return await agent.reply(_user_msg(input))

    async def reply_stream(
        self,
        *,
        session_id: str,
        input: str,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute one chat turn and stream AgentScope events."""
        agent = self._create_agent(session_id)
        async for event in agent.reply_stream(_user_msg(input)):
            yield event

    def _create_agent(self, session_id: str) -> Agent:
        state = self.get_state(session_id)
        if self.agent_factory is not None:
            return self.agent_factory(self.profile, self.resources, state)
        return create_agent(self.profile, self.resources, state)


def create_agent(profile: RuntimeProfile, resources: AgentScopeRuntimeResources, state: AgentState) -> Agent:
    """Create an AgentScope v2 agent bound to session state."""
    agent = build_agent(profile, toolkit=resources.toolkit)
    agent.state = state
    return agent


def _user_msg(input: str) -> Msg:
    return UserMsg(name="user", content=input)
