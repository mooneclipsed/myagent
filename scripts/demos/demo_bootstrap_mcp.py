"""Demo: Bootstrap a session-scoped stdio MCP runtime, chat, then shutdown."""

import re

import httpx

from _helpers import SERVICE_URL, check_service_running, send_chat

ISO_TIME_RE = re.compile(r"Current time:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def main():
    check_service_running()

    bootstrap_payload = {
        "session_id": "demo-bootstrap-mcp",
        "mcp_servers": [
            {
                "name": "time-mcp",
                "type": "stdio",
                "command": "python",
                "args": ["-m", "src.mcp.server"],
            }
        ],
    }

    bootstrap_response = httpx.post(
        f"{SERVICE_URL}/sessions/bootstrap",
        json=bootstrap_payload,
        timeout=30.0,
    )
    assert bootstrap_response.status_code == 200, (
        f"Expected bootstrap 200, got {bootstrap_response.status_code}: {bootstrap_response.text[:200]}"
    )
    session_id = bootstrap_response.json()["session_id"]

    text = send_chat(
        {
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is the current time? Use the get_time MCP tool and return the raw tool result.",
                        }
                    ],
                }
            ],
            "session_id": session_id,
        }
    )
    assert "Current time:" in text, f"Expected raw MCP tool prefix, got: {text[:200]}"
    assert ISO_TIME_RE.search(text), f"Expected ISO-like timestamp, got: {text[:200]}"

    shutdown_response = httpx.post(
        f"{SERVICE_URL}/sessions/{session_id}/shutdown",
        timeout=30.0,
    )
    assert shutdown_response.status_code == 200, (
        f"Expected shutdown 200, got {shutdown_response.status_code}: {shutdown_response.text[:200]}"
    )
    print("PASS: demo_bootstrap_mcp.py - bootstrap -> process -> shutdown succeeded")
    print(f"  Response snippet: {text[:150]}")


if __name__ == "__main__":
    main()
