"""Shared utilities for manual integration test scripts.

These scripts test tool/MCP/skill invocation THROUGH the agent's
reasoning loop — not direct function calls. The agent receives
natural language, decides which capability to invoke, and we
verify it made the right choice.
"""

import json
import os
import sys
from dataclasses import dataclass, field

import httpx

SERVICE_URL = os.getenv("SERVICE_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = float(os.getenv("TEST_TIMEOUT", "90"))


@dataclass
class ChatResult:
    """Structured result from a chat request, preserving all SSE events."""

    text: str
    events: list[dict] = field(default_factory=list)

    def _iter_dicts(self, value):
        """Recursively walk nested event payloads and yield dict nodes only."""
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from self._iter_dicts(nested)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_dicts(item)

    def _is_tool_call_record(self, node: dict) -> bool:
        """Return True only for structured tool-call-like records, not free text."""
        marker_values = {
            node.get("type"),
            node.get("object"),
            node.get("event"),
            node.get("item_type"),
            node.get("call_type"),
        }
        if "tool_call" in marker_values or "function_call" in marker_values:
            return True
        if isinstance(node.get("tool_name"), str):
            return True
        function = node.get("function")
        if isinstance(function, dict) and any(
            isinstance(function.get(key), str) for key in ("name", "tool_name", "function_name")
        ):
            return True
        return False

    def _extract_tool_name(self, node: dict) -> str | None:
        """Extract the tool/function name from a structured tool-call record."""
        for key in ("name", "tool_name", "function_name"):
            value = node.get(key)
            if isinstance(value, str) and value:
                return value
        function = node.get("function")
        if isinstance(function, dict):
            for key in ("name", "tool_name", "function_name"):
                value = function.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    @property
    def tool_calls(self) -> list[dict]:
        """Extract only structured tool_call/function_call records from SSE events."""
        calls = []
        for node in self._iter_dicts(self.events):
            if self._is_tool_call_record(node):
                calls.append(node)
        return calls

    @property
    def tool_names_used(self) -> set[str]:
        """Tool names extracted only from structured tool_call records."""
        names = set()
        for call in self.tool_calls:
            name = self._extract_tool_name(call)
            if name:
                names.add(name)
        return names

    def called_tool(self, name: str) -> bool:
        """Return True if a structured tool_call record exists for the given tool name."""
        return name in self.tool_names_used

    def has_evidence_of(self, keyword: str) -> bool:
        """Check if keyword appears anywhere in events (debug helper, not strict proof)."""
        return keyword in json.dumps(self.events, ensure_ascii=False)


def check_service_running() -> None:
    try:
        httpx.get(f"{SERVICE_URL}/docs", timeout=2.0)
    except httpx.ConnectError:
        print(
            "ERROR: Agent service is not running.\n"
            "Start it with: bash scripts/run_service.sh",
            file=sys.stderr,
        )
        sys.exit(1)


def parse_sse_events(response_text: str) -> list[dict]:
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


def extract_text(events: list[dict]) -> str:
    texts = []
    for event in events:
        delta = event.get("delta", {})
        if isinstance(delta, dict) and "text" in delta:
            texts.append(delta["text"])
        elif isinstance(delta, str):
            texts.append(delta)
        elif "text" in event and isinstance(event.get("text"), str) and event.get("type") != "response.created":
            texts.append(event["text"])
    return "".join(texts)


def bootstrap(session_id: str, payload: dict) -> dict:
    resp = httpx.post(
        f"{SERVICE_URL}/sessions/bootstrap",
        json={"session_id": session_id, **payload},
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code != 200:
        print(f"  Bootstrap FAILED ({resp.status_code}): {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def chat(session_id: str, text: str) -> ChatResult:
    """Send a natural language message and return structured ChatResult."""
    payload = {
        "session_id": session_id,
        "input": [{"role": "user", "content": [{"type": "text", "text": text}]}],
    }
    resp = httpx.post(f"{SERVICE_URL}/process", json=payload, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        print(f"  Chat FAILED ({resp.status_code}): {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)
    events = parse_sse_events(resp.text)
    statuses = [e.get("status") for e in events if "status" in e]
    if "completed" not in statuses:
        print(f"  Chat did not complete. Statuses: {statuses}", file=sys.stderr)
        if "failed" in statuses:
            print(f"  Events: {json.dumps(events, ensure_ascii=False)[:500]}", file=sys.stderr)
        sys.exit(1)
    return ChatResult(text=extract_text(events), events=events)


def shutdown(session_id: str) -> None:
    resp = httpx.post(f"{SERVICE_URL}/sessions/{session_id}/shutdown", timeout=10.0)
    if resp.status_code not in (200, 404):
        print(f"  WARNING: Shutdown returned {resp.status_code}", file=sys.stderr)


def check(condition: bool, label: str, detail: str = "") -> None:
    """Assert a condition. Exit on failure, print PASS on success."""
    if not condition:
        print(f"  FAIL: {label}", file=sys.stderr)
        if detail:
            print(f"    {detail}", file=sys.stderr)
        sys.exit(1)
    suffix = f"  ({detail[:80]})" if detail else ""
    print(f"  PASS: {label}{suffix}")
