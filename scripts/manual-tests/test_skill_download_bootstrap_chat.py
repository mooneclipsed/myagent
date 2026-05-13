"""Manual integration test for fixture-backed skill download and chat.

Prerequisite:
    sh scripts/run_service.sh
"""

from __future__ import annotations

import json
import os
import threading
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FIXTURE_DIR = ROOT / "scripts" / "manual-tests" / "skill-download-fixture"
ZIP_PATH = FIXTURE_DIR / "test-skill.zip"
RUNTIME_ID = "test-skill-download-runtime"
USER_QUERY = "请帮我检查今天的系统状态"
SERVICE_URL = os.getenv("SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
HTTP_TIMEOUT = 180.0


class SkillZipHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        expected_path = "/api/v1/skills/1001/versions/2001/download"
        if self.path != expected_path:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return

        payload = ZIP_PATH.read_bytes()
        self.send_response(200)
        self.send_header("content-type", "application/zip")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def parse_sse_events(response_text: str) -> list[dict]:
    events = []
    for line in response_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        events.append(json.loads(data))
    return events


def extract_text(events: list[dict]) -> str:
    chunks = []
    for event in events:
        delta = event.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("text"), str):
            chunks.append(delta["text"])
            continue
        text = event.get("text")
        if isinstance(text, str):
            chunks.append(text)
    return "".join(chunks)


def check_service_running(client: httpx.Client) -> None:
    try:
        response = client.get("/docs")
    except httpx.ConnectError as exc:
        raise SystemExit(
            "Service is not running. Start it with: sh scripts/run_service.sh"
        ) from exc
    response.raise_for_status()


def shutdown_runtime(client: httpx.Client) -> None:
    response = client.post(f"/runtimes/{RUNTIME_ID}/shutdown")
    if response.status_code not in {200, 404}:
        response.raise_for_status()


def assert_downloaded_skill(bootstrap_body: dict) -> Path:
    downloads = bootstrap_body.get("skill_downloads", [])
    assert len(downloads) == 1, downloads
    download = downloads[0]
    assert download["status"] == "installed", download

    skill_dir = Path(download["skill_dir"])
    assert skill_dir.is_dir(), skill_dir
    assert (skill_dir / "SKILL.md").is_file(), skill_dir

    assert bootstrap_body.get("skills") == [
        {"name": "test-skill", "structured_tools": []},
    ]
    return skill_dir


def main() -> None:
    if not ZIP_PATH.is_file():
        raise SystemExit(f"Missing skill zip: {ZIP_PATH}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), SkillZipHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with httpx.Client(base_url=SERVICE_URL, timeout=HTTP_TIMEOUT) as client:
            check_service_running(client)
            shutdown_runtime(client)

            bootstrap_response = client.post(
                "/runtimes/init",
                json={
                    "runtime_id": RUNTIME_ID,
                    "system_prompt": (
                        "你必须严格遵守已注册 skill 的说明。"
                        "当 test-skill 可用时，必须调用它处理用户请求，"
                        "最终答案必须保留 skill 输出中的分隔线和原文。"
                    ),
                    "skills_download_url": base_url,
                    "skill_downloads": [
                        {"skill_id": 1001, "version_id": 2001},
                    ],
                },
            )
            print("initialize_status=", bootstrap_response.status_code)
            print("runtime_profile=", json.dumps(bootstrap_response.json(), ensure_ascii=False))
            bootstrap_response.raise_for_status()
            skill_dir = assert_downloaded_skill(bootstrap_response.json())
            print("downloaded_skill_dir=", skill_dir)

            chat_response = client.post(
                "/chat",
                json={
                    "runtime_id": RUNTIME_ID,
                    "session_id": RUNTIME_ID,
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"必须使用 test-skill 处理这个请求：{USER_QUERY}",
                                }
                            ],
                        }
                    ],
                },
            )
            print("chat_status=", chat_response.status_code)
            chat_response.raise_for_status()
            events = parse_sse_events(chat_response.text)
            text = extract_text(events)
            print("chat_text=", text)

            statuses = [event.get("status") for event in events if "status" in event]
            assert "completed" in statuses, statuses
            assert "测试大成功" in text
            assert f"用户请求: {USER_QUERY}" in text
    finally:
        try:
            with httpx.Client(base_url=SERVICE_URL, timeout=HTTP_TIMEOUT) as client:
                shutdown_runtime(client)
        except Exception:
            pass
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
