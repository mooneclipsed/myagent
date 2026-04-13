"""Demo: Trigger an MCP tool call through the chat endpoint (DEV-03).

Sends a time query that the ReActAgent should answer by calling
the get_time MCP tool from src/mcp/server.py.

Prerequisite: Service running at http://127.0.0.1:8000
Start with: bash scripts/run_service.sh
"""

import re
import sys
from _helpers import check_service_running, send_chat


ISO_TIME_RE = re.compile(r"Current time:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def main():
    check_service_running()

    payload = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "What is the current time? Use the get_time MCP tool and return the raw tool result."}],
            }
        ]
    }

    text = send_chat(payload)
    assert "Current time:" in text, (
        f"Expected raw MCP tool prefix in response, got: {text[:200]}"
    )
    assert ISO_TIME_RE.search(text), (
        f"Expected ISO-like timestamp in response, got: {text[:200]}"
    )
    print("PASS: demo_mcp.py - MCP tool call triggered successfully")
    print(f"  Response snippet: {text[:150]}")


if __name__ == "__main__":
    main()
