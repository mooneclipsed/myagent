"""Demo: Verify skill-guided script execution through the chat endpoint.

Sends a query that instructs the assistant to use the example skill's
bundled script workflow. The response must contain the script marker and
raw report lines, proving the tool-backed script path was actually used.

Prerequisite: Service running at http://127.0.0.1:8000
Start with: bash scripts/run_service.sh
"""

import sys
from _helpers import check_service_running, send_chat


EXPECTED_LINES = [
    "EXAMPLE_SKILL_SCRIPT_OK",
    "platform=AgentScope Validation Platform",
    "capabilities=skill_calls,tool_calls,mcp_calls,context_handling,session_persistence",
    "backends=json,redis",
]


def main():
    check_service_running()

    payload = {
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Use the example skill's script workflow to generate the raw platform report. Return the script output directly.",
                    }
                ],
            }
        ]
    }

    text = send_chat(payload)
    for line in EXPECTED_LINES:
        assert line in text, f"Expected '{line}' in response, got: {text[:300]}"

    print("PASS: demo_skill_script.py - skill-guided script execution succeeded")
    print(f"  Response snippet: {text[:200]}")


if __name__ == "__main__":
    main()
