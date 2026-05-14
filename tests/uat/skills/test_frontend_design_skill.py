"""Manual test: bootstrap frontend-design and exercise it through /chat."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import make_skill_session_id, run_skill_test


SESSION_ID = make_skill_session_id("frontend-design")


def main() -> None:
    run_skill_test(
        title="Frontend Design Skill via /chat",
        session_id=SESSION_ID,
        skill_name="frontend-design",
        prompt=(
            "当前 runtime 已加载 frontend-design skill，请给我一个用于做前端页面的设计检查清单。"
            "回答里必须原样包含 Typography、Color & Theme、Motion。"
        ),
        expected_substrings=["Typography", "Color & Theme", "Motion"],
    )


if __name__ == "__main__":
    main()
