#!/usr/bin/env python
"""Pre-commit check: PaperForge runtime code must never use the two
accident patterns from 2026-08-14 (`shutil.rmtree(Path())` deleted the
production vault root):

1. ``shutil.rmtree(...)`` combined with ``ignore_errors=True`` — the
   silent-delete combo that turned a wrong path into a full vault wipe
   with no error signal;
2. ``shutil.rmtree(Path())`` / ``rmtree(Path(""))`` / ``rmtree("")`` —
   empty/current-directory paths.

Ordinary single-file `.unlink()` / plain `rmtree` on explicit temp paths
remain allowed (existing legit cleanup); the guard targets the dangerous
combos that must be added only through the trash layer.

Run: python scripts/check_no_destructive_delete.py
Exit 1 (with locations) on violation, 0 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "paperforge"

# 1) shutil.rmtree( ... ignore_errors=True ... ) — same statement (nested
# parens allowed, e.g. rmtree(Path(), ignore_errors=True))
_IGNORE_ERRORS_RMTREE = re.compile(
    r"shutil\.rmtree\s*\([^\n]*?ignore_errors\s*=\s*True"
)
# 2) shutil.rmtree(Path()) / rmtree(Path("")) / rmtree("") / rmtree(".")
# with any following args (e.g. , ignore_errors=True)
_EMPTY_RMTREE = re.compile(
    r"shutil\.rmtree\s*\(\s*(?:Path\s*\(\s*\)|Path\s*\(\s*[\"']{2}\s*\)|[\"']{2}|[\"']\.[\"'])\s*[,)]"
)


def _runtime_py_files() -> list[Path]:
    return [
        p
        for p in sorted(PACKAGE.rglob("*.py"))
        if "__pycache__" not in p.parts and p.name != "trash.py"
    ]


def violations() -> list[str]:
    found: list[str] = []
    for path in _runtime_py_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO)
        for lineno, line in enumerate(text.splitlines(), 1):
            if _IGNORE_ERRORS_RMTREE.search(line):
                found.append(f"{rel}:{lineno}: rmtree with ignore_errors=True")
            if _EMPTY_RMTREE.search(line):
                found.append(f"{rel}:{lineno}: rmtree on empty/current-dir path")
    return found


def main() -> int:
    found = violations()
    if found:
        print("Destructive-delete check FAILED (accident patterns):")
        for line in found:
            print(f"  {line}")
        print(
            "rmtree with ignore_errors=True or an empty path is forbidden; "
            "use worker/trash.py (recoverable move) instead."
        )
        return 1
    print("no-destructive-delete: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
