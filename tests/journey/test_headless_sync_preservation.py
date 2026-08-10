"""J2 — headless sync + vault preservation (#146 J-matrix).

Runs `paperforge sync` headless over a seeded vault and asserts the
Obsidian-managed directory (`.obsidian`) is byte-for-byte untouched.
This is the 3-OS machine gate: the sync path must never rewrite
Obsidian-owned files, even when a plugin bundle is present.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a CLI command as subprocess and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "paperforge"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=90,
    )


def _plant_obsidian_dir(vault: Path) -> dict[Path, bytes]:
    """Plant a .obsidian directory with sentinel content; return path -> bytes."""
    obs = vault / ".obsidian"
    sentinels = {
        obs / "app.json": json.dumps(
            {"vault": "sentinel-app", "attachmentFolderPath": "Attachments"},
            indent=2,
        ).encode("utf-8"),
        obs / "plugins" / "paperforge" / "main.js": (
            b"// sentinel plugin bundle\nconsole.log('paperforge');\n"
        ),
    }
    for path, payload in sentinels.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return sentinels


def test_headless_sync_preserves_obsidian_dir(test_vault: Path) -> None:
    """#146 J2: headless sync must not touch the Obsidian-managed directory."""
    sentinels = _plant_obsidian_dir(test_vault)

    result = _run(["sync", "--json"], test_vault)
    assert result.returncode == 0, f"sync failed: {result.stderr[:500]}"

    # Sync actually ran and produced the index...
    idx = (
        test_vault
        / "99_System"
        / "PaperForge"
        / "indexes"
        / "formal-library.json"
    )
    assert idx.exists(), "index file should exist after sync"

    # ...and the Obsidian-owned directory is byte-for-byte untouched.
    for path, payload in sentinels.items():
        assert path.read_bytes() == payload, f"{path} was modified by sync"
