"""Tests for worker/prune.py -- orphan detection and cleanup."""

from __future__ import annotations

from pathlib import Path

import pytest

import pytest

from tests.conftest import canonical_test_config


@pytest.fixture(autouse=True)
def canonical_vault(tmp_path: Path):
    canonical_test_config(tmp_path)
    return tmp_path


from paperforge.worker.prune import (
    _collect_orphan_candidates,
    _resolve_ocr_dir,
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


class TestResolveOcrDir:
    """_resolve_ocr_dir(vault, key)"""

    def test_resolves_ocr_dir_name_is_key(self, tmp_path: Path) -> None:
        result = _resolve_ocr_dir(tmp_path, "testkey123")
        assert result.name == "testkey123"


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

        monkeypatch.setattr("paperforge.embedding._chroma.delete_paper_vectors", _mock_delete)

        lit = tmp_path / "Resources" / "Literature" / "CS"
        (lit / "key1 - Orphan").mkdir(parents=True)
        fresh_index = {"schema_version": "3", "items": []}

        prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=True)
        assert calls == []

    def test_empty_fresh_index_does_not_crash(self, tmp_path: Path) -> None:
        result = prune_orphan_papers(tmp_path, fresh_index={}, dry_run=True)
        assert result["preview"] == []

    def test_handles_missing_lit_dir(self, tmp_path: Path) -> None:
        no_lit = tmp_path / "NoLiterature"
        no_lit.mkdir(parents=True)
        canonical_test_config(no_lit)
        result = prune_orphan_papers(no_lit, fresh_index={"schema_version": "3", "items": []}, dry_run=False)
        assert result["deleted"] == []

    def test_active_papers_are_not_deleted(self, tmp_path: Path) -> None:
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

    def test_force_cleans_all_db_records(self, tmp_path: Path) -> None:
        """#135: force-prune removes papers/body_units/object_units/lineage
        rows for the residual paper — paper_fts via the AFTER-DELETE
        trigger, body_units_fts via the manual external-content delete."""
        import sqlite3

        from paperforge.memory.db import (
            ensure_vec_extension,
            get_memory_db_path,
        )
        from paperforge.memory.schema import ensure_schema

        db_path = get_memory_db_path(tmp_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        ensure_vec_extension(conn)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO papers (zotero_key, citation_key, title) VALUES (?, '', ?)",
            ("key1", "Orphan Paper"),
        )
        bu_cur = conn.execute(
            "INSERT INTO body_units (unit_id, paper_id, section_path, section_path_json, "
            "section_level, section_title, unit_text, unit_kind, part_ordinal, "
            "page_span_json, block_span_json, token_estimate, indexable, veto_reason, "
            "quality_hints_json, node_id) "
            "VALUES ('u1', 'key1', '/s', '[]', 0, '', 'text', 'paragraph', 0, "
            "'[]', '[]', 10, 1, '', '{}', '')",
        )
        # external-content FTS5: production keeps body_units_fts in sync on
        # insert — mirror that so the prune delete matches a consistent DB.
        conn.execute(
            "INSERT INTO body_units_fts (rowid, unit_id, paper_id, section_path, unit_text) "
            "VALUES (?, 'u1', 'key1', '/s', 'text')",
            (bu_cur.lastrowid,),
        )
        conn.execute(
            "INSERT INTO object_units (unit_id, paper_id, section_path, object_kind, "
            "object_label, caption_text, nearby_body_text, page_span_json, "
            "block_span_json, token_estimate, indexable, veto_reason, "
            "quality_hints_json, node_id, section_path_json) "
            "VALUES ('o1', 'key1', '/s', 'figure', '', '', '', '[]', '[]', 5, 1, '', '{}', '', '[]')",
        )
        conn.execute(
            "INSERT INTO lineage (paper_id, layer, identity, updated_at) "
            "VALUES ('key1', 'retrieval', 'x', datetime('now'))",
        )
        conn.commit()
        conn.close()

        lit = tmp_path / "Resources" / "Literature" / "CS"
        (lit / "key1 - Orphan").mkdir(parents=True)
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)
        assert result["deleted"] == ["key1"]
        print("COUNTS:", result["counts"])

        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            assert conn.execute("SELECT COUNT(*) FROM papers WHERE zotero_key='key1'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM paper_fts WHERE zotero_key='key1'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='key1'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM body_units_fts WHERE paper_id='key1'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM object_units WHERE paper_id='key1'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM lineage WHERE paper_id='key1'").fetchone()[0] == 0
        finally:
            conn.close()
