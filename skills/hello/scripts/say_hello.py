import json
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    name = str(payload.get("name") or "friend")

    now = datetime.now().isoformat(timespec="seconds")
    repo_root = Path(__file__).resolve().parents[3]
    marker_dir = repo_root / "scripts" / "manual-tests" / "files"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_file = marker_dir / "hello_skill_invocations.log"
    with marker_file.open("a", encoding="utf-8") as handle:
        handle.write(f"name={name}\ttimestamp={now}\n")

    print(f"Hello, {name}! Skill script is running.")
    print(f"timestamp={now}")
    print(f"marker_file={marker_file}")


if __name__ == "__main__":
    main()
