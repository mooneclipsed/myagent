"""Demo: Bootstrap a runtime with a dynamic skill, discover it, and activate it."""

import httpx

from _helpers import SERVICE_URL, check_service_running, send_chat


def main():
    check_service_running()

    bootstrap_payload = {
        "runtime_id": "demo-skill-activation",
        "skills": [
            {
                "skill_dir": "skills/example_skill",
            }
        ],
        "mcp_servers": [],
    }

    bootstrap_response = httpx.post(
        f"{SERVICE_URL}/runtimes/initialize",
        json=bootstrap_payload,
        timeout=30.0,
    )
    assert bootstrap_response.status_code == 200, (
        f"Expected bootstrap 200, got {bootstrap_response.status_code}: {bootstrap_response.text[:200]}"
    )
    body = bootstrap_response.json()
    assert body["skills"][0]["name"] == "example-skill"
    assert body["skills"][0]["structured_tools"] == []
    runtime_id = body["runtime_id"]

    text = send_chat(
        {
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Use the example-skill instructions to summarize the platform context."
                            ),
                        }
                    ],
                }
            ],
            "runtime_id": runtime_id,
            "session_id": "demo-skill-activation-chat",
        }
    )
    assert "AgentScope" in text, f"Expected skill context, got: {text[:300]}"
    print("PASS: demo_skill_activation.py - discover -> activate succeeded")
    print(f"  Response snippet: {text[:200]}")


if __name__ == "__main__":
    main()
