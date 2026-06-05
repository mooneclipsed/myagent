"""Tests for AgentScope v2 adapter construction helpers."""

from pathlib import Path
import asyncio

import pytest
from agentscope.mcp import MCPClient
from agentscope.permission import PermissionBehavior
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

from agentops.api.schemas import RuntimeInitRequest
from agentops.frameworks.agentscope_v2 import (
    AgentScopeV2AdapterError,
    build_agent_spec,
    build_chat_model,
    build_mcp_clients,
    build_toolkit,
    resolve_skill_path,
)


def test_build_agent_spec_hashes_system_prompt() -> None:
    spec = build_agent_spec(
        RuntimeInitRequest(
            runtime_id="runtime-1",
            model_config={"model_name": "test-model", "api_key": "secret"},
            system_prompt="system prompt",
        ),
    )

    assert spec.prompt_hash.startswith("sha256:")
    assert spec.system_prompt == "system prompt"


def test_build_chat_model_requires_model_name_and_api_key() -> None:
    spec = build_agent_spec(RuntimeInitRequest(runtime_id="runtime-1"))

    with pytest.raises(AgentScopeV2AdapterError, match="model_config.model_name is required"):
        build_chat_model(spec.model_config_)


def test_build_chat_model_uses_openai_compatible_model() -> None:
    spec = build_agent_spec(
        RuntimeInitRequest(
            runtime_id="runtime-1",
            model_config={
                "model_name": "gpt-4o-mini",
                "api_key": "secret",
                "base_url": "http://localhost:9999/v1",
            },
        ),
    )

    assert isinstance(build_chat_model(spec.model_config_), OpenAIChatModel)


def test_build_toolkit_maps_tools_skills_and_mcp(tmp_path: Path) -> None:
    request = RuntimeInitRequest(
        runtime_id="runtime-1",
        capabilities=[
            {"type": "tool", "name": "read", "config": {"tool_name": "read"}},
            {"type": "skill", "name": "skills", "config": {"path": ".skills/"}},
            {
                "type": "mcp",
                "name": "time",
                "config": {"transport": "stdio", "command": "python", "args": ["server.py"]},
            },
        ],
    )

    toolkit = build_toolkit(request, tmp_path)

    assert isinstance(toolkit, Toolkit)
    assert any(isinstance(mcp, MCPClient) for mcp in build_mcp_clients(request))
    assert resolve_skill_path(".skills/", tmp_path) == str(tmp_path / ".skills")


def test_build_toolkit_maps_project_local_function_tools(tmp_path: Path) -> None:
    request = RuntimeInitRequest(
        runtime_id="runtime-1",
        capabilities=[
            {"type": "tool", "name": "get_weather", "config": {"tool_name": "local:get_weather"}},
        ],
    )

    toolkit = build_toolkit(request, tmp_path)
    tool = toolkit.tool_groups[0].tools[0]

    assert tool.name == "get_weather"
    assert tool.is_read_only is True
    decision = asyncio.run(tool.check_permissions({}, None))
    assert decision.behavior == PermissionBehavior.ALLOW


def test_build_toolkit_rejects_unknown_tool(tmp_path: Path) -> None:
    request = RuntimeInitRequest(
        runtime_id="runtime-1",
        capabilities=[
            {"type": "tool", "name": "bad", "config": {"tool_name": "missing"}},
        ],
    )

    with pytest.raises(AgentScopeV2AdapterError, match="Unknown AgentScope v2 tool"):
        build_toolkit(request, tmp_path)
