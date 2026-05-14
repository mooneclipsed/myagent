"""Manual test: AgentScope memory compression with a real LLM.

Prerequisite:
  - Start the service with real model credentials:
      bash tests/uat/run_service.sh
  - Use the JSON session backend so this script can inspect the saved memory:
      SESSION_BACKEND=json

This test bootstraps a runtime with an intentionally tiny compression
threshold, sends two real LLM requests, then verifies the saved session memory
contains a non-empty compressed summary and compressed message marks.
"""

import json
import os
import sys
import uuid
from pathlib import Path

import httpx


SERVICE_URL = os.getenv("SERVICE_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = float(os.getenv("TEST_TIMEOUT", "120"))
REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_DIR = Path(os.getenv("SESSION_DIR", REPO_ROOT / "sessions"))


def check(condition: bool, label: str, detail: str = "") -> None:
    if not condition:
        print(f"  FAIL: {label}", file=sys.stderr)
        if detail:
            print(f"    {detail}", file=sys.stderr)
        sys.exit(1)
    suffix = f"  ({detail[:120]})" if detail else ""
    print(f"  PASS: {label}{suffix}")


def check_service_running() -> None:
    try:
        response = httpx.get(f"{SERVICE_URL}/docs", timeout=2.0)
        check(response.status_code == 200, "service is running")
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
        data = line[len("data:") :].strip()
        if not data or data == "[DONE]":
            continue
        try:
            events.append(json.loads(data))
        except json.JSONDecodeError:
            continue
    return events


def bootstrap_runtime(runtime_id: str) -> None:
    response = httpx.post(
        f"{SERVICE_URL}/runtimes/init",
        json={
            "runtime_id": runtime_id,
            "memory_compression": {
                "enabled": True,
                "trigger_tokens": 1,
                "keep_recent": 1,
            },
            "skills": [],
            "mcp_servers": [],
        },
        timeout=DEFAULT_TIMEOUT,
    )
    check(response.status_code == 200, "runtime bootstrap completed", response.text[:200])


def chat(runtime_id: str, session_id: str, text: str) -> str:
    response = httpx.post(
        f"{SERVICE_URL}/chat",
        json={
            "runtime_id": runtime_id,
            "session_id": session_id,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        },
        timeout=DEFAULT_TIMEOUT,
    )
    check(response.status_code == 200, "process request returned 200", response.text[:200])
    events = parse_sse_events(response.text)
    statuses = [event.get("status") for event in events if "status" in event]
    if "completed" not in statuses:
        failed_events = [
            event for event in events if event.get("status") == "failed"
        ]
        detail = json.dumps(
            failed_events or events,
            ensure_ascii=False,
            indent=2,
        )
        check(False, "process stream completed", detail[:2000])
    texts = []
    for event in events:
        if isinstance(event.get("text"), str):
            texts.append(event["text"])
        delta = event.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("text"), str):
            texts.append(delta["text"])
    return "".join(texts)


def load_session_memory(session_id: str) -> dict:
    session_path = SESSION_DIR / f"{session_id}.json"
    check(session_path.exists(), "session file was created", str(session_path))
    with session_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    memory = payload.get("memory")
    check(isinstance(memory, dict), "session file contains memory")
    return memory


def compressed_mark_count(memory: dict) -> int:
    count = 0
    for item in memory.get("content", []):
        if isinstance(item, list) and len(item) == 2:
            marks = item[1]
            if isinstance(marks, list) and "compressed" in marks:
                count += 1
    return count


def main() -> None:
    runtime_id = f"compression-runtime-{uuid.uuid4().hex[:8]}"
    session_id = f"compression-session-{uuid.uuid4().hex[:8]}"

    print("=" * 60)
    print("TEST: Real LLM Memory Compression")
    print("=" * 60)
    print(f"  Service URL: {SERVICE_URL}")
    print(f"  Runtime ID: {runtime_id}")
    print(f"  Session ID: {session_id}")
    print(f"  Session dir: {SESSION_DIR}")

    check_service_running()
    bootstrap_runtime(runtime_id)

    first_text = chat(
        runtime_id,
        session_id,
        "Remember this exact test fact: ALPHA-COMPRESSION-FACT. Reply briefly.",
    )
    check(first_text.strip() != "", "first LLM response is non-empty", first_text[:120])

    second_text = chat(
        runtime_id,
        session_id,
        "Now answer briefly: what exact test fact did I ask you to remember?",
    )
    check(second_text.strip() != "", "second LLM response is non-empty", second_text[:120])

    memory = load_session_memory(session_id)
    summary = memory.get("_compressed_summary", "")
    check(isinstance(summary, str) and summary.strip() != "", "compressed summary was written", summary[:120])

    count = compressed_mark_count(memory)
    check(count > 0, "old messages were marked compressed", f"{count} compressed messages")
    check("ALPHA-COMPRESSION-FACT" in json.dumps(memory, ensure_ascii=False), "test fact remains in saved memory")

    print()
    print("ALL PASSED: test_memory_compression_real_llm.py")


if __name__ == "__main__":
    main()
