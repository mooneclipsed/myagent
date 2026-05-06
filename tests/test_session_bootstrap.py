"""Tests for session bootstrap MCP runtime lifecycle and routing."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import agentscope
import pytest
from agentscope.message import Msg
from agentscope.tracing._extractor import _get_common_attributes
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.agent.session_runtime import close_all_session_runtimes, get_session_runtime
from tests.test_chat_stream import _parse_sse_events



async def _mock_stream(*args, **kwargs):
    msg = Msg(
        name="agentops",
        content=[{"type": "text", "text": "ok"}],
        role="assistant",
    )
    yield msg, True


@pytest.fixture(autouse=True)
def _clear_runtime_between_tests():
    import asyncio

    asyncio.run(close_all_session_runtimes())
    yield
    asyncio.run(close_all_session_runtimes())


def test_bootstrap_stdio_session_success(client):
    payload = {
        "session_id": "bootstrap-session-001",
        "mcp_servers": [
            {
                "name": "time-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["-m", "src.mcp.server"],
                "env": {"DEMO": "1"},
                "cwd": "/tmp/demo",
            }
        ],
    }

    with patch("src.agent.session_runtime.StdIOStatefulClient") as mock_stdio:
        mock_client = AsyncMock()
        mock_client.name = "time-mcp"
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_stdio.return_value = mock_client

        response = client.post("/sessions/bootstrap", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["session_id"] == "bootstrap-session-001"
    assert body["status"] == "ready"
    assert body["mcp_servers"] == [{"name": "time-mcp", "type": "stdio", "transport": None}]
    mock_stdio.assert_called_once_with(
        name="time-mcp",
        command="python",
        args=["-m", "src.mcp.server"],
        env={"DEMO": "1"},
        cwd="/tmp/demo",
    )


def test_bootstrap_http_session_success(client):
    payload = {
        "session_id": "bootstrap-session-002",
        "mcp_servers": [
            {
                "name": "remote-mcp",
                "type": "http",
                "transport": "streamable_http",
                "url": "http://example.com/mcp",
                "headers": {"Authorization": "Bearer secret"},
                "timeout": 12,
                "sse_read_timeout": 34,
            }
        ],
    }

    with patch("src.agent.session_runtime.HttpStatefulClient") as mock_http:
        mock_client = AsyncMock()
        mock_client.name = "remote-mcp"
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_http.return_value = mock_client

        response = client.post("/sessions/bootstrap", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mcp_servers"] == [
        {
            "name": "remote-mcp",
            "type": "http",
            "transport": "streamable_http",
        }
    ]
    mock_http.assert_called_once_with(
        name="remote-mcp",
        transport="streamable_http",
        url="http://example.com/mcp",
        headers={"Authorization": "Bearer secret"},
        timeout=12,
        sse_read_timeout=34,
    )


def test_bootstrap_rejects_invalid_http_transport(client):
    payload = {
        "session_id": "bootstrap-session-003",
        "mcp_servers": [
            {
                "name": "bad-http",
                "type": "http",
                "transport": "websocket",
                "url": "http://example.com/mcp",
            }
        ],
    }

    response = client.post("/sessions/bootstrap", json=payload)
    assert response.status_code == 422


def test_bootstrap_conflict_when_another_session_active(client):
    payload_a = {"session_id": "bootstrap-session-a", "skills": [], "mcp_servers": []}
    payload_b = {"session_id": "bootstrap-session-b", "skills": [], "mcp_servers": []}

    response_a = client.post("/sessions/bootstrap", json=payload_a)
    response_b = client.post("/sessions/bootstrap", json=payload_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 409
    assert "already owns this pod runtime" in response_b.json()["detail"]


def test_bootstrap_without_system_prompt_uses_default_prompt(client):
    payload = {"session_id": "bootstrap-default-prompt", "skills": [], "mcp_servers": []}

    response = client.post("/sessions/bootstrap", json=payload)

    assert response.status_code == 200, response.text
    runtime = get_session_runtime("bootstrap-default-prompt")
    assert runtime is not None
    assert runtime.agent.sys_prompt == "You are a helpful assistant."


def test_bootstrap_same_session_returns_existing_runtime(client):
    payload = {"session_id": "bootstrap-session-same", "skills": [], "mcp_servers": []}

    response_a = client.post("/sessions/bootstrap", json=payload)
    response_b = client.post("/sessions/bootstrap", json=payload)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json()["session_id"] == response_b.json()["session_id"]


def test_bootstrap_with_blank_system_prompt_uses_default_prompt(client):
    payload = {
        "session_id": "bootstrap-blank-prompt",
        "system_prompt": "   ",
        "skills": [],
        "mcp_servers": [],
    }

    response = client.post("/sessions/bootstrap", json=payload)

    assert response.status_code == 200, response.text
    runtime = get_session_runtime("bootstrap-blank-prompt")
    assert runtime is not None
    assert runtime.agent.sys_prompt == "You are a helpful assistant."


def test_build_react_agent_enables_console_output_from_settings(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.setenv("AGENT_CONSOLE_OUTPUT_ENABLED", "true")

    from src.agent.session_runtime import build_react_agent
    from src.core.settings import get_settings
    from agentscope.memory import InMemoryMemory
    from agentscope.tool import Toolkit

    get_settings.cache_clear()

    agent = build_react_agent(
        resolved_config={
            "model_name": "test-model",
            "api_key": "test-key",
            "base_url": "http://localhost:9999/v1",
        },
        memory=InMemoryMemory(),
        toolkit=Toolkit(),
    )

    assert agent._disable_console_output is False


def test_thinking_formatter_warning_filter_is_installed_on_agentscope_logger():
    import logging
    from src.agent.session_runtime import _AgentScopeThinkingWarningFilter

    logger = logging.getLogger("as")

    assert any(isinstance(item, _AgentScopeThinkingWarningFilter) for item in logger.filters)


def test_bootstrap_failure_rolls_back_connected_clients(client):
    payload = {
        "session_id": "bootstrap-session-fail",
        "mcp_servers": [
            {"name": "first", "type": "stdio", "command": "python"},
            {"name": "second", "type": "stdio", "command": "python"},
        ],
    }

    first_client = AsyncMock()
    first_client.name = "first"
    first_client.is_connected = True
    first_client.list_tools = AsyncMock(return_value=[])

    second_client = AsyncMock()
    second_client.name = "second"
    second_client.connect = AsyncMock(side_effect=RuntimeError("boom"))
    second_client.is_connected = False

    with patch(
        "src.agent.session_runtime.StdIOStatefulClient",
        side_effect=[first_client, second_client],
    ):
        response = client.post("/sessions/bootstrap", json=payload)

    assert response.status_code == 502
    assert "Failed to initialize MCP server 'second' (stdio)." == response.json()["detail"]
    first_client.close.assert_awaited_once_with(ignore_errors=True)


def test_process_reuses_bootstrapped_session_agent(client, valid_payload):
    bootstrap_payload = {"session_id": "bootstrap-process-001", "skills": [], "mcp_servers": []}
    response = client.post("/sessions/bootstrap", json=bootstrap_payload)
    assert response.status_code == 200

    runtime = get_session_runtime("bootstrap-process-001")
    assert runtime is not None

    async def _mock_stream_runtime(*args, **kwargs):
        assert kwargs["agents"] == [runtime.agent]
        coroutine_task = kwargs["coroutine_task"]
        assert coroutine_task.cr_code.co_name == "__call__"
        coroutine_task.close()
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "ok"}],
            role="assistant",
        )
        yield msg, True

    with patch("src.agent.query.stream_printing_messages", _mock_stream_runtime):
        process_payload = {
            **valid_payload,
            "session_id": "bootstrap-process-001",
        }
        process_response = client.post("/process", json=process_payload)

    assert process_response.status_code == 200
    events = _parse_sse_events(process_response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


def test_process_rebinds_agentscope_run_context_for_bootstrapped_session(client, valid_payload):
    session_id = "bootstrap-process-trace-bind"
    response = client.post("/sessions/bootstrap", json={"session_id": session_id, "skills": [], "mcp_servers": []})
    assert response.status_code == 200

    captured = {}

    async def _mock_stream_runtime(*args, **kwargs):
        captured["run_id"] = agentscope._config.run_id
        coroutine_task = kwargs["coroutine_task"]
        coroutine_task.close()
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "ok"}],
            role="assistant",
        )
        yield msg, True

    with patch("src.agent.query.stream_printing_messages", _mock_stream_runtime):
        process_response = client.post(
            "/process",
            json={
                **valid_payload,
                "session_id": session_id,
            },
        )

    assert process_response.status_code == 200
    assert captured["run_id"] == session_id


def test_process_exports_span_with_session_conversation_id(client, monkeypatch, valid_payload):
    session_id = "bootstrap-process-trace-span"
    monkeypatch.setenv("STUDIO_URL", "http://127.0.0.1:3000")

    from src.core.settings import get_settings

    get_settings.cache_clear()

    with patch("src.agent.session_runtime.agentscope.init"):
        response = client.post(
            "/sessions/bootstrap",
            json={"session_id": session_id, "skills": [], "mcp_servers": []},
        )

    assert response.status_code == 200, response.text

    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    async def _mock_stream_runtime(*args, **kwargs):
        with tracer_provider.get_tracer("tests.trace").start_as_current_span(
            "test-span-bound",
            attributes=_get_common_attributes(),
        ):
            coroutine_task = kwargs["coroutine_task"]
            coroutine_task.close()
            msg = Msg(
                name="agentops",
                content=[{"type": "text", "text": "ok"}],
                role="assistant",
            )
            yield msg, True

    with patch("src.agent.query.ot_trace.get_tracer_provider", return_value=tracer_provider):
        with patch("src.agent.query.stream_printing_messages", _mock_stream_runtime):
            process_response = client.post(
                "/process",
                json={
                    **valid_payload,
                    "session_id": session_id,
                },
            )

    assert process_response.status_code == 200
    spans = exporter.get_finished_spans()
    assert any(json.loads(span.attributes["gen_ai.conversation.id"]) == session_id for span in spans)


def test_bootstrap_with_skills_also_registers_local_runtime_tools(client):
    skill_dir = str((__import__("pathlib").Path(__file__).resolve().parents[1] / "skills" / "hello").resolve())
    response = client.post(
        "/sessions/bootstrap",
        json={
            "session_id": "bootstrap-skill-local-tools-001",
            "skills": [{"skill_dir": skill_dir, "activation_mode": "lazy"}],
            "mcp_servers": [],
        },
    )

    assert response.status_code == 200, response.text
    runtime = get_session_runtime("bootstrap-skill-local-tools-001")
    assert runtime is not None
    assert "read_file" in runtime.toolkit.tools
    assert "edit_file" in runtime.toolkit.tools
    assert "run_local_shell" in runtime.toolkit.tools


def test_process_rejects_agent_config_for_bootstrapped_session(client, valid_payload):
    bootstrap_payload = {"session_id": "bootstrap-process-002", "skills": [], "mcp_servers": []}
    response = client.post("/sessions/bootstrap", json=bootstrap_payload)
    assert response.status_code == 200

    process_payload = {
        **valid_payload,
        "session_id": "bootstrap-process-002",
        "agent_config": {"model_name": "other-model"},
    }
    process_response = client.post("/process", json=process_payload)

    assert process_response.status_code == 200
    events = _parse_sse_events(process_response.text)
    assert any(event.get("status") == "failed" for event in events)


def test_shutdown_closes_active_runtime(client):
    response = client.post(
        "/sessions/bootstrap",
        json={"session_id": "bootstrap-shutdown-001", "skills": [], "mcp_servers": []},
    )
    assert response.status_code == 200

    shutdown_response = client.post("/sessions/bootstrap-shutdown-001/shutdown")
    assert shutdown_response.status_code == 200
    assert shutdown_response.json() == {
        "session_id": "bootstrap-shutdown-001",
        "status": "closed",
    }


def test_shutdown_missing_session_returns_404(client):
    response = client.post("/sessions/unknown-session/shutdown")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tool registry integration tests
# ---------------------------------------------------------------------------


def test_bootstrap_with_tools_registers_requested_tools(client):
    payload = {
        "session_id": "bootstrap-tools-001",
        "tools": [{"name": "get_weather"}, {"name": "calculate"}],
    }
    response = client.post("/sessions/bootstrap", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    tool_names = [t["name"] for t in body["tools"]]
    assert "get_weather" in tool_names
    assert "calculate" in tool_names
    assert len(body["tools"]) == 2
    for t in body["tools"]:
        assert len(t["description"]) > 0


def test_bootstrap_rejects_unknown_tool_name(client):
    payload = {
        "session_id": "bootstrap-tools-bad",
        "tools": [{"name": "get_weather"}, {"name": "nonexistent_tool"}],
    }
    response = client.post("/sessions/bootstrap", json=payload)
    assert response.status_code == 400
    assert "nonexistent_tool" in response.json()["detail"]
    assert "Unknown tool" in response.json()["detail"]


def test_bootstrap_with_empty_tools_succeeds(client):
    payload = {
        "session_id": "bootstrap-tools-empty",
        "tools": [],
    }
    response = client.post("/sessions/bootstrap", json=payload)
    assert response.status_code == 200
    assert response.json()["tools"] == []


def test_bootstrap_with_builtin_tools_registers_agentscope_tools(client):
    payload = {
        "session_id": "bootstrap-builtins-001",
        "tools": [
            {"name": "execute_shell_command"},
            {"name": "view_text_file"},
            {"name": "write_text_file"},
        ],
    }
    response = client.post("/sessions/bootstrap", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    tool_names = [t["name"] for t in body["tools"]]
    assert "execute_shell_command" in tool_names
    assert "view_text_file" in tool_names
    assert "write_text_file" in tool_names


def test_bootstrap_initializes_agentscope_studio_when_configured(client, monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLED", "true")
    monkeypatch.setenv("STUDIO_URL", "http://127.0.0.1:3000")

    from src.core.settings import get_settings

    get_settings.cache_clear()

    with patch("src.agent.session_runtime.agentscope.init") as mock_init:
        response = client.post(
            "/sessions/bootstrap",
            json={"session_id": "bootstrap-studio-001", "skills": [], "mcp_servers": []},
        )

    assert response.status_code == 200, response.text
    mock_init.assert_called_once_with(
        project="agentops",
        studio_url="http://127.0.0.1:3000",
        tracing_url="http://127.0.0.1:3000/v1/traces",
        run_id="bootstrap-studio-001",
    )


def test_bootstrap_skips_agentscope_studio_when_disabled(client, monkeypatch):
    monkeypatch.setenv("STUDIO_URL", "http://127.0.0.1:3000")

    from src.core.settings import get_settings

    get_settings.cache_clear()

    with patch("src.agent.session_runtime.agentscope.init") as mock_init:
        response = client.post(
            "/sessions/bootstrap",
            json={"session_id": "bootstrap-studio-disabled-001", "skills": [], "mcp_servers": []},
        )

    assert response.status_code == 200, response.text
    mock_init.assert_not_called()
