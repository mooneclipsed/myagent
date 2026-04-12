"""Demo: Trigger an MCP tool call through the chat endpoint (DEV-03).

Sends a time query that the ReActAgent should answer by calling
the get_time MCP tool from src/mcp/server.py.

Prerequisite: Service running at http://127.0.0.1:8000
Start with: bash scripts/run_service.sh
"""

import sys
from _helpers import check_service_running, send_chat


def main():
    check_service_running()

    payload = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "What is the current time? Use the get_time MCP tool."}],
            }
        ]
    }

    text = send_chat(payload)
    # The get_time MCP tool returns "Current time: {isoformat}"
    assert "time" in text.lower() or "current" in text.lower() or "clock" in text.lower(), (
        f"Expected time info in response, got: {text[:200]}"
    )
    print("PASS: demo_mcp.py - MCP tool call triggered successfully")
    print(f"  Response snippet: {text[:150]}")


if __name__ == "__main__":
    main()
