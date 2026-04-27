"""Run all manual skill tests under scripts/manual-tests/skills/."""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TESTS = [
    ("test_doc_coauthoring_skill.py", "doc-coauthoring"),
    ("test_docx_skill.py", "docx"),
    ("test_pdf_skill.py", "pdf"),
    ("test_xlsx_skill.py", "xlsx"),
    ("test_frontend_design_skill.py", "frontend-design"),
    ("test_theme_factory_skill.py", "theme-factory"),
    ("test_webapp_testing_skill.py", "webapp-testing"),
]


def run_test(script: str, label: str) -> bool:
    print()
    print(f"RUN: {label}")
    result = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, script)], cwd=SCRIPT_DIR)
    return result.returncode == 0


def main() -> None:
    passed = []
    failed = []

    for script, label in TESTS:
        if run_test(script, label):
            passed.append(label)
        else:
            failed.append(label)

    print()
    print("=" * 60)
    print("SKILL TEST SUMMARY")
    print("=" * 60)
    for label in passed:
        print(f"  PASS: {label}")
    for label in failed:
        print(f"  FAIL: {label}")

    if failed:
        print()
        print(f"RESULT: {len(failed)}/{len(TESTS)} FAILED")
        sys.exit(1)

    print()
    print(f"RESULT: {len(passed)}/{len(TESTS)} PASSED")


if __name__ == "__main__":
    main()
