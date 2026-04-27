"""Manual test: bootstrap doc-coauthoring and exercise it through /process."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import run_skill_test


SESSION_ID = "manual-skill-doc-coauthoring"


def main() -> None:
    run_skill_test(
        title="Doc Co-Authoring Skill via /process",
        session_id=SESSION_ID,
        skill_name="doc-coauthoring",
        prompt=(
            "请先激活 doc-coauthoring skill，然后按照 skill 里的原始英文阶段名，"
            "概括它的三阶段工作流。回答里必须原样包含 "
            "Context Gathering、Refinement & Structure、Reader Testing。"
        ),
        expected_substrings=[
            "Context Gathering",
            "Refinement & Structure",
            "Reader Testing",
        ],
    )


if __name__ == "__main__":
    main()
