"""Run all manual integration tests in sequence.

Usage:
    cd scripts/manual-tests
    python run_all.py                 # run all
    python run_all.py --skip-http-mcp # skip HTTP MCP (servers not running)
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TESTS = [
    ("test_tools.py",     "Local Tools (agent invocation)"),
    ("test_mcp_stdio.py", "MCP stdio (agent invocation)"),
    ("test_mcp_http.py",  "MCP HTTP (agent invocation)"),
    ("test_skill.py",     "Skill activation & script (agent invocation)"),
    ("test_combined.py",  "Combined tool+MCP+skill routing"),
    ("test_b2b_reactagent.py", "B2B reactagent happy path"),
]


def run_test(script: str, label: str) -> bool:
    print()
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, script)],
        cwd=SCRIPT_DIR,
    )
    return result.returncode == 0


def main():
    skip_http_mcp = "--skip-http-mcp" in sys.argv

    passed, failed, skipped = [], [], []

    for script, label in TESTS:
        if script == "test_mcp_http.py" and skip_http_mcp:
            print(f"\nSKIP: {label}")
            skipped.append(label)
            continue
        if run_test(script, label):
            passed.append(label)
        else:
            failed.append(label)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for label in passed:
        print(f"  PASS: {label}")
    for label in skipped:
        print(f"  SKIP: {label}")
    for label in failed:
        print(f"  FAIL: {label}")
    print()

    total = len(passed) + len(failed)
    if failed:
        print(f"RESULT: {len(failed)}/{total} FAILED")
        sys.exit(1)
    else:
        extra = f", {len(skipped)} skipped" if skipped else ""
        print(f"RESULT: {len(passed)}/{total} PASSED{extra}")


if __name__ == "__main__":
    main()
