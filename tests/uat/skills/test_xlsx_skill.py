"""Manual test: bootstrap xlsx and exercise it through /chat."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import run_skill_test


SESSION_ID = "manual-skill-xlsx"


def main() -> None:
    run_skill_test(
        title="XLSX Skill via /chat",
        session_id=SESSION_ID,
        skill_name="xlsx",
        prompt=(
            "当前 runtime 已加载 xlsx skill，请总结它对 Excel 交付最关键的两条要求，"
            "并说明为什么不要在 Python 里硬编码计算结果。回答里必须原样包含 "
            "Zero Formula Errors、Use Formulas, Not Hardcoded Values、LibreOffice。"
        ),
        expected_substrings=[
            "Zero Formula Errors",
            "Use Formulas, Not Hardcoded Values",
            "LibreOffice",
        ],
    )


if __name__ == "__main__":
    main()
