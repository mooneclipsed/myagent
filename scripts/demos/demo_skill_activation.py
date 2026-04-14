"""Demo: Bootstrap a session with a dynamic skill, discover it, activate it, and execute a script-backed capability."""

import httpx

from _helpers import SERVICE_URL, check_service_running, send_chat


def main():
    check_service_running()

    bootstrap_payload = {
        "session_id": "demo-skill-activation",
        "skills": [
            {
                "skill_dir": "skills/example_skill",
                "activation_mode": "lazy",
                "expose_structured_tools": True,
            }
        ],
        "mcp_servers": [],
    }

    bootstrap_response = httpx.post(
        f"{SERVICE_URL}/sessions/bootstrap",
        json=bootstrap_payload,
        timeout=30.0,
    )
    assert bootstrap_response.status_code == 200, (
        f"Expected bootstrap 200, got {bootstrap_response.status_code}: {bootstrap_response.text[:200]}"
    )
    body = bootstrap_response.json()
    assert body["skills"][0]["name"] == "example-skill"
    session_id = body["session_id"]

    text = send_chat(
        {
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "List available skills, activate example-skill, then use the appropriate script-backed tool "
                                "to return the raw platform report directly."
                            ),
                        }
                    ],
                }
            ],
            "session_id": session_id,
        }
    )
    assert "EXAMPLE_SKILL_SCRIPT_OK" in text, f"Expected script output marker, got: {text[:300]}"
    assert "platform=AgentScope Validation Platform" in text, (
        f"Expected platform line, got: {text[:300]}"
    )
    print("PASS: demo_skill_activation.py - discover -> activate -> execute succeeded")
    print(f"  Response snippet: {text[:200]}")


if __name__ == "__main__":
    main()
