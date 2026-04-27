"""Shared helpers for manual skill integration tests under scripts/manual-tests/skills."""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MANUAL_TESTS_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

sys.path.insert(0, MANUAL_TESTS_DIR)

from _helpers import bootstrap, chat, check, check_service_running, shutdown  # noqa: E402


def resolve_skill_dir(skill_dir_name: str) -> str:
    return os.path.join(REPO_ROOT, "skills", skill_dir_name)


def run_skill_test(
    *,
    title: str,
    session_id: str,
    skill_name: str,
    prompt: str,
    expected_substrings: list[str],
    skill_dir_name: str | None = None,
) -> None:
    target_skill_dir = resolve_skill_dir(skill_dir_name or skill_name)

    print("=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)
    print(f"  Skill dir: {target_skill_dir}")
    print(f"  Session ID: {session_id}")
    check_service_running()

    body = bootstrap(
        session_id,
        {
            "skills": [
                {
                    "skill_dir": target_skill_dir,
                    "activation_mode": "lazy",
                }
            ],
            "mcp_servers": [],
        },
    )
    skill_names = [item["name"] for item in body.get("skills", [])]
    check(skill_name in skill_names, f"bootstrap registered {skill_name}", str(skill_names))

    try:
        result = chat(session_id, prompt)
        activation_detail = json.dumps(result.tool_calls or result.events, ensure_ascii=False)[:200]
        check(
            result.called_tool("activate_skill") or result.has_evidence_of("activate_skill"),
            "agent called activate_skill",
            activation_detail,
        )
        for snippet in expected_substrings:
            check(snippet in result.text, f"response contains {snippet}", result.text)
    finally:
        shutdown(session_id)

    print()
    print(f"ALL PASSED: {os.path.basename(sys.argv[0])}")
