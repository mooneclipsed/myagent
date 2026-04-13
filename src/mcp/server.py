"""Local example MCP server for end-to-end verification.

Provides a single tool: get_time — returns the current date and time.
Start via: python -m src.mcp.server
No network dependencies — uses stdio transport only (D-05).
"""

from datetime import datetime

from mcp.server.fastmcp import FastMCP

server = FastMCP("example-mcp")


@server.tool(description="Get the current date and time.")
def get_time() -> str:
    """Get the current date and time."""
    return f"Current time: {datetime.now().isoformat()}"


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
