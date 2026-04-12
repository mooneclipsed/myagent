"""Demo: Session resume with context persistence (DEV-03).

Sends a chat with a session_id, then sends a second chat with the same
session_id to verify the agent remembers prior context. Uses the default
JSON backend.

Prerequisite: Service running at http://127.0.0.1:8000
Start with: bash scripts/run_service.sh
"""

import uuid

import httpx

from _helpers import check_service_running, extract_text_from_events, parse_sse_events, SERVICE_URL


def main():
    check_service_running()

    session_id = f"demo-resume-{uuid.uuid4()}"
    timeout = 30.0

    # First message: tell the agent something
    payload1 = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "My favorite number is 42. Remember it."}],
            }
        ],
        "session_id": session_id,
    }

    response1 = httpx.post(f"{SERVICE_URL}/process", json=payload1, timeout=timeout)
    assert response1.status_code == 200, (
        f"Request 1 failed: {response1.status_code} {response1.text[:200]}"
    )
    events1 = parse_sse_events(response1.text)
    statuses1 = [e.get("status") for e in events1 if "status" in e]
    assert "completed" in statuses1, f"Request 1 did not complete: {statuses1}"

    # Second message: ask the agent to recall
    payload2 = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "What is my favorite number?"}],
            }
        ],
        "session_id": session_id,
    }

    response2 = httpx.post(f"{SERVICE_URL}/process", json=payload2, timeout=timeout)
    assert response2.status_code == 200, (
        f"Request 2 failed: {response2.status_code} {response2.text[:200]}"
    )
    events2 = parse_sse_events(response2.text)
    statuses2 = [e.get("status") for e in events2 if "status" in e]
    assert "completed" in statuses2, f"Request 2 did not complete: {statuses2}"

    text2 = extract_text_from_events(events2)
    assert "42" in text2, (
        f"Expected '42' in resumed response, got: {text2[:200]}"
    )

    print("PASS: demo_resume.py - session resume with context persistence works")
    print(f"  Session ID: {session_id}")
    print(f"  Response snippet: {text2[:150]}")


if __name__ == "__main__":
    main()
