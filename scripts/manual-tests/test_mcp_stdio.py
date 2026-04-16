"""Test: Agent invokes MCP tools (stdio transport) during conversation.

The agent is bootstrapped with external MCP servers via stdio.
Natural language questions trigger the agent to discover and call
the MCP-provided tools (get_weather, recommend_hiking_spots).

Prerequisite:
  - bash scripts/run_service.sh
  - uv in PATH (agent service spawns MCP subprocesses)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from _helpers import check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-mcp-stdio"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_SERVER_DIR = os.path.join(REPO_ROOT, "mcp-server")
WEATHER_SCRIPT = os.path.join(MCP_SERVER_DIR, "weather_mcp.py")
HIKING_SCRIPT = os.path.join(MCP_SERVER_DIR, "hiking_spot_mcp.py")


def test_agent_calls_weather_mcp():
    """Weather question → agent should discover and call MCP get_weather."""
    result = chat(SESSION_ID, "深圳现在天气怎么样？")
    check(
        "深圳" in result.text and ("天气" in result.text or "度" in result.text or "多云" in result.text),
        "agent invoked MCP get_weather for weather question",
        result.text[:150],
    )


def test_agent_calls_hiking_mcp():
    """Hiking question → agent should discover and call MCP recommend_hiking_spots."""
    shutdown(SESSION_ID)
    bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "hiking-mcp",
                "type": "stdio",
                "command": "uv",
                "args": ["run", HIKING_SCRIPT, "stdio"],
            }
        ],
    })

    result = chat(SESSION_ID, "推荐一些深圳适合徒步的地方。")
    check(
        "梧桐山" in result.text or "仙湖" in result.text,
        "agent invoked MCP recommend_hiking_spots for hiking question",
        result.text[:150],
    )


def test_agent_picks_right_mcp_tool():
    """Two MCP servers registered, different questions → agent picks correctly."""
    shutdown(SESSION_ID)
    bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "weather-mcp",
                "type": "stdio",
                "command": "uv",
                "args": ["run", WEATHER_SCRIPT, "stdio"],
            },
            {
                "name": "hiking-mcp",
                "type": "stdio",
                "command": "uv",
                "args": ["run", HIKING_SCRIPT, "stdio"],
            },
        ],
    })

    result = chat(SESSION_ID, "深圳天气如何？")
    check(
        "多云" in result.text or "度" in result.text,
        "dual MCP: agent chose weather-mcp for weather question",
        result.text[:150],
    )

    result = chat(SESSION_ID, "深圳有什么好的徒步路线？")
    check(
        "梧桐山" in result.text or "仙湖" in result.text,
        "dual MCP: agent chose hiking-mcp for hiking question",
        result.text[:150],
    )


def main():
    print("=" * 60)
    print("TEST: Agent MCP Invocation (stdio)")
    print("=" * 60)
    print(f"  MCP server dir: {MCP_SERVER_DIR}")
    check_service_running()

    body = bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "weather-mcp",
                "type": "stdio",
                "command": "uv",
                "args": ["run", WEATHER_SCRIPT, "stdio"],
            }
        ],
    })
    mcp_names = [s["name"] for s in body.get("mcp_servers", [])]
    check("weather-mcp" in mcp_names, "bootstrap registered weather-mcp (stdio)")

    try:
        test_agent_calls_weather_mcp()
        test_agent_calls_hiking_mcp()
        test_agent_picks_right_mcp_tool()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_mcp_stdio.py")


if __name__ == "__main__":
    main()
