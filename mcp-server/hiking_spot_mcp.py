#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "mcp",
# ]
# ///
"""Simple hiking recommendation MCP server with stdio/http modes."""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="hiking-spot-mcp",
    instructions="Returns a mocked hiking recommendation in Shenzhen.",
    host="127.0.0.1",
    port=8766,
)


@mcp.tool()
def recommend_hiking_spots(city: str = "深圳") -> str:
    """Return mocked hiking recommendations for Shenzhen."""
    if city.strip() in {"深圳", "shenzhen", "Shenzhen"}:
        return "推荐徒步景点：梧桐山，仙湖庙。"
    return f"暂时只支持深圳徒步推荐；你输入的是：{city}。推荐徒步景点：梧桐山，仙湖庙。"


def main() -> None:
    parser = argparse.ArgumentParser(description="Hiking spot MCP server")
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
    parser.add_argument("--port", type=int, default=8766, help="HTTP port (http mode only)")
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
