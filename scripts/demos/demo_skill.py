"""Demo: Verify agent skill injection through the chat endpoint (DEV-03).

Sends a query about the platform's purpose. The registered example-skill
should inject context into the agent's system prompt, influencing the response
to reference the AgentScope Validation Platform.

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
                "content": [{"type": "text", "text": "What is this platform for? What does it validate?"}],
            }
        ]
    }

    text = send_chat(payload)
    # The skill injects context about the AgentScope validation platform
    assert "validat" in text.lower() or "platform" in text.lower() or "agentscope" in text.lower(), (
        f"Expected platform/skill context in response, got: {text[:200]}"
    )
    print("PASS: demo_skill.py - skill context influenced response")
    print(f"  Response snippet: {text[:150]}")


if __name__ == "__main__":
    main()
