#!/usr/bin/env python3
"""Compatibility wrapper for the PaperForge setup wizard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    wizard = repo_root / "setup_wizard.py"
    if not wizard.exists():
        print(f"[ERR] setup_wizard.py not found: {wizard}")
        return 1
    return subprocess.run([sys.executable, str(wizard), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
