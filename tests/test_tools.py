"""Tests for tool registration, registry, and response format (CAP-02 invocation side).

Per D-06/D-07, structured tracing/observability is deferred.
These tests verify tool registration, invocation, and response format.
"""

import pytest
from agentscope.tool import Toolkit, ToolResponse

from src.core.config import ToolConfig
from src.tools import TOOL_REGISTRY, ToolRegistryError, register_configured_tools


class TestToolRegistration:
    """Tests for toolkit registration per D-01 (framework-native) and D-02 (startup-time)."""

    def test_toolkit_has_example_tools(self):
        """Toolkit singleton contains get_weather and calculate tools."""
        from src.tools import toolkit

        tool_names = list(toolkit.tools.keys())
        assert "get_weather" in tool_names, f"get_weather not in {tool_names}"
        assert "calculate" in tool_names, f"calculate not in {tool_names}"
        assert "run_platform_report" in tool_names, f"run_platform_report not in {tool_names}"

    def test_toolkit_is_singleton(self):
        """Toolkit imported from different paths is the same object (D-02: shared)."""
        from src.tools import toolkit as t1
        from src.tools import toolkit as t2

        assert t1 is t2

    def test_toolkit_shared_across_imports(self):
        """Toolkit shared across requests — no per-request isolation needed."""
        from src.tools import toolkit

        initial_count = len(toolkit.tools)
        assert initial_count >= 2, f"Expected at least 2 tools, got {initial_count}"


class TestToolResponseFormat:
    """Tests verifying tool functions return correct ToolResponse format."""

    def test_get_weather_returns_tool_response(self):
        """get_weather returns ToolResponse (not plain string/dict)."""
        from src.tools.examples import get_weather

        result = get_weather(city="London")
        assert isinstance(result, ToolResponse)
        assert len(result.content) > 0
        assert isinstance(result.content[0], dict)
        assert result.content[0]["type"] == "text"
        assert "London" in result.content[0]["text"]

    def test_get_weather_is_deterministic(self):
        """Same input produces same output (no external API calls)."""
        from src.tools.examples import get_weather

        r1 = get_weather(city="Tokyo")
        r2 = get_weather(city="Tokyo")
        assert r1.content[0]["text"] == r2.content[0]["text"]

    def test_calculate_add(self):
        """calculate performs addition correctly."""
        from src.tools.examples import calculate

        result = calculate(operation="add", a=2, b=3)
        assert isinstance(result, ToolResponse)
        assert "5" in result.content[0]["text"]

    def test_calculate_divide_by_zero(self):
        """calculate handles division by zero gracefully."""
        from src.tools.examples import calculate

        result = calculate(operation="divide", a=10, b=0)
        assert isinstance(result, ToolResponse)
        assert "Error" in result.content[0]["text"] or "division by zero" in result.content[0]["text"]

    def test_calculate_unknown_operation(self):
        """calculate handles unknown operations gracefully."""
        from src.tools.examples import calculate

        result = calculate(operation="modulo", a=10, b=3)
        assert isinstance(result, ToolResponse)
        assert "Error" in result.content[0]["text"] or "unknown" in result.content[0]["text"]

    def test_run_platform_report_returns_script_output(self):
        """run_platform_report executes the bundled script and returns raw stdout."""
        from src.tools.examples import run_platform_report

        result = run_platform_report()
        assert isinstance(result, ToolResponse)
        text = result.content[0]["text"]
        assert "EXAMPLE_SKILL_SCRIPT_OK" in text
        assert "platform=AgentScope Validation Platform" in text
        assert "backends=json,redis" in text


class TestToolRegistry:
    """Tests for name-based tool registry and register_configured_tools."""

    def test_registry_contains_all_example_tools(self):
        assert "get_weather" in TOOL_REGISTRY
        assert "calculate" in TOOL_REGISTRY
        assert "run_platform_report" in TOOL_REGISTRY
        assert "summarize_platform_callable" in TOOL_REGISTRY

    def test_registry_values_are_callable(self):
        for name, func in TOOL_REGISTRY.items():
            assert callable(func), f"{name} is not callable"

    def test_register_configured_tools_adds_to_toolkit(self):
        tk = Toolkit()
        configs = [ToolConfig(name="get_weather"), ToolConfig(name="calculate")]
        summaries = register_configured_tools(tk, configs)
        assert len(summaries) == 2
        assert summaries[0].name == "get_weather"
        assert summaries[1].name == "calculate"
        assert len(summaries[0].description) > 0

    def test_register_configured_tools_empty_list(self):
        tk = Toolkit()
        summaries = register_configured_tools(tk, [])
        assert summaries == []

    def test_register_configured_tools_rejects_unknown(self):
        tk = Toolkit()
        with pytest.raises(ToolRegistryError, match="nonexistent"):
            register_configured_tools(tk, [ToolConfig(name="nonexistent")])
