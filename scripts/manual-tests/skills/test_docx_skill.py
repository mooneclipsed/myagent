"""Manual test: bootstrap docx and exercise it through /process."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import run_skill_test


SESSION_ID = "manual-skill-docx"


def main() -> None:
    run_skill_test(
        title="DOCX Skill via /process",
        session_id=SESSION_ID,
        skill_name="docx",
        prompt=(
            "请先激活 docx skill，然后直接根据它的 Quick Reference 告诉我："
            "读取或分析 .docx 内容、创建新文档、编辑现有文档，分别推荐什么路径。"
            "回答里必须原样包含 pandoc、docx-js、edit XML。"
        ),
        expected_substrings=["pandoc", "docx-js", "edit XML"],
    )


if __name__ == "__main__":
    main()
