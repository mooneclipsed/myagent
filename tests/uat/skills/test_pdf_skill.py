"""Manual test: bootstrap pdf and exercise it through /chat."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _skill_test_helpers import make_skill_session_id, run_skill_test


SESSION_ID = make_skill_session_id("pdf")


def main() -> None:
    run_skill_test(
        title="PDF Skill via /chat",
        session_id=SESSION_ID,
        skill_name="pdf",
        prompt=(
            "当前 runtime 已加载 pdf skill，请按 skill 的结构告诉我：基本 PDF 操作、文本或表格提取、"
            "创建 PDF，各自推荐哪个 Python 库。回答里必须原样包含 pypdf、pdfplumber、reportlab。"
        ),
        expected_substrings=["pypdf", "pdfplumber", "reportlab"],
    )


if __name__ == "__main__":
    main()
