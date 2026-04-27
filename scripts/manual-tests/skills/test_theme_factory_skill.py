"""Manual test: bootstrap theme-factory and exercise it through /process."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import run_skill_test


SESSION_ID = "manual-skill-theme-factory"


def main() -> None:
    run_skill_test(
        title="Theme Factory Skill via /process",
        session_id=SESSION_ID,
        skill_name="theme-factory",
        prompt=(
            "请先激活 theme-factory skill，然后总结它要求的主题应用流程，"
            "并告诉我主题展示文件和一个可选主题名。回答里必须原样包含 "
            "theme-showcase.pdf、Modern Minimalist、themes/。"
        ),
        expected_substrings=["theme-showcase.pdf", "Modern Minimalist", "themes/"],
    )


if __name__ == "__main__":
    main()
