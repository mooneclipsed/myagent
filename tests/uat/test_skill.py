"""Test: Agent uses a bootstrapped skill and executes its script.

The agent is bootstrapped with hello.
Through natural conversation the agent should:
  1. Understand the hello skill is available from bootstrap
  2. Read skill instructions/resources when needed
  3. Execute the bundled script with the native shell tool
  4. Read skill resources via `read_file`

Strong proof strategy:
- Response contains script-unique markers
- Skill script appends to a marker file under tests/uat/files/
- Test verifies marker file contents changed after each script execution

Prerequisite: bash tests/uat/run_service.sh
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from _helpers import check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-skill"

HELLO_SKILL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "skills",
    "hello",
)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MARKER_FILE = os.path.join(REPO_ROOT, "tests", "uat", "files", "hello_skill_invocations.log")


def read_marker_lines() -> list[str]:
    if not os.path.exists(MARKER_FILE):
        return []
    with open(MARKER_FILE, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle.readlines() if line.strip()]


def truncate_marker_file() -> None:
    os.makedirs(os.path.dirname(MARKER_FILE), exist_ok=True)
    with open(MARKER_FILE, "w", encoding="utf-8"):
        pass


def test_agent_uses_loaded_skill_context():
    """Ask about the loaded skill without encouraging filesystem-wide discovery."""
    result = chat(SESSION_ID, "当前 runtime 已加载 hello skill。请简要说明这个 skill 的用途。")
    check(
        "hello" in result.text or result.has_evidence_of("hello"),
        "agent recognized loaded hello skill",
        result.text,
    )


def test_agent_uses_skill_script():
    """Ask agent to greet someone → agent should run the skill script."""
    before = read_marker_lines()
    result = chat(
        SESSION_ID,
        "帮我用 hello skill 和 Alice 打个招呼。"
        "这个 skill 已经随 runtime 加载；请根据技能说明用 run_local_shell 执行 scripts/say_hello.py。",
    )
    after = read_marker_lines()

    check(
        "Hello, Alice! Skill script is running." in result.text,
        "agent returned script-specific greeting for Alice",
        result.text,
    )
    check(
        any("timestamp=" in line and "name=Alice" in line for line in after[len(before):]),
        "script marker records Alice timestamp",
        result.text,
    )
    check(
        "hello_skill_invocations.log" in result.text
        or any("name=Alice" in line for line in after[len(before):]),
        "agent surfaced or recorded marker file evidence",
        result.text,
    )
    check(
        len(after) == len(before) + 1,
        "script execution appended one marker line",
        f"before={before}, after={after}",
    )
    check(
        any("name=Alice" in line for line in after[len(before):]),
        "marker file records Alice invocation",
        str(after),
    )


def test_agent_reads_skill_resources():
    """Ask about skill usage → agent should read resources/usage.md."""
    result = chat(
        SESSION_ID,
        "hello skill 的 resources 目录下有一个 usage.md，帮我读取一下它的内容。",
    )
    check(
        "say_hello.py" in result.text or "chengtong" in result.text,
        "agent read skill resource file and returned content",
        result.text,
    )


def test_agent_runs_script_with_different_args():
    """Ask greeting with different name → agent executes script with new args."""
    before = read_marker_lines()
    result = chat(SESSION_ID, "再帮我用同样的方式跟 Bob 打个招呼。")
    after = read_marker_lines()

    check(
        "Hello, Bob! Skill script is running." in result.text,
        "agent re-executed say_hello.py for Bob",
        result.text,
    )
    check(
        "timestamp=" in result.text,
        "agent returned timestamp for Bob run",
        result.text,
    )
    check(
        len(after) == len(before) + 1,
        "second script execution appended one marker line",
        f"before={before}, after={after}",
    )
    check(
        any("name=Bob" in line for line in after[len(before):]),
        "marker file records Bob invocation",
        str(after),
    )


def main():
    print("=" * 60)
    print("TEST: Agent Skill Loading & Script Execution")
    print("=" * 60)
    print(f"  Skill dir: {HELLO_SKILL_DIR}")
    print(f"  Marker file: {MARKER_FILE}")
    check_service_running()
    truncate_marker_file()

    body = bootstrap(SESSION_ID, {
        "skills": [
            {
                "skill_dir": HELLO_SKILL_DIR,
            }
        ],
    })
    skill_names = [s["name"] for s in body.get("skills", [])]
    check("hello" in skill_names, "bootstrap registered hello")

    try:
        test_agent_uses_loaded_skill_context()
        test_agent_uses_skill_script()
        test_agent_reads_skill_resources()
        test_agent_runs_script_with_different_args()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_skill.py")


if __name__ == "__main__":
    main()
