"""Shared utilities for demo scripts.

Provides service health check, SSE event parsing, and text extraction
used by all demo scripts (D-02, D-04).
"""

import json
import os
import sys

import httpx

SERVICE_URL = os.getenv("SERVICE_URL", "http://127.0.0.1:8000")


def check_service_running() -> None:
    """Verify the service is reachable. Exit with clear message if not (Pitfall 1)."""
    try:
        httpx.get(f"{SERVICE_URL}/docs", timeout=2.0)
    except httpx.ConnectError:
        print(
            "ERROR: Service is not running.\n"
            "Start it first with:\n"
            "  sh scripts/run_service.sh\n"
            "Then re-run this demo.",
            file=sys.stderr,
        )
        sys.exit(1)


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE response text into a list of JSON event dicts."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("data:"):
            continue
        data_str = line[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            events.append(json.loads(data_str))
        except json.JSONDecodeError:
            continue
    return events


def extract_text_from_events(events: list[dict]) -> str:
    """Extract concatenated text from SSE content/delta events (Pitfall 4)."""
    texts = []
    for event in events:
        # Handle content delta events
        delta = event.get("delta", {})
        if isinstance(delta, dict) and "text" in delta:
            texts.append(delta["text"])
        elif isinstance(delta, str):
            texts.append(delta)
        # Handle direct text field
        elif "text" in event and isinstance(event.get("text"), str) and event.get("type") != "response.created":
            texts.append(event["text"])
    return "".join(texts)


def send_chat(payload: dict, timeout: float = 30.0) -> str:
    """Send a chat request and return extracted response text."""
    response = httpx.post(
        f"{SERVICE_URL}/process",
        json=payload,
        timeout=timeout,
    )
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    events = parse_sse_events(response.text)
    statuses = [e.get("status") for e in events if "status" in e]
    assert "completed" in statuses, (
        f"Expected completed status, got: {statuses}"
    )
    return extract_text_from_events(events)
