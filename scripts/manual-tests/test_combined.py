"""Test: Agent picks the right capability when tools + MCP + skills coexist.

Single session bootstrapped with ALL three capability types:
  - Local tool: calculate
  - MCP server: weather-mcp (stdio, get_weather)
  - Skill: hello (lazy, structured greeting tool)

The agent receives different natural language requests and must
route each to the correct capability without being told which to use.

Prerequisite: bash scripts/run_service.sh
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from _helpers import check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-combined"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_SERVER_DIR = os.path.join(REPO_ROOT, "mcp-server")
WEATHER_SCRIPT = os.path.join(MCP_SERVER_DIR, "weather_mcp.py")
HELLO_SKILL_DIR = os.path.join(REPO_ROOT, "skills", "hello")


def test_agent_routes_to_tool():
    """Math question → agent should use local calculate tool."""
    result = chat(SESSION_ID, "帮我算一下 15 乘以 27 等于多少？")
    check("405" in result.text, "routed to calculate tool", result.text[:120])


def test_agent_routes_to_mcp():
    """Weather question → agent should use MCP get_weather."""
    result = chat(SESSION_ID, "深圳天气怎么样？")
    check(
        "多云" in result.text or "度" in result.text or "深圳" in result.text,
        "routed to MCP weather tool",
        result.text[:120],
    )


def test_agent_routes_to_skill():
    """Greeting request → agent should activate hello and run script."""
    result = chat(
        SESSION_ID,
        "帮我用 hello skill 和 Charlie 打个招呼，先激活技能再执行。",
    )
    check(
        "Charlie" in result.text or "Hello" in result.text,
        "routed to hello skill script",
        result.text[:150],
    )


def test_agent_switches_between_capabilities():
    """Rapid-fire different requests → agent switches capability each time."""
    r1 = chat(SESSION_ID, "200 除以 8 是多少？")
    check("25" in r1.text, "switch test: calculate invoked", r1.text[:80])

    r2 = chat(SESSION_ID, "深圳现在多少度？")
    check(
        "度" in r2.text or "多云" in r2.text,
        "switch test: MCP weather invoked",
        r2.text[:80],
    )


def main():
    print("=" * 60)
    print("TEST: Combined Tool + MCP + Skill (Agent Routing)")
    print("=" * 60)
    check_service_running()

    body = bootstrap(SESSION_ID, {
        "tools": [{"name": "calculate"}],
        "mcp_servers": [
            {
                "name": "weather-mcp",
                "type": "stdio",
                "command": "uv",
                "args": ["run", WEATHER_SCRIPT, "stdio"],
            },
        ],
        "skills": [
            {
                "skill_dir": HELLO_SKILL_DIR,
                "activation_mode": "lazy",
            }
        ],
    })

    tool_names = [t["name"] for t in body.get("tools", [])]
    mcp_names = [s["name"] for s in body.get("mcp_servers", [])]
    skill_names = [s["name"] for s in body.get("skills", [])]
    check("calculate" in tool_names, "bootstrap: calculate tool registered")
    check("weather-mcp" in mcp_names, "bootstrap: weather-mcp registered")
    check("hello" in skill_names, "bootstrap: hello registered")

    try:
        test_agent_routes_to_tool()
        test_agent_routes_to_mcp()
        test_agent_routes_to_skill()
        test_agent_switches_between_capabilities()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_combined.py")


if __name__ == "__main__":
    main()
