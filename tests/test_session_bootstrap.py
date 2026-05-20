"""Tests for session bootstrap MCP runtime lifecycle and routing."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import agentscope
import pytest
from agentscope.model import ChatResponse
from agentscope.message import Msg
from agentscope.tracing._extractor import _get_common_attributes
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentops.application.runtime_service import close_all_session_runtimes, get_active_runtime_profile
from tests.test_chat_stream import _parse_sse_events



async def _mock_stream(*args, **kwargs):
    msg = Msg(
        name="agentops",
        content=[{"type": "text", "text": "ok"}],
        role="assistant",
    )
    yield msg, True


def test_run_agent_stream_does_not_close_owned_coroutine():
    from agentops.adapters.agentscope import runtime

    close_called = False

    class AwaitableStub:
        def __await__(self):
            if False:
                yield None
            return None

        def close(self):
            nonlocal close_called
            close_called = True

    coroutine = AwaitableStub()

    class AgentStub:
        def __call__(self, msgs):
            assert msgs[0].content == "hello"
            return coroutine

    async def _mock_stream_runtime(*args, **kwargs):
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "ok"}],
            role="assistant",
        )
        yield msg, True

    async def _run():
        with patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream_runtime):
            items = []
            async for item in runtime._run_agent_stream(
                AgentStub(),
                [Msg(name="user", content="hello", role="user")],
            ):
                items.append(item)
            return items

    items = asyncio.run(_run())

    assert len(items) == 1
    assert close_called is False


@pytest.fixture(autouse=True)
def _clear_runtime_between_tests():
    import asyncio

    asyncio.run(close_all_session_runtimes())
    yield
    asyncio.run(close_all_session_runtimes())


def test_bootstrap_stdio_session_success(client):
    payload = {
        "mcp_servers": [
            {
                "name": "time-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["-m", "agentops.resources.mcp_servers.example"],
                "env": {"DEMO": "1"},
                "cwd": "/tmp/demo",
            }
        ],
    }

    with patch("agentops.adapters.agentscope.mcp_runtime.StdIOStatefulClient") as mock_stdio:
        mock_client = AsyncMock()
        mock_client.name = "time-mcp"
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_stdio.return_value = mock_client

        response = client.post("/runtimes/init", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "runtime_id" not in body
    assert body["status"] == "ready"
    assert body["mcp_servers"] == [{"name": "time-mcp", "type": "stdio", "transport": None}]
    mock_stdio.assert_called_once_with(
        name="time-mcp",
        command="python",
        args=["-m", "agentops.resources.mcp_servers.example"],
        env={"DEMO": "1"},
        cwd="/tmp/demo",
    )


def test_bootstrap_http_session_success(client):
    payload = {
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

    with patch("agentops.adapters.agentscope.mcp_runtime.HttpStatefulClient") as mock_http:
        mock_client = AsyncMock()
        mock_client.name = "remote-mcp"
        mock_client.is_connected = True
        mock_client.list_tools = AsyncMock(return_value=[])
        mock_http.return_value = mock_client

        response = client.post("/runtimes/init", json=payload)

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
        "mcp_servers": [
            {
                "name": "bad-http",
                "type": "http",
                "transport": "websocket",
                "url": "http://example.com/mcp",
            }
        ],
    }

    response = client.post("/runtimes/init", json=payload)
    assert response.status_code == 422


def test_bootstrap_reloads_when_another_runtime_is_active(client):
    payload_a = {"skills": [], "mcp_servers": []}
    payload_b = {"skills": [], "mcp_servers": []}

    response_a = client.post("/runtimes/init", json=payload_a)
    response_b = client.post("/runtimes/init", json=payload_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert get_active_runtime_profile() is not None


def test_bootstrap_reinit_closes_old_runtime_and_deletes_managed_skills(client, tmp_path):
    from agentops.application.skill_install_service import ManagedSkillState, ManagedSkillSyncResult
    from agentops.capabilities.models import SkillConfig, SkillDownloadSummary

    old_skill_dir = tmp_path / "skills" / ".managed" / "skill_1_v1"
    old_skill_dir.mkdir(parents=True)
    (old_skill_dir / "SKILL.md").write_text("---\nname: old\n---\n", encoding="utf-8")

    def build_old_sync_result():
        return ManagedSkillSyncResult(
            managed_skills={
                (1, 1): ManagedSkillState(
                    skill_id=1,
                    version_id=1,
                    skill_dir=str(old_skill_dir),
                )
            },
        )

    def build_new_sync_result():
        skill_dir = tmp_path / "skills" / ".managed" / "skill_2_v1"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: new\ndescription: new skill\n---\n",
            encoding="utf-8",
        )
        return ManagedSkillSyncResult(
            skills=[SkillConfig(skill_dir=str(skill_dir))],
            summaries=[
                SkillDownloadSummary(
                    skill_id=2,
                    version_id=1,
                    status="installed",
                    skill_dir=str(skill_dir),
                )
            ],
            managed_skills={
                (2, 1): ManagedSkillState(
                    skill_id=2,
                    version_id=1,
                    skill_dir=str(skill_dir),
                )
            },
        )

    with patch("agentops.application.runtime_service.prepare_remote_skills") as sync:
        sync.side_effect = [build_old_sync_result(), build_new_sync_result()]
        response_a = client.post("/runtimes/init", json={})
        response_b = client.post(
            "/runtimes/init",
            json={
                "skills_download_url": "http://skills.example",
                "skill_downloads": [{"skill_id": 2, "version_id": 1}],
            },
        )

    assert response_a.status_code == 200, response_a.text
    assert response_b.status_code == 200, response_b.text
    assert not old_skill_dir.exists()
    assert get_active_runtime_profile() is not None


def test_bootstrap_without_system_prompt_uses_default_prompt(client):
    payload = {"skills": [], "mcp_servers": []}

    response = client.post("/runtimes/init", json=payload)

    assert response.status_code == 200, response.text
    runtime = get_active_runtime_profile()
    assert runtime is not None
    assert runtime.system_prompt is None


def test_bootstrap_reloads_active_runtime(client):
    payload = {"skills": [], "mcp_servers": []}

    response_a = client.post("/runtimes/init", json=payload)
    response_b = client.post("/runtimes/init", json=payload)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert get_active_runtime_profile() is not None


def test_bootstrap_with_blank_system_prompt_uses_default_prompt(client):
    payload = {
        "system_prompt": "   ",
        "skills": [],
        "mcp_servers": [],
    }

    response = client.post("/runtimes/init", json=payload)

    assert response.status_code == 200, response.text
    runtime = get_active_runtime_profile()
    assert runtime is not None
    assert runtime.system_prompt == "   "


def test_build_react_agent_enables_console_output_from_settings(configured_env, clear_settings_cache, monkeypatch):
    monkeypatch.setenv("AGENT_CONSOLE_OUTPUT_ENABLED", "true")

    from agentops.adapters.agentscope.agent_factory import build_react_agent
    from agentops.config.runtime_models import AgentModelConfig
    from agentops.config.settings import get_settings
    from agentscope.memory import InMemoryMemory
    from agentscope.tool import Toolkit

    get_settings.cache_clear()

    agent = build_react_agent(
        resolved_config=AgentModelConfig(
            model_name="test-model",
            api_key="test-key",
            base_url="http://localhost:9999/v1",
        ),
        memory=InMemoryMemory(),
        toolkit=Toolkit(),
    )

    assert agent._disable_console_output is False


def test_bootstrap_stores_memory_compression_config(client):
    payload = {
        "memory_compression": {
            "enabled": True,
            "trigger_tokens": 12345,
            "keep_recent": 7,
        },
        "skills": [],
        "mcp_servers": [],
    }

    response = client.post("/runtimes/init", json=payload)

    assert response.status_code == 200, response.text
    runtime = get_active_runtime_profile()
    assert runtime is not None
    assert runtime.memory_compression is not None
    assert runtime.memory_compression.enabled is True
    assert runtime.memory_compression.trigger_tokens == 12345
    assert runtime.memory_compression.keep_recent == 7


def test_build_react_agent_uses_bootstrap_memory_compression(configured_env, clear_settings_cache):
    from agentscope.memory import InMemoryMemory
    from agentscope.tool import Toolkit

    from agentops.adapters.agentscope.agent_factory import build_react_agent
    from agentops.config.runtime_models import AgentModelConfig, MemoryCompressionConfig

    agent = build_react_agent(
        resolved_config=AgentModelConfig(
            model_name="gpt-4o",
            api_key="test-key",
            base_url="http://localhost:9999/v1",
        ),
        memory=InMemoryMemory(),
        toolkit=Toolkit(),
        memory_compression=MemoryCompressionConfig(
            enabled=True,
            trigger_tokens=12345,
            keep_recent=7,
        ),
    )

    assert agent.compression_config is not None
    assert agent.compression_config.enable is True
    assert agent.compression_config.trigger_threshold == 12345
    assert agent.compression_config.keep_recent == 7
    assert agent.compression_config.agent_token_counter.model_name == "gpt-4o"
    assert agent.compression_config.compression_model.stream is False


def test_compression_fallback_model_wraps_plain_text_summary():
    from agentops.adapters.agentscope.agent_factory import CompressionFallbackModel

    class PlainTextModel:
        model_name = "test-model"
        stream = False

        def __init__(self):
            self.calls = 0

        async def __call__(self, messages, structured_model=None, **kwargs):
            self.calls += 1
            if structured_model is not None:
                raise ValueError("structured output unsupported")
            return ChatResponse(
                content=[{"type": "text", "text": "## Continuation Summary\nRemember ALPHA."}],
                metadata=None,
            )

    async def _run():
        base_model = PlainTextModel()
        model = CompressionFallbackModel(base_model)
        response = await model(
            [{"role": "user", "content": "summarize"}],
            structured_model=object,
        )
        assert base_model.calls == 2
        assert response.metadata["task_overview"].startswith("## Continuation Summary")
        assert "ALPHA" in response.metadata["context_to_preserve"]

    asyncio.run(_run())


def test_bootstrap_memory_compression_overrides_env_defaults(client, monkeypatch):
    monkeypatch.setenv("AGENT_MEMORY_COMPRESSION_ENABLED", "true")
    monkeypatch.setenv("AGENT_MEMORY_COMPRESSION_TRIGGER_TOKENS", "60000")
    monkeypatch.setenv("AGENT_MEMORY_COMPRESSION_KEEP_RECENT", "8")

    from agentops.config.settings import get_settings

    get_settings.cache_clear()

    response = client.post(
        "/runtimes/init",
        json={
            "memory_compression": {
                "enabled": False,
                "trigger_tokens": 1000,
                "keep_recent": 2,
            },
            "skills": [],
            "mcp_servers": [],
        },
    )

    assert response.status_code == 200, response.text
    runtime = get_active_runtime_profile()
    assert runtime is not None
    assert runtime.memory_compression is not None
    assert runtime.memory_compression.enabled is False


def test_thinking_formatter_warning_filter_is_installed_on_agentscope_logger():
    import logging
    from agentops.adapters.agentscope.tracing import _AgentScopeThinkingWarningFilter

    logger = logging.getLogger("as")

    assert any(isinstance(item, _AgentScopeThinkingWarningFilter) for item in logger.filters)


def test_bootstrap_failure_rolls_back_connected_clients(client):
    payload = {
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
        "agentops.adapters.agentscope.mcp_runtime.StdIOStatefulClient",
        side_effect=[first_client, second_client],
    ):
        response = client.post("/runtimes/init", json=payload)

    assert response.status_code == 502
    assert "Failed to initialize MCP server 'second' (stdio)." == response.json()["detail"]
    first_client.close.assert_awaited_once_with(ignore_errors=True)


def test_chat_uses_bootstrapped_runtime_profile_with_session_memory(client, valid_payload):
    bootstrap_payload = {"skills": [], "mcp_servers": []}
    response = client.post("/runtimes/init", json=bootstrap_payload)
    assert response.status_code == 200

    runtime = get_active_runtime_profile()
    assert runtime is not None

    async def _mock_stream_runtime(*args, **kwargs):
        agent = kwargs["agents"][0]
        assert agent.toolkit is runtime.toolkit
        assert agent.memory is not None
        coroutine_task = kwargs["coroutine_task"]
        assert coroutine_task.cr_code.co_name == "__call__"
        coroutine_task.close()
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "ok"}],
            role="assistant",
        )
        yield msg, True

    with patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream_runtime):
        chat_payload = {
            **valid_payload,
            "session_id": "conversation-chat-001",
        }
        chat_response = client.post("/chat", json=chat_payload)

    assert chat_response.status_code == 200
    events = _parse_sse_events(chat_response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses


def test_chat_passes_runtime_memory_compression_to_agent(client, valid_payload):
    response = client.post(
        "/runtimes/init",
        json={
            "memory_compression": {
                "enabled": True,
                "trigger_tokens": 12345,
                "keep_recent": 7,
            },
            "skills": [],
            "mcp_servers": [],
        },
    )
    assert response.status_code == 200, response.text

    async def _mock_stream_runtime(*args, **kwargs):
        coroutine_task = kwargs["coroutine_task"]
        coroutine_task.close()
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "ok"}],
            role="assistant",
        )
        yield msg, True

    with (
        patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream_runtime),
        patch("agentops.adapters.agentscope.agent_factory.build_react_agent", wraps=__import__("agentops.adapters.agentscope.agent_factory", fromlist=["build_react_agent"]).build_react_agent) as mock_build,
    ):
        chat_response = client.post(
            "/chat",
            json={
                **valid_payload,
                "session_id": "conversation-chat-compression",
            },
        )

    assert chat_response.status_code == 200
    build_kwargs = mock_build.call_args.kwargs
    assert build_kwargs["memory_compression"].enabled is True
    assert build_kwargs["memory_compression"].trigger_tokens == 12345
    assert build_kwargs["memory_compression"].keep_recent == 7


def test_chat_binds_agentscope_request_context_for_bootstrapped_session(client, valid_payload):
    session_id = "bootstrap-chat-trace-bind"
    response = client.post("/runtimes/init", json={"skills": [], "mcp_servers": []})
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

    with patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream_runtime):
        chat_response = client.post(
            "/chat",
            json={
                **valid_payload,
                "session_id": session_id,
            },
        )

    assert chat_response.status_code == 200
    assert captured["run_id"] == session_id


def test_chat_exports_span_with_session_conversation_id(client, monkeypatch, valid_payload):
    session_id = "bootstrap-chat-trace-span"
    monkeypatch.setenv("STUDIO_URL", "http://127.0.0.1:3000")

    from agentops.config.settings import get_settings

    get_settings.cache_clear()

    with patch("agentops.adapters.agentscope.runtime.agentscope.init"):
        response = client.post(
            "/runtimes/init",
            json={"skills": [], "mcp_servers": []},
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

    with patch("agentops.adapters.agentscope.tracing.ot_trace.get_tracer_provider", return_value=tracer_provider):
        with patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream_runtime):
            chat_response = client.post(
                "/chat",
                json={
                    **valid_payload,
                    "session_id": session_id,
                },
            )

    assert chat_response.status_code == 200
    spans = exporter.get_finished_spans()
    assert any(json.loads(span.attributes["gen_ai.conversation.id"]) == session_id for span in spans)


def test_bootstrap_with_skills_also_registers_local_runtime_tools(client):
    skill_dir = str((__import__("pathlib").Path(__file__).resolve().parents[1] / "skills" / "hello").resolve())
    response = client.post(
        "/runtimes/init",
        json={
            "skills": [{"skill_dir": skill_dir}],
            "mcp_servers": [],
        },
    )

    assert response.status_code == 200, response.text
    runtime = get_active_runtime_profile()
    assert runtime is not None
    assert "read_file" in runtime.toolkit.tools
    assert "edit_file" in runtime.toolkit.tools
    assert "run_local_shell" in runtime.toolkit.tools


def test_bootstrap_downloads_remote_skills_and_loads_successes(client, tmp_path):
    skill_dir = tmp_path / "skills" / ".managed" / "skill_1_v1"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: downloaded-skill\ndescription: downloaded\n---\n",
        encoding="utf-8",
    )

    def fake_sync(**kwargs):
        from agentops.application.skill_install_service import (
            ManagedSkillState,
            ManagedSkillSyncResult,
        )
        from agentops.capabilities.models import SkillConfig, SkillDownloadSummary

        assert kwargs["skills_download_url"] == "http://skills.example"
        return ManagedSkillSyncResult(
            skills=[SkillConfig(skill_dir=str(skill_dir))],
            summaries=[
                SkillDownloadSummary(
                    skill_id=1,
                    version_id=1,
                    status="installed",
                    skill_dir=str(skill_dir),
                    zip_path=str(tmp_path / "skills" / ".downloads" / "skill_1_v1.zip"),
                )
            ],
            managed_skills={
                (1, 1): ManagedSkillState(
                    skill_id=1,
                    version_id=1,
                    skill_dir=str(skill_dir),
                )
            },
        )

    with patch("agentops.application.runtime_service.prepare_remote_skills", fake_sync):
        response = client.post(
            "/runtimes/init",
            json={
                "skills_download_url": "http://skills.example",
                "skill_downloads": [{"skill_id": 1, "version_id": 1}],
                "skills": [],
                "mcp_servers": [],
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["skills"] == [{"name": "downloaded-skill", "structured_tools": []}]
    assert body["skill_downloads"][0]["status"] == "installed"


def test_bootstrap_download_failure_fails_initialization(client):
    def fake_sync(**kwargs):
        from agentops.application.skill_install_service import ManagedSkillSyncResult
        from agentops.capabilities.models import SkillDownloadSummary

        return ManagedSkillSyncResult(
            summaries=[
                SkillDownloadSummary(
                    skill_id=1,
                    version_id=1,
                    status="failed",
                    error="download failed",
                )
            ],
        )

    with patch("agentops.application.runtime_service.prepare_remote_skills", fake_sync):
        response = client.post(
            "/runtimes/init",
            json={
                "skills_download_url": "http://skills.example",
                "skill_downloads": [{"skill_id": 1, "version_id": 1}],
                "skills": [],
                "mcp_servers": [],
            },
        )

    assert response.status_code == 502, response.text
    assert "Remote skill download failed" in response.json()["detail"]
    assert get_active_runtime_profile() is None


def test_chat_rejects_model_config_for_bootstrapped_session(client, valid_payload):
    bootstrap_payload = {"skills": [], "mcp_servers": []}
    response = client.post("/runtimes/init", json=bootstrap_payload)
    assert response.status_code == 200

    chat_payload = {
        **valid_payload,
        "session_id": "conversation-chat-002",
        "model_config": {"model_name": "other-model"},
    }
    chat_response = client.post("/chat", json=chat_payload)

    assert chat_response.status_code == 200
    events = _parse_sse_events(chat_response.text)
    assert any(event.get("status") == "failed" for event in events)


def test_chat_without_session_id_uses_active_runtime_context(client, valid_payload):
    bootstrap_payload = {"skills": [], "mcp_servers": []}
    response = client.post("/runtimes/init", json=bootstrap_payload)
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

    with patch("agentops.adapters.agentscope.runtime.stream_printing_messages", _mock_stream_runtime):
        chat_response = client.post(
            "/chat",
            json=valid_payload,
        )

    assert chat_response.status_code == 200
    events = _parse_sse_events(chat_response.text)
    response_session_ids = [event.get("session_id") for event in events if event.get("session_id")]
    assert response_session_ids
    assert captured["run_id"]


def test_same_session_id_streams_are_serialized():
    from agentops.application import chat_service

    entered = asyncio.Event()
    release_first = asyncio.Event()
    events: list[str] = []

    async def _mock_runtime_stream(*args, **kwargs):
        call_number = events.count("enter") + 1
        events.append("enter")
        if call_number == 1:
            entered.set()
            await release_first.wait()
        events.append("exit")
        msg = Msg(
            name="agentops",
            content=[{"type": "text", "text": "ok"}],
            role="assistant",
        )
        yield msg, True

    class Request:
        session_id = "conversation-lock-001"
        model_config = None

    msgs = [Msg(name="user", content="hello", role="user")]
    request = Request()

    async def _collect_stream():
        items = []
        async for item in chat_service.chat_service(None, msgs, request=request):
            items.append(item)
        return items

    async def _run():
        class Runtime:
            pass

        with (
            patch("agentops.application.chat_service.get_active_runtime_profile", return_value=Runtime()),
            patch("agentops.application.chat_service._runtime_adapter.stream_chat", _mock_runtime_stream),
        ):
            first = asyncio.create_task(_collect_stream())
            await entered.wait()
            second = asyncio.create_task(_collect_stream())
            await asyncio.sleep(0)
            assert events == ["enter"]
            release_first.set()
            await asyncio.gather(first, second)

    asyncio.run(_run())

    assert events == ["enter", "exit", "enter", "exit"]


# ---------------------------------------------------------------------------
# Tool registry integration tests
# ---------------------------------------------------------------------------


def test_bootstrap_with_tools_registers_requested_tools(client):
    payload = {
        "tools": [{"name": "get_weather"}, {"name": "calculate"}],
    }
    response = client.post("/runtimes/init", json=payload)
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
        "tools": [{"name": "get_weather"}, {"name": "nonexistent_tool"}],
    }
    response = client.post("/runtimes/init", json=payload)
    assert response.status_code == 400
    assert "nonexistent_tool" in response.json()["detail"]
    assert "Unknown tool" in response.json()["detail"]


def test_bootstrap_with_empty_tools_succeeds(client):
    payload = {
        "tools": [],
    }
    response = client.post("/runtimes/init", json=payload)
    assert response.status_code == 200
    assert response.json()["tools"] == []


def test_bootstrap_with_builtin_tools_registers_agentscope_tools(client):
    payload = {
        "tools": [
            {"name": "execute_shell_command"},
            {"name": "view_text_file"},
            {"name": "write_text_file"},
        ],
    }
    response = client.post("/runtimes/init", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    tool_names = [t["name"] for t in body["tools"]]
    assert "execute_shell_command" in tool_names
    assert "view_text_file" in tool_names
    assert "write_text_file" in tool_names


def test_bootstrap_initializes_agentscope_studio_when_configured(client, monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLED", "true")
    monkeypatch.setenv("STUDIO_URL", "http://127.0.0.1:3000")

    from agentops.config.settings import get_settings

    get_settings.cache_clear()

    with patch("agentops.adapters.agentscope.runtime.agentscope.init") as mock_init:
        response = client.post(
            "/runtimes/init",
            json={"skills": [], "mcp_servers": []},
        )

    assert response.status_code == 200, response.text
    mock_init.assert_called_once_with(
        project="agentops",
        studio_url="http://127.0.0.1:3000",
        tracing_url="http://127.0.0.1:3000/v1/traces",
        run_id="agentops-runtime",
    )


def test_bootstrap_skips_agentscope_studio_when_disabled(client, monkeypatch):
    monkeypatch.setenv("STUDIO_URL", "http://127.0.0.1:3000")

    from agentops.config.settings import get_settings

    get_settings.cache_clear()

    with patch("agentops.adapters.agentscope.runtime.agentscope.init") as mock_init:
        response = client.post(
            "/runtimes/init",
            json={"skills": [], "mcp_servers": []},
        )

    assert response.status_code == 200, response.text
    mock_init.assert_not_called()
