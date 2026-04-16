#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "mcp",
# ]
# ///
"""Simple weather MCP server (Shenzhen mock response) with stdio/http modes."""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="weather-mcp",
    instructions="Returns a mocked weather response for Shenzhen.",
    host="127.0.0.1",
    port=8765,
)


@mcp.tool()
def get_weather(city: str = "深圳") -> str:
    """Return mocked weather information for Shenzhen."""
    if city.strip() in {"深圳", "shenzhen", "Shenzhen"}:
        return "深圳的天气26度，多云。"
    return f"暂时只支持深圳天气查询；你输入的是：{city}。深圳的天气26度，多云。"


def main() -> None:
    parser = argparse.ArgumentParser(description="Weather MCP server")
    parser.add_argument(
        "transport_pos",
        nargs="?",
        choices=["stdio", "http"],
        help="Transport (positional): stdio or http",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        help="Transport (flag): stdio or http",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (http mode only)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (http mode only)")
    args = parser.parse_args()

    transport = args.transport or args.transport_pos or "stdio"
    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
