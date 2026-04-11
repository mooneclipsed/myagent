"""Local example MCP server for end-to-end verification.

Provides a single tool: get_time — returns the current date and time.
Start via: python -m src.mcp.server
No network dependencies — uses stdio transport only (D-05).
"""

import asyncio

import mcp.server.stdio
from mcp.server import Server
from mcp.types import TextContent, Tool

server = Server("example-mcp")


@server.call_tool()
async def get_time() -> list[TextContent]:
    """Get the current date and time."""
    from datetime import datetime

    return [TextContent(type="text", text=f"Current time: {datetime.now().isoformat()}")]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_time",
            description="Get the current date and time.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
    ]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
