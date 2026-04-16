"""B2B happy-path test for bootstrapped reactagent capability loading.

Scenario:
  - Local runtime tools: read_file, edit_file
  - MCP tool: get_weather (stdio)
  - Dynamic skill: hello

The agent must read a file, query weather through MCP, activate/use hello,
and persist the conversation summary to `b2b_test.log` via `edit_file`.

Prerequisite: bash scripts/run_service.sh
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from _helpers import check_service_running, bootstrap, chat, shutdown, check

SESSION_ID = "test-agent-b2b-reactagent"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_SERVER_DIR = os.path.join(REPO_ROOT, "mcp-server")
WEATHER_SCRIPT = os.path.join(MCP_SERVER_DIR, "weather_mcp.py")
HELLO_SKILL_DIR = os.path.join(REPO_ROOT, "skills", "hello")
LOG_FILE = os.path.join(REPO_ROOT, "b2b_test.log")


def truncate_log_file() -> None:
    with open(LOG_FILE, "w", encoding="utf-8"):
        pass


def read_log_file() -> str:
    if not os.path.exists(LOG_FILE):
        return ""
    with open(LOG_FILE, "r", encoding="utf-8") as handle:
        return handle.read()


def test_agent_executes_full_b2b_flow() -> None:
    before = read_log_file()
    result = chat(
        SESSION_ID,
        "请严格按顺序完成这个正向验证场景："
        "先用 read_file 读取 skills/hello/resources/usage.md；"
        "再通过 MCP 的 get_weather 查询深圳天气；"
        "然后激活 hello skill 并和我打招呼；"
        "最后把你读取到的 usage 内容、天气结果、你的问候语，"
        "以及一句包含 reactagent 的总结，通过 edit_file 写入 b2b_test.log。",
    )
    after = read_log_file()

    check(result.called_tool("read_file") or result.has_evidence_of("read_file"), "agent used read_file")
    check(result.called_tool("get_weather") or result.has_evidence_of("get_weather"), "agent used MCP get_weather")
    check(result.called_tool("activate_skill") or result.has_evidence_of("activate_skill"), "agent activated hello skill")
    check(
        result.called_tool("say_hello")
        or result.has_evidence_of("say_hello")
        or "Hello," in result.text
        or "Hello," in after,
        "agent used hello skill",
    )
    check(result.called_tool("edit_file") or result.has_evidence_of("edit_file"), "agent used edit_file")
    check("Hello," in result.text or "Hello," in after, "response contains greeting", result.text)
    check("深圳" in result.text or "多云" in result.text or "26度" in result.text, "response contains weather", result.text)
    check(after != before, "b2b_test.log updated")
    check("reactagent" in after, "log contains reactagent summary", after)
    check("Hello," in after, "log contains greeting", after)
    check("深圳" in after or "多云" in after or "26度" in after, "log contains weather", after)
    check("say_hello.py" in after or "hello skill usage" in after, "log contains read_file content", after)


def main() -> None:
    print("=" * 60)
    print("TEST: B2B ReactAgent Happy Path")
    print("=" * 60)
    print(f"  MCP script: {WEATHER_SCRIPT}")
    print(f"  Skill dir: {HELLO_SKILL_DIR}")
    print(f"  Log file: {LOG_FILE}")
    check_service_running()
    truncate_log_file()

    body = bootstrap(SESSION_ID, {
        "mcp_servers": [
            {
                "name": "weather-mcp",
                "type": "stdio",
                "command": "uv",
                "args": ["run", WEATHER_SCRIPT, "stdio"],
            }
        ],
        "skills": [
            {
                "skill_dir": HELLO_SKILL_DIR,
                "activation_mode": "lazy",
            }
        ],
    })
    mcp_names = [s["name"] for s in body.get("mcp_servers", [])]
    skill_names = [s["name"] for s in body.get("skills", [])]
    check("weather-mcp" in mcp_names, "bootstrap registered weather-mcp")
    check("hello" in skill_names, "bootstrap registered hello skill")

    try:
        test_agent_executes_full_b2b_flow()
    finally:
        shutdown(SESSION_ID)

    print()
    print("ALL PASSED: test_b2b_reactagent.py")


if __name__ == "__main__":
    main()
