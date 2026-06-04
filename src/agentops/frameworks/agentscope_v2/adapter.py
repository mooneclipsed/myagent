"""AgentScope v2 adapter construction helpers."""

from __future__ import annotations

from pathlib import Path

from agentscope.agent import Agent
from agentscope.credential import DashScopeCredential, OpenAICredential
from agentscope.mcp import HttpMCPConfig, MCPClient, StdioMCPConfig
from agentscope.model import DashScopeChatModel, OpenAIChatModel
from agentscope.tool import Bash, Edit, Glob, Grep, Read, Toolkit, Write

from agentops.api.schemas import RuntimeInitRequest
from agentops.capabilities.v2_models import MCPCapabilityConfig
from agentops.orchestration.models import AgentSpec, ModelConfig, RuntimeProfile
from agentops.orchestration.observability import hash_system_prompt


class AgentScopeV2AdapterError(RuntimeError):
    """Raised when AgentScope v2 adapter construction fails."""


def build_agent_spec(request: RuntimeInitRequest) -> AgentSpec:
    """Build an immutable agent spec from an init request."""
    system_prompt = request.system_prompt or "You are a helpful assistant."
    return AgentSpec(
        model_config=request.model_config_ or ModelConfig(),
        system_prompt=system_prompt,
        prompt_hash=hash_system_prompt(system_prompt),
    )


def build_chat_model(model_config: ModelConfig):
    """Build an AgentScope v2 chat model from platform model config."""
    if not model_config.model_name:
        raise AgentScopeV2AdapterError("model_config.model_name is required.")
    if not model_config.api_key:
        raise AgentScopeV2AdapterError("model_config.api_key is required.")

    if model_config.base_url and "dashscope" in model_config.base_url:
        credential = DashScopeCredential(api_key=model_config.api_key, base_url=model_config.base_url)
        return DashScopeChatModel(credential=credential, model=model_config.model_name)

    credential = OpenAICredential(api_key=model_config.api_key, base_url=model_config.base_url)
    return OpenAIChatModel(credential=credential, model=model_config.model_name)


def build_toolkit(request: RuntimeInitRequest, workspace_path: Path) -> Toolkit:
    """Build an AgentScope v2 toolkit from enabled local tools and skills."""
    tools = []
    skill_paths = []

    for capability in request.capabilities:
        if not capability.enabled:
            continue
        if capability.type == "tool":
            tools.append(_build_builtin_tool(capability.config["tool_name"]))
        elif capability.type == "skill":
            skill_paths.append(resolve_skill_path(capability.config["path"], workspace_path))

    return Toolkit(tools=tools, skills_or_loaders=skill_paths)


def build_mcp_clients(request: RuntimeInitRequest) -> list[MCPClient]:
    """Build AgentScope v2 MCP clients from enabled MCP capabilities."""
    return [
        _build_mcp_client(capability.name, capability.config)
        for capability in request.capabilities
        if capability.enabled and capability.type == "mcp"
    ]


def build_agent(profile: RuntimeProfile, toolkit: Toolkit | None = None) -> Agent:
    """Build an AgentScope v2 agent from a runtime profile."""
    chat_model = build_chat_model(profile.agent_spec.model_config_)
    return Agent(
        name=profile.runtime_id,
        system_prompt=profile.agent_spec.system_prompt,
        model=chat_model,
        toolkit=toolkit,
    )


def resolve_skill_path(path: str, workspace_path: Path) -> str:
    """Resolve a skill path relative to the runtime workspace."""
    skill_path = Path(path)
    if skill_path.is_absolute():
        return str(skill_path)
    return str(workspace_path / skill_path)


def _build_builtin_tool(tool_name: str):
    if tool_name == "bash":
        return Bash()
    if tool_name == "read":
        return Read()
    if tool_name == "write":
        return Write()
    if tool_name == "edit":
        return Edit()
    if tool_name == "grep":
        return Grep()
    if tool_name == "glob":
        return Glob()
    raise AgentScopeV2AdapterError(f"Unknown AgentScope v2 tool: {tool_name}")


def _build_mcp_client(name: str, config: dict) -> MCPClient:
    parsed = MCPCapabilityConfig.model_validate(config)
    if parsed.transport == "stdio":
        mcp_config = StdioMCPConfig(
            command=parsed.command or "",
            args=parsed.args,
            env=parsed.env,
            cwd=parsed.cwd,
        )
    elif parsed.transport in {"sse", "streamable_http"}:
        if not parsed.url:
            raise AgentScopeV2AdapterError("MCP http transport requires url.")
        mcp_config = HttpMCPConfig(url=parsed.url, headers=parsed.headers, timeout=parsed.timeout)
    else:
        raise AgentScopeV2AdapterError(f"Unsupported MCP transport: {parsed.transport}")

    return MCPClient(name=name, is_stateful=True, mcp_config=mcp_config, execution_timeout=parsed.timeout)
