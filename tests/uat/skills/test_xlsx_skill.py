"""Manual test: bootstrap xlsx and exercise it through /chat."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import make_skill_session_id, run_skill_test


SESSION_ID = make_skill_session_id("xlsx")
TENANT_SESSION_ID = make_skill_session_id("xlsx-liuyue")
TENANT_ID = "liuyue"


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
    run_skill_test(
        title="Tenant liuyue skill-excel via /chat",
        session_id=TENANT_SESSION_ID,
        tenant_id=TENANT_ID,
        skill_name="xlsx",
        skill_dir_name="xlsx",
        prompt=(
            "当前 tenant_id 是 liuyue，runtime 已加载 skill-excel（本地 xlsx skill）。"
            "请给出一个 Excel 交付检查用例，说明如何验证公式没有错误、为什么要使用公式而不是硬编码值，"
            "以及什么时候需要用 LibreOffice 重算。回答必须原样包含 liuyue、"
            "Zero Formula Errors、Use Formulas, Not Hardcoded Values、LibreOffice。"
        ),
        expected_substrings=[
            "liuyue",
            "Zero Formula Errors",
            "Use Formulas, Not Hardcoded Values",
            "LibreOffice",
        ],
    )


if __name__ == "__main__":
    main()
