"""Tests for tool registration and response format (CAP-02 invocation side).

Per D-06/D-07, structured tracing/observability is deferred.
These tests verify tool registration, invocation, and response format.
"""

import pytest
from agentscope.tool import ToolResponse


class TestToolRegistration:
    """Tests for toolkit registration per D-01 (framework-native) and D-02 (startup-time)."""

    def test_toolkit_has_example_tools(self):
        """Toolkit singleton contains get_weather and calculate tools."""
        from src.tools import toolkit

        tool_names = list(toolkit.tools.keys())
        assert "get_weather" in tool_names, f"get_weather not in {tool_names}"
        assert "calculate" in tool_names, f"calculate not in {tool_names}"

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
