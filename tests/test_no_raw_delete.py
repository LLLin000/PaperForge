"""Static guard — pinned against the 2026-08-14 incident.

The authoritative check lives in scripts/check_no_destructive_delete.py
(also wired as a pre-commit hook).  This test reuses it so CI (pytest) and
the git pre-commit hook always agree: no new code may add the accident
patterns (rmtree + ignore_errors, rmtree on empty/current-dir paths).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from check_no_destructive_delete import violations  # noqa: E402


def test_no_accident_delete_patterns() -> None:
    found = violations()
    assert not found, (
        "destructive-delete accident patterns present:\n" + "\n".join(found)
    )
