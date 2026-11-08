"""Every tracked file must exist in the working tree.

Three tracked test files disappeared during a working session and were restored
by hand. This guard makes the loss visible on the next test run instead of
letting repeated `git checkout` hide it; it deliberately does not restore
anything.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_every_tracked_file_exists() -> None:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    missing = [
        path
        for path in proc.stdout.split("\0")
        if path and not (REPO_ROOT / path).is_file()
    ]
    assert not missing, "tracked files missing from the working tree:\n  " + "\n  ".join(missing[:20])
