"""Tests for refactor-v2 framework-neutral schemas."""

from pydantic import ValidationError
import pytest

from agentops.api.schemas import ChatRequest, RuntimeInitRequest
from agentops.capabilities.v2_models import CapabilitySpec
from agentops.frameworks.registry import UnknownFrameworkError, list_frameworks, resolve_framework
from agentops.orchestration.messages import StandardMessage
from agentops.orchestration.models import AgentSpec, RuntimeInitResult, StorageRef, TraceRef, WorkspaceRef
from agentops.orchestration.observability import hash_system_prompt
from agentops.orchestration.workspace import build_runtime_workspace_path


def test_standard_message_validates_payload_by_type():
    message = StandardMessage(
        type="tool_call",
        payload={
            "id": "call_1",
            "name": "get_weather",
            "provider": "mcp",
            "arguments": {"city": "Beijing"},
        },
    )

    assert message.type == "tool_call"


def test_standard_message_rejects_wrong_payload_shape():
    with pytest.raises(ValidationError):
        StandardMessage(
            type="tool_call",
            payload={"content": [{"type": "text", "text": "not a tool call"}]},
        )


def test_capability_spec_validates_type_specific_config():
    capability = CapabilitySpec(
        type="skill",
        name="project_skills",
        config={"path": ".skills/"},
    )

    assert capability.enabled is True


def test_capability_spec_rejects_unknown_type():
    with pytest.raises(ValidationError):
        CapabilitySpec(type="unknown", name="bad", config={})


def test_chat_request_uses_current_input_not_history():
    request = ChatRequest(
        runtime_id="runtime-1",
        session_id="session-1",
        input="hello",
    )

    assert request.input == "hello"

    with pytest.raises(ValidationError):
        ChatRequest(
            runtime_id="runtime-1",
            session_id="session-1",
            input=[{"role": "user", "content": "hello"}],
        )


def test_runtime_init_request_defaults_to_agentscope_framework():
    request = RuntimeInitRequest(
        runtime_id="runtime-1",
        model_config={"model_name": "test-model"},
    )

    assert request.framework == "agentscope"
    assert request.model_config_.model_name == "test-model"


def test_framework_registry_resolves_agentscope_and_rejects_unknown():
    assert list_frameworks() == ["agentscope"]
    assert resolve_framework("agentscope").adapter_package.endswith("agentscope_v2")

    with pytest.raises(UnknownFrameworkError, match="Framework 'missing' does not exist."):
        resolve_framework("missing")


def test_runtime_init_result_excludes_secrets_and_raw_prompt():
    agent_spec = AgentSpec(
        model_config={
            "model_name": "gpt-4o",
            "api_key": "secret",
            "base_url": "http://localhost:9999/v1",
        },
        system_prompt="secret prompt",
        prompt_hash=hash_system_prompt("secret prompt"),
    )
    result = RuntimeInitResult(
        runtime_id="runtime-1",
        framework="agentscope",
        status="ready",
        workspace=WorkspaceRef(root="/app/workspaces", runtime_path="/app/workspaces/runtime-1"),
        storage=StorageRef(type="redis"),
        tracing=TraceRef(enabled=False),
    )

    dumped_spec = agent_spec.model_dump(by_alias=True)
    dumped_result = result.model_dump()

    assert "api_key" not in dumped_spec["model_config"]
    assert "base_url" not in dumped_spec["model_config"]
    assert "system_prompt" not in dumped_spec
    assert "secret" not in str(dumped_result)


def test_runtime_workspace_path_rejects_path_traversal():
    assert str(build_runtime_workspace_path("runtime-1", root="/tmp/workspaces")).endswith(
        "/tmp/workspaces/runtime-1",
    )

    with pytest.raises(ValueError):
        build_runtime_workspace_path("../bad", root="/tmp/workspaces")
