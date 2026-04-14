"""Request-scoped agent configuration tests.

Validates config override, .env fallback, partial override, instance
isolation, config trace logging (without api_key exposure), and extra
field rejection. Covers CORE-02, CORE-03, D-02, D-06, T-03-02.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
from agentscope.message import Msg
from pydantic import ValidationError

from src.core.config import AgentConfig, resolve_effective_config


# ---------------------------------------------------------------------------
# Mock stream helper -- yields one chunk so the async handler completes
# ---------------------------------------------------------------------------


async def _mock_stream(*args, **kwargs):
    msg = Msg(
        name="agentops",
        content=[{"type": "text", "text": "ok"}],
        role="assistant",
    )
    yield msg, True


# ---------------------------------------------------------------------------
# Test 1: Request with agent_config uses override values (CORE-02)
# ---------------------------------------------------------------------------


def test_config_override_applied(client, config_override_payload):
    mock_model = MagicMock()

    with (
        patch("src.agent.session_runtime.OpenAIChatModel", mock_model),
        patch("src.agent.query.stream_printing_messages", _mock_stream),
    ):
        response = client.post("/process", json=config_override_payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    mock_model.assert_called_once_with(
        model_name="gpt-4o",
        api_key="sk-override-key",
        client_kwargs={"base_url": "http://custom-api.example.com/v1"},
        stream=True,
    )


# ---------------------------------------------------------------------------
# Test 2: Request without agent_config falls back to .env defaults
# ---------------------------------------------------------------------------


def test_config_fallback_to_env(client, valid_payload):
    mock_model = MagicMock()

    with (
        patch("src.agent.session_runtime.OpenAIChatModel", mock_model),
        patch("src.agent.query.stream_printing_messages", _mock_stream),
    ):
        response = client.post("/process", json=valid_payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    mock_model.assert_called_once_with(
        model_name="test-model",
        api_key="test-key",
        client_kwargs={"base_url": "http://localhost:9999/v1"},
        stream=True,
    )


# ---------------------------------------------------------------------------
# Test 3: Partial override keeps unset fields from .env (D-02)
# ---------------------------------------------------------------------------


def test_partial_override(client, valid_payload):
    mock_model = MagicMock()
    payload = {
        **valid_payload,
        "agent_config": {"model_name": "gpt-4o-mini"},
    }

    with (
        patch("src.agent.session_runtime.OpenAIChatModel", mock_model),
        patch("src.agent.query.stream_printing_messages", _mock_stream),
    ):
        response = client.post("/process", json=payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    mock_model.assert_called_once_with(
        model_name="gpt-4o-mini",
        api_key="test-key",
        client_kwargs={"base_url": "http://localhost:9999/v1"},
        stream=True,
    )


# ---------------------------------------------------------------------------
# Test 4: Sequential requests with different configs are isolated (CORE-03)
# ---------------------------------------------------------------------------


def test_different_configs_sequential(client, valid_payload):
    mock_model = MagicMock()

    payload_a = {**valid_payload, "agent_config": {"model_name": "model-a"}}
    payload_b = {**valid_payload, "agent_config": {"model_name": "model-b"}}

    with (
        patch("src.agent.session_runtime.OpenAIChatModel", mock_model),
        patch("src.agent.query.stream_printing_messages", _mock_stream),
    ):
        response_a = client.post("/process", json=payload_a)
        response_b = client.post("/process", json=payload_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    calls = mock_model.call_args_list
    assert len(calls) == 2, f"Expected 2 OpenAIChatModel calls, got {len(calls)}"

    first_kwargs = calls[0].kwargs if calls[0].kwargs else calls[0][1]
    second_kwargs = calls[1].kwargs if calls[1].kwargs else calls[1][1]

    assert first_kwargs.get("model_name") == "model-a", (
        f"First call should use model-a, got {first_kwargs.get('model_name')}"
    )
    assert second_kwargs.get("model_name") == "model-b", (
        f"Second call should use model-b, got {second_kwargs.get('model_name')}"
    )


# ---------------------------------------------------------------------------
# Test 5: Config trace logging emits source and model, never api_key (D-06)
# ---------------------------------------------------------------------------


def test_config_trace_logging(client, config_override_payload, caplog):
    mock_model = MagicMock()

    with (
        patch("src.agent.session_runtime.OpenAIChatModel", mock_model),
        patch("src.agent.query.stream_printing_messages", _mock_stream),
        caplog.at_level(logging.INFO, logger="src.core.config"),
    ):
        response = client.post("/process", json=config_override_payload)

    assert response.status_code == 200

    log_messages = [rec.message for rec in caplog.records]

    # Assert config trace log is emitted
    assert any("effective config" in msg for msg in log_messages), (
        f"Expected 'effective config' in logs, got: {log_messages}"
    )

    # Assert model_name appears in logs
    assert any("gpt-4o" in msg for msg in log_messages), (
        f"Expected model_name 'gpt-4o' in logs, got: {log_messages}"
    )

    # Assert source is logged as "request"
    assert any("source=request" in msg for msg in log_messages), (
        f"Expected 'source=request' in logs, got: {log_messages}"
    )

    # Assert api_key VALUE is NOT present in any log message (T-03-01)
    assert not any("sk-override-key" in msg for msg in log_messages), (
        "api_key value must NOT appear in log output"
    )


# ---------------------------------------------------------------------------
# Test 6: AgentConfig rejects extra fields with ValidationError (T-03-02)
# ---------------------------------------------------------------------------


def test_agent_config_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AgentConfig(model_name="test", unknown_field="bad")
