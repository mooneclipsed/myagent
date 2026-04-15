"""Test: Agent discovers, activates, and executes skills.

The agent is bootstrapped with hello-skill (lazy activation).
Through natural conversation the agent should:
  1. Discover the skill exists
  2. Activate it to read instructions
  3. Execute say_hello.py via run_local_shell
  4. Read skill resources via read_local_text_file

Strong proof strategy:
- Response contains script-unique markers
- Skill script appends to a marker file under scripts/manual-tests/files/
- Test verifies marker file contents changed after each script execution

Prerequisite: bash scripts/run_service.sh
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from _helpers import check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-skill"

HELLO_SKILL_DIR = os.path.expanduser("~/skills_test/hello-skill")
MARKER_FILE = "/Users/chengtong/OpenSource/myagent/scripts/manual-tests/files/hello_skill_invocations.log"


def read_marker_lines() -> list[str]:
    if not os.path.exists(MARKER_FILE):
        return []
    with open(MARKER_FILE, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle.readlines() if line.strip()]


def truncate_marker_file() -> None:
    os.makedirs(os.path.dirname(MARKER_FILE), exist_ok=True)
    with open(MARKER_FILE, "w", encoding="utf-8"):
        pass


def test_agent_discovers_skill():
    """Ask what skills are available → agent should reveal hello-skill exists."""
    result = chat(SESSION_ID, "你现在有哪些可用的技能？")
    check(
        "hello-skill" in result.text or result.has_evidence_of("hello-skill"),
        "agent discovered hello-skill",
        result.text,
    )


def test_agent_activates_and_uses_skill():
    """Ask agent to greet someone → agent should activate skill, then run script."""
    before = read_marker_lines()
    result = chat(
        SESSION_ID,
        "帮我用 hello-skill 和 Alice 打个招呼。"
        "先激活这个技能，然后根据技能说明执行对应的脚本。",
    )
    after = read_marker_lines()

    check(
        "Hello, Alice! Skill script is running." in result.text,
        "agent returned script-specific greeting for Alice",
        result.text,
    )
    check(
        "timestamp=" in result.text,
        "agent returned script timestamp marker",
        result.text,
    )
    check(
        "marker_file=" in result.text,
        "agent returned marker file path from script output",
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
        "hello-skill 的 resources 目录下有一个 usage.md，帮我读取一下它的内容。",
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
    print("TEST: Agent Skill Activation & Script Execution")
    print("=" * 60)
    print(f"  Skill dir: {HELLO_SKILL_DIR}")
    print(f"  Marker file: {MARKER_FILE}")
    check_service_running()
    truncate_marker_file()

    body = bootstrap(SESSION_ID, {
        "skills": [
            {
                "skill_dir": HELLO_SKILL_DIR,
                "activation_mode": "lazy",
            }
        ],
    })
    skill_names = [s["name"] for s in body.get("skills", [])]
    check("hello-skill" in skill_names, "bootstrap registered hello-skill (lazy)")

    try:
        test_agent_discovers_skill()
        test_agent_activates_and_uses_skill()
        test_agent_reads_skill_resources()
        test_agent_runs_script_with_different_args()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_skill.py")


if __name__ == "__main__":
    main()
