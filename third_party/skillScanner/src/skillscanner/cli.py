# -*- coding: utf-8 -*-
"""Command line interface for the standalone skill scanner."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .scan_policy import ScanPolicy
from .scanner import SkillScanner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillscanner",
        description="Scan an agent skill directory for security issues.",
    )
    parser.add_argument("path", help="Path to the skill directory to scan")
    parser.add_argument(
        "--name",
        help="Optional skill name to include in the scan result",
    )
    parser.add_argument(
        "--policy",
        help="Optional custom scan policy YAML path",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of pretty JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        policy = (
            ScanPolicy.from_yaml(args.policy)
            if args.policy
            else ScanPolicy.default()
        )
        result = SkillScanner(policy=policy).scan_skill(
            Path(args.path),
            skill_name=args.name,
        )
        json_kwargs = (
            {"ensure_ascii": False, "separators": (",", ":")}
            if args.compact
            else {"ensure_ascii": False, "indent": 2}
        )
        print(json.dumps(result.to_dict(), **json_kwargs))
        return 0 if result.is_safe else 1
    except Exception as exc:
        print(f"skillscanner: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
