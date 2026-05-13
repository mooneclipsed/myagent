"""Manual test: bootstrap webapp-testing and exercise it through /chat."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import run_skill_test


SESSION_ID = "manual-skill-webapp-testing"


def main() -> None:
    run_skill_test(
        title="Webapp Testing Skill via /chat",
        session_id=SESSION_ID,
        skill_name="webapp-testing",
        prompt=(
            "当前 runtime 已加载 webapp-testing skill，请告诉我测试本地 web app 时应该用什么框架、"
            "什么 helper script，以及动态页面的关键等待条件。回答里必须原样包含 "
            "Playwright、scripts/with_server.py、networkidle。"
        ),
        expected_substrings=["Playwright", "scripts/with_server.py", "networkidle"],
    )


if __name__ == "__main__":
    main()
