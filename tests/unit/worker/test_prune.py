"""Tests for worker/prune.py -- orphan detection and cleanup."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperforge.worker.prune import (
    _collect_orphan_candidates,
    prune_orphan_papers,
)


class TestCollectOrphanCandidates:
    """_collect_orphan_candidates(lit_dir, fresh_keys) -> list[dict]"""

    def test_returns_no_orphans_when_all_match(self, tmp_path: Path) -> None:
        lit = tmp_path / "Literature" / "CS"
        (lit / "key1 - Paper One").mkdir(parents=True)
        (lit / "key2 - Paper Two").mkdir(parents=True)
        fresh_keys = {"key1", "key2"}
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert result == []

    def test_returns_orphan_for_missing_key(self, tmp_path: Path) -> None:
        lit = tmp_path / "Literature"
        ws = lit / "CS" / "key1 - Orphan Paper"
        ws.mkdir(parents=True)
        fresh_keys = set()
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert len(result) == 1
        assert result[0]["key"] == "key1"
        assert result[0]["workspace_dir"] == ws

    def test_skips_non_workspace_dirs(self, tmp_path: Path) -> None:
        lit = tmp_path / "Literature"
        domain = lit / "CS"
        domain.mkdir(parents=True)
        (domain / "orphan_file.md").write_text("not a dir")
        (domain / "random_dir").mkdir()
        fresh_keys = set()
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert result == []

    def test_skips_dirs_without_dash_space_pattern(self, tmp_path: Path) -> None:
        lit = tmp_path / "Literature"
        domain = lit / "CS"
        domain.mkdir(parents=True)
        (domain / "justakey").mkdir()
        (domain / "key-with-dashes-no-slug").mkdir()
        fresh_keys = set()
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert result == []

    def test_handles_multiple_domains(self, tmp_path: Path) -> None:
        lit = tmp_path / "Literature"
        (lit / "CS" / "key1 - Paper One").mkdir(parents=True)
        (lit / "Med" / "key2 - Paper Two").mkdir(parents=True)
        (lit / "Sport" / "key3 - Paper Three").mkdir(parents=True)
        fresh_keys = {"key1"}
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert len(result) == 2
        returned_keys = {c["key"] for c in result}
        assert returned_keys == {"key2", "key3"}


class TestPruneOrphanPapers:
    """prune_orphan_papers(vault, fresh_index, dry_run)"""

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        lit = tmp_path / "Resources" / "Literature" / "CS"
        ws = lit / "key1 - Orphan"
        ws.mkdir(parents=True)
        note = ws / "note.md"
        note.write_text("hello")
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=True)

        assert len(result["preview"]) == 1
        assert note.exists()

    def test_force_deletes_workspace(self, tmp_path: Path) -> None:
        lit = tmp_path / "Resources" / "Literature" / "CS"
        ws = lit / "key1 - Orphan"
        ws.mkdir(parents=True)
        (ws / "note.md").write_text("hello")
        (ws / "ai").mkdir()
        (ws / "ai" / "discussion.md").write_text("some discussion")
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)

        assert result["deleted"] == ["key1"]
        assert not ws.exists()

    def test_force_deletes_ocr_dir(self, tmp_path: Path) -> None:
        ocr = tmp_path / "System" / "PaperForge" / "ocr" / "key1"
        ocr.mkdir(parents=True)
        (ocr / "fulltext.md").write_text("fulltext")
        lit = tmp_path / "Resources" / "Literature" / "CS"
        (lit / "key1 - Orphan").mkdir(parents=True)
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)

        assert result["deleted"] == ["key1"]
        assert not ocr.exists()

    def test_vectors_not_deleted_in_dry_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = []

        def _mock_delete(vault, key):
            calls.append(key)
            return 0

        monkeypatch.setattr("paperforge.worker.prune.delete_paper_vectors", _mock_delete)

        lit = tmp_path / "Resources" / "Literature" / "CS"
        (lit / "key1 - Orphan").mkdir(parents=True)
        fresh_index = {"schema_version": "3", "items": []}

        prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=True)
        assert calls == []

    def test_orphan_not_in_fresh_index_is_skipped(self, tmp_path: Path) -> None:
        lit = tmp_path / "Resources" / "Literature" / "CS"
        ws = lit / "key1 - Active Paper"
        ws.mkdir(parents=True)
        fresh_index = {
            "schema_version": "3",
            "items": [{"zotero_key": "key1", "title": "Active Paper"}],
        }

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)
        assert result["deleted"] == []
        assert ws.exists()
