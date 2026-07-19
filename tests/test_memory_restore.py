"""Focused tests for memory restore-backup (Issue #78 repair).

Covers:
- CLI restore-backup subcommand
- Backup validation (integrity_check)
- Corrupt DB preservation
- Atomic replace (os.replace)
- Invalid backup safety (no restore)
- Probe emits restore_backup action
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


def _run_memory_cmd(vault: Path, subcmd: str, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault), "memory", subcmd]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


def _setup_memory_dirs(tmp_path: Path) -> Path:
    """Create paperforge.json and indexes dir, return indexes dir."""
    (tmp_path / "paperforge.json").write_text(
        json.dumps({"system_dir": "99_System"}), encoding="utf-8",
    )
    indexes = tmp_path / "99_System" / "PaperForge" / "indexes"
    indexes.mkdir(parents=True, exist_ok=True)
    return indexes


def _create_valid_db(db_path: Path, paper_count: int = 3) -> None:
    """Create a valid paperforge.db with schema_version and papers."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT)")
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('schema_version', '8')")
    for i in range(paper_count):
        conn.execute("INSERT INTO papers VALUES (?, ?)", (f"KEY{i}", f"Paper {i}"))
    conn.commit()
    conn.close()


class TestMemoryRestoreCli:
    """CLI restore-backup subcommand acceptance."""

    def test_restore_backup_no_backup_file(self, tmp_path: Path) -> None:
        """No backup file -> exits nonzero."""
        indexes = _setup_memory_dirs(tmp_path)
        _create_valid_db(indexes / "paperforge.db")
        result = _run_memory_cmd(tmp_path, "restore-backup", ["--json"])
        data = json.loads(result.stdout)
        assert data["ok"] is False
        assert "No backup found" in data["error"]["message"]

    def test_restore_backup_invalid_backup(self, tmp_path: Path) -> None:
        """Invalid backup (not a database) -> exits nonzero, current DB untouched."""
        indexes = _setup_memory_dirs(tmp_path)
        db_path = indexes / "paperforge.db"
        backup_path = indexes / "paperforge.db.backup"
        _create_valid_db(db_path)
        backup_path.write_text("not a database", encoding="utf-8")
        result = _run_memory_cmd(tmp_path, "restore-backup", ["--json"])
        data = json.loads(result.stdout)
        assert data["ok"] is False
        assert "integrity check" in data["error"]["message"].lower() or "validate backup" in data["error"]["message"].lower() or "not a database" in data["error"]["message"].lower()
        # Current DB still intact
        assert db_path.exists()

    def test_restore_backup_success(self, tmp_path: Path) -> None:
        """Valid backup -> restores successfully, old DB preserved."""
        indexes = _setup_memory_dirs(tmp_path)
        db_path = indexes / "paperforge.db"
        backup_path = indexes / "paperforge.db.backup"

        # Create current DB with old content
        _create_valid_db(db_path, paper_count=1)

        # Create backup with more papers
        _create_valid_db(backup_path, paper_count=5)

        result = _run_memory_cmd(tmp_path, "restore-backup", ["--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert data["data"]["action"] == "restore_backup"

        # Verify restored DB has 5 papers
        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT COUNT(*) FROM papers").fetchone()
        conn.close()
        assert row[0] == 5

        # Verify backup still exists (not consumed)
        assert backup_path.exists()

        # Verify old DB preserved as corrupt snapshot
        corrupt_files = list(indexes.glob("paperforge.corrupt-*.db"))
        assert len(corrupt_files) == 1

    def test_restore_backup_without_current_db(self, tmp_path: Path) -> None:
        """No current DB, just backup -> restores directly."""
        indexes = _setup_memory_dirs(tmp_path)
        db_path = indexes / "paperforge.db"
        backup_path = indexes / "paperforge.db.backup"
        _create_valid_db(backup_path, paper_count=3)

        result = _run_memory_cmd(tmp_path, "restore-backup", ["--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True

        # Verify restored
        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT COUNT(*) FROM papers").fetchone()
        conn.close()
        assert row[0] == 3

        # No corrupt snapshot since there was no current DB
        corrupt_files = list(indexes.glob("paperforge.corrupt-*.db"))
        assert len(corrupt_files) == 0


    def test_replace_failure_leaves_db_and_backup_untouched(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When os.replace fails, current DB and backup remain unchanged (direct call)."""
        import sqlite3
        from paperforge.commands.memory import _restore_backup

        indexes = _setup_memory_dirs(tmp_path)
        db_path = indexes / "paperforge.db"
        backup_path = indexes / "paperforge.db.backup"

        # Create current DB with known content
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT)")
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('schema_version', '8')")
        conn.execute("INSERT INTO papers VALUES ('OLD', 'Old Paper')")
        conn.commit()
        conn.close()
        original_bytes = db_path.read_bytes()

        # Create backup with different content
        conn = sqlite3.connect(str(backup_path))
        conn.execute("CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT)")
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO meta VALUES ('schema_version', '8')")
        conn.execute("INSERT INTO papers VALUES ('NEW', 'New Paper')")
        conn.commit()
        conn.close()
        backup_bytes = backup_path.read_bytes()

        # Monkeypatch os.replace to fail (direct call, so monkeypatch works)
        import os as _os
        def _failing_replace(src, dst):
            raise OSError("simulated replace failure")
        monkeypatch.setattr(_os, "replace", _failing_replace)

        result = _restore_backup(tmp_path)
        assert result.ok is False
        assert "Failed to restore backup" in result.error.message

        # Original DB still intact (byte-identical)
        assert db_path.read_bytes() == original_bytes

        # Backup still intact
        assert backup_path.exists()
        assert backup_path.read_bytes() == backup_bytes

        # Clean up temp files
        for f in indexes.glob("paperforge.restore-*"):
            f.unlink(missing_ok=True)


class TestMemoryRestoreProbe:
    """Probe emits restore_backup when corrupt DB + backup exists."""

    def test_corrupt_db_with_backup_emits_restore(self, tmp_path: Path) -> None:
        """Corrupt DB + valid backup -> restore_backup action."""
        from paperforge.commands import probe as probe_mod

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        indexes = tmp_path / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True, exist_ok=True)

        # Create corrupt DB
        (indexes / "paperforge.db").write_text("not a database", encoding="utf-8")
        # Create valid backup
        _create_valid_db(indexes / "paperforge.db.backup", paper_count=3)

        data = probe_mod.probe_memory(tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["reason"]["code"] == "memory.db_corrupt"
        assert data["action"]["primary"]["verb"] == "restore_backup"
        assert data["action"]["primary"]["command"] == "paperforge memory restore-backup"
        assert data["action"]["primary"]["destructive"] is True
        assert data["action"]["primary"]["confirmation_required"] is True

    def test_corrupt_db_without_backup_emits_rebuild(self, tmp_path: Path) -> None:
        """Corrupt DB without backup -> rebuild action."""
        from paperforge.commands import probe as probe_mod

        (tmp_path / "paperforge.json").write_text(
            json.dumps({"system_dir": "99_System"}), encoding="utf-8",
        )
        indexes = tmp_path / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True, exist_ok=True)

        # Create corrupt DB, no backup
        (indexes / "paperforge.db").write_text("not a database", encoding="utf-8")

        data = probe_mod.probe_memory(tmp_path)
        assert data["capability_state"] == "unavailable"
        assert data["reason"]["code"] == "memory.db_corrupt"
        assert data["action"]["primary"]["verb"] == "run"
        assert data["action"]["primary"]["command"] == "paperforge memory build"
