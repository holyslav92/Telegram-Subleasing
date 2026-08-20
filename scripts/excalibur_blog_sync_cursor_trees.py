#!/usr/bin/env python3
"""Copy plugin trees into .cursor/ so Cloud and the plugin stay identical."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAIRS = (
    (ROOT / "agents", ROOT / ".cursor/agents"),
    (ROOT / "skills", ROOT / ".cursor/skills"),
    (ROOT / "rules", ROOT / ".cursor/rules"),
)


def sync() -> None:
    for src, dest in PAIRS:
        if not src.is_dir():
            raise SystemExit(f"missing source tree: {src}")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)


def main(argv: list[str]) -> int:
    sync()
    if argv[1:] == ["--check"]:
        return 0
    print("synced agents/, skills/, rules/ → .cursor/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
