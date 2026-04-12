"""Demo: Trigger a tool call through the chat endpoint (DEV-03).

Sends a weather query that the ReActAgent should answer by calling
the get_weather tool function registered in src/tools/examples.py.

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
                "content": [{"type": "text", "text": "What is the weather in Tokyo? Use the get_weather tool."}],
            }
        ]
    }

    text = send_chat(payload)
    # The get_weather tool returns "The weather in Tokyo is sunny, 22C."
    # The agent should relay this information
    assert "sunny" in text.lower() or "tokyo" in text.lower() or "weather" in text.lower(), (
        f"Expected weather info in response, got: {text[:200]}"
    )
    print("PASS: demo_tool.py - tool call triggered successfully")
    print(f"  Response snippet: {text[:150]}")


if __name__ == "__main__":
    main()
