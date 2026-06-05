"""Shared utilities for manual integration test scripts.

These scripts test tool/MCP/skill invocation THROUGH the agent's
reasoning loop — not direct function calls. The agent receives
natural language, decides which capability to invoke, and we
verify it made the right choice.
"""

import json
import os
import sys
import uuid
from dataclasses import dataclass, field

import httpx

SERVICE_URL = os.getenv("SERVICE_URL", "http://127.0.0.1:8000")
CHAT_PATH = os.getenv("CHAT_PATH", "/v2/chat")
DEFAULT_TIMEOUT = float(os.getenv("TEST_TIMEOUT", "90"))


def make_session_id(prefix: str) -> str:
    """Return a unique session id with a readable test prefix."""
    normalized_prefix = prefix.strip("-")
    return f"{normalized_prefix}-{uuid.uuid4().hex}"


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
            "Start it with: bash tests/uat/run_service.sh",
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
        payload = event.get("payload")
        if isinstance(payload, dict) and payload.get("status") == "streaming":
            delta = payload.get("delta")
            if isinstance(delta, str):
                texts.append(delta)
        delta = event.get("delta", {})
        if isinstance(delta, dict) and "text" in delta:
            texts.append(delta["text"])
        elif isinstance(delta, str):
            texts.append(delta)
        elif "text" in event and isinstance(event.get("text"), str) and event.get("type") != "response.created":
            texts.append(event["text"])
    return "".join(texts)


def initialize_runtime(session_id: str, payload: dict) -> dict:
    resp = httpx.post(
        f"{SERVICE_URL}/v2/runtimes/init",
        json=_v2_runtime_payload(session_id, payload),
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code != 200:
        print(f"  Runtime initialize FAILED ({resp.status_code}): {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)
    return _legacy_bootstrap_summary(resp.json())


bootstrap = initialize_runtime


def chat(
    session_id: str,
    text: str,
    path: str | None = None,
    tenant_id: str | None = None,
) -> ChatResult:
    """Send a natural language message and return structured ChatResult."""
    payload = {
        "runtime_id": session_id,
        "session_id": session_id,
        "input": text,
    }
    if tenant_id:
        payload["tenant_id"] = tenant_id
    target_path = path or CHAT_PATH
    resp = httpx.post(f"{SERVICE_URL}{target_path}", json=payload, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        print(f"  Chat FAILED ({resp.status_code}): {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)
    events = parse_sse_events(resp.text)
    statuses = [e.get("status") for e in events if "status" in e]
    payload_statuses = [
        e.get("payload", {}).get("status")
        for e in events
        if isinstance(e.get("payload"), dict) and "status" in e["payload"]
    ]
    if "completed" not in statuses and "completed" not in payload_statuses:
        print(f"  Chat did not complete. Statuses: {statuses}", file=sys.stderr)
        if "failed" in statuses or "failed" in payload_statuses:
            print(f"  Events: {json.dumps(events, ensure_ascii=False)[:500]}", file=sys.stderr)
        sys.exit(1)
    return ChatResult(text=extract_text(events), events=events)


def _v2_runtime_payload(session_id: str, payload: dict) -> dict:
    converted = {
        "runtime_id": payload.get("runtime_id", session_id),
        "tenant_id": payload.get("tenant_id"),
        "framework": payload.get("framework", "agentscope"),
        "model_config": payload.get("model_config"),
        "system_prompt": payload.get("system_prompt"),
        "capabilities": payload.get("capabilities", []),
    }
    capabilities = list(converted["capabilities"])

    for tool in payload.get("tools", []):
        name = tool["name"]
        tool_name = _v2_tool_name(name)
        capabilities.append(
            {
                "type": "tool",
                "name": name,
                "config": {"tool_name": tool_name},
            }
        )

    for server in payload.get("mcp_servers", []):
        config = {
            "transport": server.get("transport") or server.get("type", "stdio"),
            "command": server.get("command"),
            "args": server.get("args", []),
            "env": server.get("env", {}),
            "cwd": server.get("cwd"),
            "url": server.get("url"),
            "headers": server.get("headers", {}),
            "timeout": server.get("timeout", 30),
        }
        capabilities.append({"type": "mcp", "name": server["name"], "config": config})

    for skill in payload.get("skills", []):
        capabilities.append(
            {
                "type": "skill",
                "name": os.path.basename(os.path.normpath(skill["skill_dir"])),
                "config": {"path": skill["skill_dir"]},
            }
        )

    converted["capabilities"] = capabilities
    return {key: value for key, value in converted.items() if value is not None}


def _legacy_bootstrap_summary(body: dict) -> dict:
    capabilities = body.get("capabilities", [])
    return {
        **body,
        "tools": [{"name": item["name"]} for item in capabilities if item.get("type") == "tool"],
        "mcp_servers": [{"name": item["name"]} for item in capabilities if item.get("type") == "mcp"],
        "skills": [{"name": item["name"]} for item in capabilities if item.get("type") == "skill"],
    }


def _v2_tool_name(name: str) -> str:
    aliases = {
        "run_local_shell": "bash",
        "read_file": "read",
        "edit_file": "write",
        "get_weather": "local:get_weather",
        "calculate": "local:calculate",
        "run_platform_report": "local:run_platform_report",
        "summarize_platform_callable": "local:summarize_platform_callable",
    }
    return aliases.get(name, name)


def check(condition: bool, label: str, detail: str = "") -> None:
    """Assert a condition. Exit on failure, print PASS on success."""
    if not condition:
        print(f"  FAIL: {label}", file=sys.stderr)
        if detail:
            print(f"    {detail}", file=sys.stderr)
        sys.exit(1)
    suffix = f"  ({detail[:80]})" if detail else ""
    print(f"  PASS: {label}{suffix}")
