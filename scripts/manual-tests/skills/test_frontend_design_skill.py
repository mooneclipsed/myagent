"""Manual test: bootstrap frontend-design and exercise it through /process."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import run_skill_test


SESSION_ID = "manual-skill-frontend-design"


def main() -> None:
    run_skill_test(
        title="Frontend Design Skill via /process",
        session_id=SESSION_ID,
        skill_name="frontend-design",
        prompt=(
            "请先激活 frontend-design skill，然后给我一个用于做前端页面的设计检查清单。"
            "回答里必须原样包含 Typography、Color & Theme、Motion。"
        ),
        expected_substrings=["Typography", "Color & Theme", "Motion"],
    )


if __name__ == "__main__":
    main()
