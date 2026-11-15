"""Behavior tests for the recoverable Trash CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.conftest import canonical_test_config


def test_purge_older_than_only_removes_expired_entries(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    trash_root = vault / ".paperforge" / "trash"
    now = datetime.now(timezone.utc)
    entries: dict[str, Path] = {}

    for age_days, paper_key in ((8, "OLD001"), (6, "NEW001")):
        stamp = (now - timedelta(days=age_days)).strftime("%Y%m%dT%H%M%SZ")
        record_id = paper_key.lower()
        record_dir = trash_root / stamp / record_id
        item = record_dir / paper_key
        item.mkdir(parents=True)
        _ = (item / "fulltext.md").write_text(paper_key, encoding="utf-8")
        _ = (record_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "trash_id": record_id,
                    "operation": "test",
                    "paper_key": paper_key,
                    "original_path": str(vault / "System" / paper_key),
                    "trash_path": str(item),
                    "timestamp": stamp,
                    "trashed_at": stamp,
                }
            ),
            encoding="utf-8",
        )
        entries[paper_key] = item

    outside = vault / "keep.md"
    _ = outside.write_text("preserve", encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "paperforge",
            "--vault",
            str(vault),
            "trash",
            "purge",
            "--older-than",
            "7",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "trash: purged 1 item(s)"
    assert not entries["OLD001"].exists()
    assert (entries["NEW001"] / "fulltext.md").read_text(encoding="utf-8") == "NEW001"
    assert outside.read_text(encoding="utf-8") == "preserve"
