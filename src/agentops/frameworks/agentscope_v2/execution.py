"""AgentScope v2 session execution helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field

from agentscope.agent import Agent
from agentscope.event import AgentEvent
from agentscope.message import Msg, UserMsg
from agentscope.state import AgentState

from agentops.orchestration.models import RuntimeProfile
from agentops.orchestration.events import PlatformEvent

from .adapter import build_agent
from .event_mapping import PlatformEventMapper
from .runtime import AgentScopeRuntimeResources
from .session_store import AgentScopeSessionStore, InMemoryAgentScopeSessionStore

AgentFactory = Callable[[RuntimeProfile, AgentScopeRuntimeResources, AgentState], Agent]


@dataclass
class AgentScopeSessionExecutor:
    """Execute AgentScope v2 chat turns with frontend-owned session ids."""

    profile: RuntimeProfile
    resources: AgentScopeRuntimeResources
    agent_factory: AgentFactory | None = None
    session_store: AgentScopeSessionStore = field(default_factory=InMemoryAgentScopeSessionStore)
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
        agent = await self._create_agent(session_id)
        message = await agent.reply(_user_msg(input))
        await self._save_state(session_id, agent.state)
        return message

    async def reply_stream(
        self,
        *,
        session_id: str,
        input: str,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute one chat turn and stream AgentScope events."""
        agent = await self._create_agent(session_id)
        try:
            async for event in agent.reply_stream(_user_msg(input)):
                yield event
        finally:
            await self._save_state(session_id, agent.state)

    async def platform_event_stream(
        self,
        *,
        session_id: str,
        input: str,
        request_id: str | None = None,
    ) -> AsyncGenerator[PlatformEvent, None]:
        """Execute one chat turn and stream platform events."""
        mapper = PlatformEventMapper(
            profile=self.profile,
            session_id=session_id,
            request_id=request_id,
        )
        async for event in self.reply_stream(session_id=session_id, input=input):
            platform_event = mapper.map_event(event)
            if platform_event is not None:
                yield platform_event

    async def _create_agent(self, session_id: str) -> Agent:
        state = await self._get_or_load_state(session_id)
        if self.agent_factory is not None:
            return self.agent_factory(self.profile, self.resources, state)
        return create_agent(self.profile, self.resources, state)

    async def _get_or_load_state(self, session_id: str) -> AgentState:
        state = self._states_by_session_id.get(session_id)
        if state is not None:
            return state

        loaded_state = await self.session_store.load_state(
            runtime_id=self.profile.runtime_id,
            session_id=session_id,
            workspace_id=self.profile.workspace.runtime_path,
        )
        if loaded_state is not None:
            self._states_by_session_id[session_id] = loaded_state
            return loaded_state

        return self.get_state(session_id)

    async def _save_state(self, session_id: str, state: AgentState) -> None:
        self._states_by_session_id[session_id] = state
        await self.session_store.save_state(
            runtime_id=self.profile.runtime_id,
            session_id=session_id,
            workspace_id=self.profile.workspace.runtime_path,
            state=state,
        )


def create_agent(profile: RuntimeProfile, resources: AgentScopeRuntimeResources, state: AgentState) -> Agent:
    """Create an AgentScope v2 agent bound to session state."""
    agent = build_agent(profile, toolkit=resources.toolkit)
    agent.state = state
    return agent


def _user_msg(input: str) -> Msg:
    return UserMsg(name="user", content=input)
