"""Test: Agent autonomously invokes local tools during conversation.

The agent receives natural language questions and must DECIDE to use
the registered tools. We verify the agent actually called the tool
by checking for tool-specific content in the response.

Prerequisite: bash scripts/run_service.sh
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import httpx
from _helpers import SERVICE_URL, DEFAULT_TIMEOUT, check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-tools"


def test_agent_calls_weather_tool():
    """Natural question about weather → agent should invoke get_weather."""
    result = chat(SESSION_ID, "深圳今天天气怎么样？")
    # The get_weather tool returns deterministic text containing the city name
    check("深圳" in result.text, "agent used get_weather for weather question", result.text)


def test_agent_calls_calculate_tool():
    """Math question → agent should invoke calculate."""
    result = chat(SESSION_ID, "帮我算一下 123 加 456 等于多少？")
    check("579" in result.text, "agent used calculate for math question", result.text)


def test_agent_picks_right_tool():
    """Two tools available, different questions → agent picks the correct one each time."""
    result = chat(SESSION_ID, "北京天气如何？")
    check("北京" in result.text, "agent chose weather tool for city question", result.text)

    result = chat(SESSION_ID, "100 除以 4 是多少？")
    check("25" in result.text, "agent chose calculate tool for division", result.text)


def main():
    print("=" * 60)
    print("TEST: Agent Tool Invocation")
    print("=" * 60)
    check_service_running()

    body = bootstrap(SESSION_ID, {
        "tools": [{"name": "get_weather"}, {"name": "calculate"}],
    })
    tool_names = [t["name"] for t in body.get("tools", [])]
    check(len(tool_names) == 2, "bootstrap registered 2 tools", str(tool_names))

    try:
        test_agent_calls_weather_tool()
        test_agent_calls_calculate_tool()
        test_agent_picks_right_tool()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_tools.py")


if __name__ == "__main__":
    main()
