"""Test: Agent invokes MCP tools (HTTP streamable_http transport).

Same tests as stdio but through HTTP MCP servers. This validates
the agent can discover and call tools served over network transport.

Prerequisite:
  - bash scripts/run_service.sh
  - Start MCP HTTP servers in separate terminals:
      uv run ~/mcp-server/weather_mcp.py http           # port 8765
      uv run ~/mcp-server/hiking_spot_mcp.py http        # port 8766
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import httpx
from _helpers import check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-mcp-http"

WEATHER_MCP_URL = "http://127.0.0.1:8765/mcp"
HIKING_MCP_URL = "http://127.0.0.1:8766/mcp"


def check_mcp_http_server(url: str, label: str) -> None:
    try:
        httpx.get(url, timeout=2.0)
    except httpx.ConnectError:
        print(f"ERROR: {label} not reachable at {url}", file=sys.stderr)
        print(f"Start it: uv run ~/mcp-server/{label.replace('-', '_')}.py http", file=sys.stderr)
        sys.exit(1)
    except Exception:
        pass  # Non-200 on GET is fine for MCP endpoints


def test_agent_calls_weather_mcp_http():
    """Weather question → agent calls MCP get_weather over HTTP."""
    result = chat(SESSION_ID, "深圳现在天气怎么样？")
    check(
        "深圳" in result.text and ("天气" in result.text or "度" in result.text or "多云" in result.text),
        "agent invoked HTTP MCP get_weather",
        result.text[:150],
    )


def test_agent_calls_hiking_mcp_http():
    """Hiking question → agent calls MCP recommend_hiking_spots over HTTP."""
    shutdown(SESSION_ID)
    bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "hiking-mcp",
                "type": "http",
                "transport": "streamable_http",
                "url": HIKING_MCP_URL,
            }
        ],
    })

    result = chat(SESSION_ID, "推荐一些深圳适合徒步的地方。")
    check(
        "梧桐山" in result.text or "仙湖" in result.text,
        "agent invoked HTTP MCP recommend_hiking_spots",
        result.text[:150],
    )


def test_agent_picks_right_http_mcp():
    """Two HTTP MCP servers, different questions → agent picks correctly."""
    shutdown(SESSION_ID)
    bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "weather-mcp",
                "type": "http",
                "transport": "streamable_http",
                "url": WEATHER_MCP_URL,
            },
            {
                "name": "hiking-mcp",
                "type": "http",
                "transport": "streamable_http",
                "url": HIKING_MCP_URL,
            },
        ],
    })

    result = chat(SESSION_ID, "深圳天气如何？")
    check(
        "多云" in result.text or "度" in result.text,
        "dual HTTP MCP: agent chose weather for weather question",
        result.text[:150],
    )

    result = chat(SESSION_ID, "深圳有什么好的徒步路线？")
    check(
        "梧桐山" in result.text or "仙湖" in result.text,
        "dual HTTP MCP: agent chose hiking for hiking question",
        result.text[:150],
    )


def main():
    print("=" * 60)
    print("TEST: Agent MCP Invocation (HTTP streamable_http)")
    print("=" * 60)
    check_service_running()
    check_mcp_http_server(WEATHER_MCP_URL, "weather_mcp")
    check_mcp_http_server(HIKING_MCP_URL, "hiking_spot_mcp")

    body = bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "weather-mcp",
                "type": "http",
                "transport": "streamable_http",
                "url": WEATHER_MCP_URL,
            }
        ],
    })
    mcp_names = [s["name"] for s in body.get("mcp_servers", [])]
    check("weather-mcp" in mcp_names, "bootstrap registered weather-mcp (http)")

    try:
        test_agent_calls_weather_mcp_http()
        test_agent_calls_hiking_mcp_http()
        test_agent_picks_right_http_mcp()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_mcp_http.py")


if __name__ == "__main__":
    main()
