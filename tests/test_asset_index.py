"""Tests for asset_index.py — envelope format, atomic writes, locking.

Covers: get_index_path, build_envelope, atomic_write_index, build_index
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import filelock
import pytest

from paperforge.worker.asset_index import (
    CURRENT_SCHEMA_VERSION,
    INDEX_FILENAME,
    LOCK_TIMEOUT,
    atomic_write_index,
    build_envelope,
    build_index,
    get_index_path,
    summarize_index,
)


class TestGetIndexPath:
    """get_index_path(vault) -> Path"""

    def test_returns_path_suffix(self, tmp_path: Path) -> None:
        """Index path must end with indexes/formal-library.json."""
        vault = _minimal_vault(tmp_path)
        result = get_index_path(vault)
        assert isinstance(result, Path)
        assert result.name == INDEX_FILENAME
        assert result.parent.name == "indexes"

    def test_path_uses_paperforge_dir(self, tmp_path: Path) -> None:
        """Index path is inside the PaperForge system directory."""
        vault = _minimal_vault(tmp_path)
        result = get_index_path(vault)
        assert "PaperForge" in result.parts
        assert "indexes" in result.parts


class TestBuildEnvelope:
    """build_envelope(items) -> dict"""

    def test_empty_list(self) -> None:
        """Empty items list produces schema_version='2', paper_count=0."""
        envelope = build_envelope([])
        assert envelope["schema_version"] == CURRENT_SCHEMA_VERSION
        assert envelope["paper_count"] == 0
        assert envelope["items"] == []
        assert "generated_at" in envelope
        assert envelope["generated_at"].endswith("+08:00") or envelope["generated_at"].endswith("Z")

    def test_with_items(self) -> None:
        """Envelope with 3 items has matching paper_count."""
        items = [
            {"zotero_key": "AAA", "title": "Paper A"},
            {"zotero_key": "BBB", "title": "Paper B"},
            {"zotero_key": "CCC", "title": "Paper C"},
        ]
        envelope = build_envelope(items)
        assert envelope["paper_count"] == 3
        assert envelope["items"] == items
        assert envelope["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_paper_count_matches_length(self) -> None:
        """paper_count always equals len(items) regardless of content."""
        for n in (0, 1, 5, 100):
            items = [{"id": i} for i in range(n)]
            envelope = build_envelope(items)
            assert envelope["paper_count"] == n
            assert len(envelope["items"]) == n

    def test_generated_at_is_beijing_time(self) -> None:
        """generated_at ends with +08:00 (Beijing time) and is parseable."""
        envelope = build_envelope([])
        ts = envelope["generated_at"]
        assert ts.endswith("+08:00")
        # Should be ISO-format date (rough check): YYYY-MM-DDT...
        assert "T" in ts


class TestAtomicWriteIndex:
    """atomic_write_index(path, data) -> None"""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Writes valid JSON to the target file."""
        target = tmp_path / "indexes" / "formal-library.json"
        data = {"schema_version": "2", "paper_count": 0, "items": []}
        atomic_write_index(target, data)
        assert target.exists()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data

    def test_content_is_correct(self, tmp_path: Path) -> None:
        """Written content matches input data exactly."""
        target = tmp_path / "out.json"
        data = {"items": [{"key": "ABC"}], "paper_count": 1}
        atomic_write_index(target, data)
        assert json.loads(target.read_text(encoding="utf-8")) == data

    def test_no_partial_file_on_interrupt(self, monkeypatch, tmp_path: Path) -> None:
        """Simulate a crash after NamedTemporaryFile write but before os.replace.

        The target file should either contain the old content or not exist
        — never a half-written partial file.
        """
        target = tmp_path / "safe.json"
        original_replace = os.replace
        calls = []

        def _failing_replace(src, dst):
            calls.append((src, dst))
            raise OSError("Simulated crash during replace")

        monkeypatch.setattr(os, "replace", _failing_replace)

        with pytest.raises(OSError, match="Simulated crash"):
            atomic_write_index(target, {"key": "should-not-appear"})

        # Temp file should have been cleaned up
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0, f"Temp file not cleaned up: {temp_files}"

        # Target file should not exist (never completed os.replace)
        assert not target.exists() or target.read_text(encoding="utf-8") == ""

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Creates intermediate directories automatically."""
        target = tmp_path / "a" / "b" / "c" / "index.json"
        atomic_write_index(target, {"key": "val"})
        assert target.exists()
        assert json.loads(target.read_text(encoding="utf-8")) == {"key": "val"}

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Overwrites an existing file atomically."""
        target = tmp_path / "existing.json"
        target.write_text(json.dumps({"old": "data"}), encoding="utf-8")
        atomic_write_index(target, {"new": "data"})
        assert json.loads(target.read_text(encoding="utf-8")) == {"new": "data"}

    def test_lock_timeout(self, tmp_path: Path) -> None:
        """Second concurrent writer raises filelock.Timeout."""
        target = tmp_path / "locked.json"
        lock_path = target.with_suffix(".json.lock")
        held = threading.Event()
        done = threading.Event()

        def _holder():
            lock = filelock.FileLock(lock_path, timeout=30)
            with lock:
                held.set()
                # Hold the lock longer than LOCK_TIMEOUT
                done.wait(timeout=15)

        t = threading.Thread(target=_holder, daemon=True)
        t.start()
        held.wait(timeout=5)  # Wait for holder to acquire

        # Now try to write — should time out
        with pytest.raises(filelock.Timeout):
            atomic_write_index(target, {"will": "timeout"})

        done.set()
        t.join(timeout=5)


class TestBuildIndexEmpty:
    """build_index(vault, verbose=False) with empty exports"""

    def test_empty_exports_dir(self, tmp_path: Path) -> None:
        """Empty exports directory returns 0 and writes empty envelope."""
        vault = _minimal_vault(tmp_path)

        # Create empty exports directory
        exports_dir = vault / "99_System" / "PaperForge" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        # Create domain config so load_domain_config doesn't crash
        _ensure_domain_config(vault)

        count = build_index(vault, verbose=False)
        assert count == 0

        # Verify empty envelope was written
        index_path = get_index_path(vault)
        assert index_path.exists()
        envelope = json.loads(index_path.read_text(encoding="utf-8"))
        assert envelope["schema_version"] == CURRENT_SCHEMA_VERSION
        assert envelope["paper_count"] == 0
        assert envelope["items"] == []

    def test_absent_exports_dir(self, tmp_path: Path) -> None:
        """No exports directory returns 0 and writes empty envelope."""
        vault = _minimal_vault(tmp_path)

        # Do NOT create exports dir — it should not exist
        _ensure_domain_config(vault)

        count = build_index(vault, verbose=False)
        assert count == 0

        index_path = get_index_path(vault)
        assert index_path.exists()
        envelope = json.loads(index_path.read_text(encoding="utf-8"))
        assert envelope["paper_count"] == 0


class TestSummarizeIndex:
    """summarize_index(vault) -> dict | None"""

    def _write_envelope(self, vault: Path, items: list[dict]) -> None:
        """Helper: write an envelope-format index to the vault."""
        from paperforge.worker.asset_index import atomic_write_index, build_envelope

        idx_path = get_index_path(vault)
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        envelope = build_envelope(items)
        atomic_write_index(idx_path, envelope)

    def test_summarize_index_returns_aggregates(self, tmp_path: Path) -> None:
        """3 items at different lifecycle states produce correct counts."""
        vault = _minimal_vault(tmp_path)
        items = [
            {
                "zotero_key": "AAA",
                "lifecycle": "indexed",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "healthy",
                    "asset_health": "healthy",
                },
                "maturity": {"level": 1},
            },
            {
                "zotero_key": "BBB",
                "lifecycle": "fulltext_ready",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "PDF path missing",
                    "asset_health": "healthy",
                },
                "maturity": {"level": 3},
            },
            {
                "zotero_key": "CCC",
                "lifecycle": "ai_context_ready",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "healthy",
                    "asset_health": "healthy",
                },
                "maturity": {"level": 6},
            },
        ]
        self._write_envelope(vault, items)
        result = summarize_index(vault)
        assert result is not None
        assert result["paper_count"] == 3
        assert result["lifecycle_level_counts"]["indexed"] == 1
        assert result["lifecycle_level_counts"]["fulltext_ready"] == 1
        assert result["lifecycle_level_counts"]["ai_context_ready"] == 1
        # Unhealthy in note_health due to "PDF path missing"
        assert result["health_aggregate"]["note_health"]["unhealthy"] == 1
        assert result["health_aggregate"]["note_health"]["healthy"] == 2
        assert result["maturity_distribution"]["1"] == 1
        assert result["maturity_distribution"]["3"] == 1
        assert result["maturity_distribution"]["6"] == 1

    def test_summarize_index_missing_index_returns_none(self, tmp_path: Path) -> None:
        """When index file does not exist, returns None."""
        vault = _minimal_vault(tmp_path)
        # Do NOT write an index file
        result = summarize_index(vault)
        assert result is None

    def test_summarize_index_legacy_format_returns_none(self, tmp_path: Path) -> None:
        """When index is a bare list (legacy), returns None."""
        vault = _minimal_vault(tmp_path)
        idx_path = get_index_path(vault)
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        # Legacy format: bare list
        idx_path.write_text(json.dumps([{"zotero_key": "AAA"}]), encoding="utf-8")
        result = summarize_index(vault)
        assert result is None

    def test_summarize_index_empty_items_all_zeros(self, tmp_path: Path) -> None:
        """When items list is empty, all counts are zero."""
        vault = _minimal_vault(tmp_path)
        self._write_envelope(vault, [])
        result = summarize_index(vault)
        assert result is not None
        assert result["paper_count"] == 0
        for key in ("indexed", "pdf_ready", "fulltext_ready", "deep_read_done", "ai_context_ready"):
            assert result["lifecycle_level_counts"][key] == 0
        for dim in ("pdf_health", "ocr_health", "note_health", "asset_health"):
            assert result["health_aggregate"][dim]["healthy"] == 0
            assert result["health_aggregate"][dim]["unhealthy"] == 0
        for level in range(1, 7):
            assert result["maturity_distribution"][str(level)] == 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with paperforge.json for path resolution."""
    vault = tmp_path / "test_vault"
    vault.mkdir(parents=True, exist_ok=True)
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                    "base_dir": "05_Bases",
                    "skill_dir": ".opencode/skills",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return vault


def _ensure_domain_config(vault: Path) -> None:
    """Create domain config so load_domain_config returns a valid configuration."""
    from paperforge.config import paperforge_paths as _pp

    paths = _pp(vault)
    config_dir = paths["paperforge"] / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "domain-collections.json"
    config_path.write_text(
        json.dumps(
            {
                "collections": {},
                "domains": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
