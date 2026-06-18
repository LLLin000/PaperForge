"""Tests for Zotero annotation importer/reconciliation (TDD — RED first).

Tests verify:
- Importing new Zotero annotations inserts rows into annotations.
- Re-importing the same identity updates content instead of duplicating.
- Missing rows from the latest import are marked stale only within the
  requested paper/source/library/parent/attachment scope.
- Rows for a different paper_id, library_id, or attachment are untouched.
- Local PaperForge rows (source='paperforge') are untouched.
- Imported rows keep is_readonly=1.
- Import result counts are correct.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from paperforge.annotation.importer import import_zotero_annotations_for_paper
from paperforge.annotation.zotero_probe import open_zotero_readonly, zotero_snapshot

from .conftest import open_ann


# ---------------------------------------------------------------------------
# Import helper (wraps the target function for test ergonomics)
# ---------------------------------------------------------------------------


def _do_import(
    zotero_path: Path,
    annotations_db: Path,
    paper_id: str = "paper001",
    library_id: int = 1,
    parent_item_id: int = 1,
    parent_item_key: str = "PAPER001",
    attachment_item_id: int = 2,
    attachment_item_key: str = "ATTACH01",
):
    """Convenience wrapper: snapshot → open → import → close."""
    with zotero_snapshot(zotero_path) as snap:
        zconn = open_zotero_readonly(snap)
        result = import_zotero_annotations_for_paper(
            zotero_conn=zconn,
            annotations_db_path=annotations_db,
            paper_id=paper_id,
            library_id=library_id,
            parent_item_id=parent_item_id,
            parent_item_key=parent_item_key,
            attachment_item_id=attachment_item_id,
            attachment_item_key=attachment_item_key,
        )
        zconn.close()
    return result


# ===================================================================
# Tests
# ===================================================================


class TestInsertNew:
    """Inserting new Zotero annotations from scratch."""

    def test_import_inserts_new_annotations(self, zotero_full_path: Path, ann_db_path: Path):
        """Importing from ATTACH01 should produce 2 rows in annotations."""
        result = _do_import(zotero_full_path, ann_db_path)
        assert result.inserted == 2
        assert result.updated == 0
        assert result.unchanged == 0
        assert result.total == 2

        conn = open_ann(ann_db_path)
        rows = conn.execute(
            "SELECT id, paper_id, source, type, sort_index FROM annotations ORDER BY sort_index"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0][1] == "paper001"
        assert rows[0][2] == "zotero"
        assert rows[0][3] == "highlight"

    def test_imported_rows_have_expected_fields(self, zotero_full_path: Path, ann_db_path: Path):
        """Imported rows should have key fields populated correctly."""
        result = _do_import(zotero_full_path, ann_db_path)
        assert result.inserted == 2

        conn = open_ann(ann_db_path)
        rows = conn.execute(
            "SELECT id, source_library_id, source_annotation_key, "
            "source_attachment_key, source_parent_key, "
            "selected_text, comment, color, page_label, "
            "is_readonly, sync_state FROM annotations ORDER BY sort_index"
        ).fetchall()
        conn.close()
        assert len(rows) == 2

        row0 = dict(rows[0])
        assert row0["id"] == "zotero:1:ATTACH01:ANNT001"
        assert row0["source_library_id"] == "1"
        assert row0["source_annotation_key"] == "ANNT001"
        assert row0["source_attachment_key"] == "ATTACH01"
        assert row0["source_parent_key"] == "PAPER001"
        assert row0["is_readonly"] == 1
        assert row0["sync_state"] == "imported"
        assert row0["selected_text"] == "significant result"

        row1 = dict(rows[1])
        assert row1["id"] == "zotero:1:ATTACH01:ANNT002"
        assert row1["source_annotation_key"] == "ANNT002"
        assert row1["selected_text"] == "another observation"

    def test_imported_rows_have_tags(self, zotero_full_path: Path, ann_db_path: Path):
        """Tags from the Zotero fixture should be preserved."""
        _do_import(zotero_full_path, ann_db_path)
        conn = open_ann(ann_db_path)
        row = conn.execute(
            "SELECT tags_json FROM annotations WHERE source_annotation_key = 'ANNT001'"
        ).fetchone()
        conn.close()
        assert row is not None
        import json
        tags = json.loads(row["tags_json"])
        assert "important" in tags


class TestReimportUpdates:
    """Re-importing the same Zotero identity updates rather than duplicating."""

    def test_reimport_preserves_row_count(self, zotero_full_path: Path, ann_db_path: Path):
        """Importing twice should produce 2 total rows (not 4)."""
        r1 = _do_import(zotero_full_path, ann_db_path)
        assert r1.inserted == 2

        r2 = _do_import(zotero_full_path, ann_db_path)
        assert r2.inserted == 0
        assert r2.updated == 0
        assert r2.unchanged == 2
        assert r2.total == 2

        conn = open_ann(ann_db_path)
        count = conn.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]
        conn.close()
        assert count == 2

    def test_reimport_updates_modified_content(self, zotero_full_path: Path, ann_db_path: Path):
        """When Zotero annotation text/comment changes, re-import should update."""
        r1 = _do_import(zotero_full_path, ann_db_path)
        assert r1.inserted == 2

        # Modify annotation ANNT001 in the Zotero fixture
        mod_conn = sqlite3.connect(str(zotero_full_path))
        mod_conn.execute(
            "UPDATE itemAnnotations SET text = ?, comment = ? WHERE itemID = ?",
            ("updated text", "updated comment", 3),
        )
        mod_conn.commit()
        mod_conn.close()

        r2 = _do_import(zotero_full_path, ann_db_path)
        assert r2.updated == 1
        assert r2.unchanged == 1
        assert r2.total == 2

        conn = open_ann(ann_db_path)
        row = conn.execute(
            "SELECT selected_text, comment FROM annotations WHERE source_annotation_key = 'ANNT001'"
        ).fetchone()
        conn.close()
        assert row["selected_text"] == "updated text"
        assert row["comment"] == "updated comment"

    def test_reimport_refreshes_updated_at(self, zotero_full_path: Path, ann_db_path: Path):
        """Re-import should update updated_at while preserving created_at."""
        r1 = _do_import(zotero_full_path, ann_db_path)
        assert r1.inserted == 2

        conn = open_ann(ann_db_path)
        row1 = conn.execute(
            "SELECT created_at, updated_at FROM annotations WHERE source_annotation_key = 'ANNT001'"
        ).fetchone()
        conn.close()
        orig_created = row1["created_at"]
        orig_updated = row1["updated_at"]

        # Modify and re-import
        mod_conn = sqlite3.connect(str(zotero_full_path))
        mod_conn.execute(
            "UPDATE itemAnnotations SET text = 'modified' WHERE itemID = 3"
        )
        mod_conn.commit()
        mod_conn.close()

        r2 = _do_import(zotero_full_path, ann_db_path)
        assert r2.updated == 1

        conn = open_ann(ann_db_path)
        row2 = conn.execute(
            "SELECT created_at, updated_at FROM annotations WHERE source_annotation_key = 'ANNT001'"
        ).fetchone()
        conn.close()
        assert row2["created_at"] == orig_created
        assert row2["updated_at"] >= orig_updated


class TestStaleMarking:
    """Stale (soft-delete) reconciliation is scoped to the import scope."""

    def test_stale_marked_when_annotation_removed_from_zotero(
        self, zotero_full_path: Path, zotero_reduced_path: Path, ann_db_path: Path
    ):
        """Annotations present in the first import but absent in the second are
        marked as stale (deleted_at is set)."""
        r1 = _do_import(zotero_full_path, ann_db_path)
        assert r1.inserted == 2

        r2 = _do_import(zotero_reduced_path, ann_db_path)
        assert r2.unchanged == 1
        assert r2.stale == 1
        assert r2.total == 2

        conn = open_ann(ann_db_path)
        stale_row = conn.execute(
            "SELECT id, deleted_at FROM annotations WHERE source_annotation_key = 'ANNT002'"
        ).fetchone()
        active_row = conn.execute(
            "SELECT deleted_at FROM annotations WHERE source_annotation_key = 'ANNT001'"
        ).fetchone()
        conn.close()

        assert stale_row["deleted_at"] is not None, "ANNT002 should be stale"
        assert active_row["deleted_at"] is None, "ANNT001 should remain active"

    def test_stale_row_reappears_on_reimport(
        self, zotero_full_path: Path, zotero_reduced_path: Path, ann_db_path: Path
    ):
        """A formerly stale row should have deleted_at set to NULL when it
        returns in a later import."""
        r1 = _do_import(zotero_full_path, ann_db_path)
        assert r1.inserted == 2

        r2 = _do_import(zotero_reduced_path, ann_db_path)
        assert r2.stale == 1

        r3 = _do_import(zotero_full_path, ann_db_path)
        assert r3.updated == 1  # ANNT002 is restored (un-staled)
        assert r3.stale == 0

        conn = open_ann(ann_db_path)
        row = conn.execute(
            "SELECT deleted_at FROM annotations WHERE source_annotation_key = 'ANNT002'"
        ).fetchone()
        conn.close()
        assert row["deleted_at"] is None, "Reappeared row should not be stale"


class TestScopeIsolation:
    """Stale marking and related operations must not leak across scope boundaries."""

    def test_other_paper_untouched(self, zotero_full_path: Path, ann_db_path: Path):
        """Annotations for a different paper_id must not be stale-marked."""
        _do_import(zotero_full_path, ann_db_path, paper_id="paper001")
        _do_import(
            zotero_full_path, ann_db_path,
            paper_id="paper002",
            library_id=2,
            parent_item_id=7,
            parent_item_key="PAPER002",
            attachment_item_id=8,
            attachment_item_key="ATTACH03",
        )

        conn = open_ann(ann_db_path)
        paper1_rows = conn.execute(
            "SELECT COUNT(*) FROM annotations WHERE paper_id = 'paper001' AND deleted_at IS NULL"
        ).fetchone()[0]
        paper2_rows = conn.execute(
            "SELECT COUNT(*) FROM annotations WHERE paper_id = 'paper002' AND deleted_at IS NULL"
        ).fetchone()[0]
        conn.close()

        assert paper1_rows == 2
        assert paper2_rows == 1

    def test_other_library_untouched(self, zotero_full_path: Path, ann_db_path: Path):
        """Annotations from a different Zotero library must survive import."""
        _do_import(zotero_full_path, ann_db_path)

        conn = open_ann(ann_db_path)
        lib1_rows = conn.execute(
            "SELECT COUNT(*) FROM annotations WHERE source_library_id = '1'"
        ).fetchone()[0]
        conn.close()
        assert lib1_rows == 2

    def test_other_attachment_untouched(self, zotero_full_path: Path, ann_db_path: Path):
        """Annotations for other attachments must not be stale-marked."""
        _do_import(zotero_full_path, ann_db_path)

        conn = open_ann(ann_db_path)
        rows = conn.execute(
            "SELECT source_attachment_key, deleted_at FROM annotations ORDER BY sort_index"
        ).fetchall()
        conn.close()
        assert len(rows) == 2

    def test_local_rows_untouched(self, zotero_full_path: Path, ann_db_path: Path):
        """Rows with source='paperforge' must never be stale-marked by Zotero imports."""
        conn = open_ann(ann_db_path)
        conn.execute(
            "INSERT INTO annotations (id, paper_id, source, type, created_at, updated_at) "
            "VALUES ('local:001', 'paper001', 'paperforge', 'highlight', '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()

        _do_import(zotero_full_path, ann_db_path)

        conn = open_ann(ann_db_path)
        row = conn.execute(
            "SELECT source, deleted_at FROM annotations WHERE id = 'local:001'"
        ).fetchone()
        conn.close()
        assert row["source"] == "paperforge"
        assert row["deleted_at"] is None, "local rows must not be stale-marked"


class TestReadOnly:
    """Imported Zotero rows are read-only in PaperForge."""

    def test_is_readonly_set(self, zotero_full_path: Path, ann_db_path: Path):
        """All imported rows must have is_readonly=1."""
        _do_import(zotero_full_path, ann_db_path)

        conn = open_ann(ann_db_path)
        rows = conn.execute(
            "SELECT is_readonly FROM annotations WHERE source = 'zotero'"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        for row in rows:
            assert row["is_readonly"] == 1


class TestImportResultCounts:
    """ImportResult exposes accurate counts for later CLI JSON."""

    def test_counts_after_insert(self, zotero_full_path: Path, ann_db_path: Path):
        """Fresh import returns correct inserted and total counts."""
        result = _do_import(zotero_full_path, ann_db_path)
        assert result.inserted == 2
        assert result.updated == 0
        assert result.stale == 0
        assert result.skipped == 0
        assert result.unchanged == 0
        assert result.total == 2

    def test_counts_after_update(self, zotero_full_path: Path, ann_db_path: Path):
        """Modified re-import returns correct updated count."""
        _do_import(zotero_full_path, ann_db_path)

        mod_conn = sqlite3.connect(str(zotero_full_path))
        mod_conn.execute("UPDATE itemAnnotations SET comment = 'changed' WHERE itemID = 3")
        mod_conn.execute("UPDATE itemAnnotations SET comment = 'also changed' WHERE itemID = 4")
        mod_conn.commit()
        mod_conn.close()

        result = _do_import(zotero_full_path, ann_db_path)
        assert result.inserted == 0
        assert result.updated == 2
        assert result.unchanged == 0
        assert result.total == 2

    def test_counts_with_stale_and_skipped(self, zotero_full_path: Path, zotero_reduced_path: Path, ann_db_path: Path):
        """Re-import with removed annotations returns correct stale and unchanged counts."""
        _do_import(zotero_full_path, ann_db_path)

        result = _do_import(zotero_reduced_path, ann_db_path)
        assert result.unchanged == 1
        assert result.stale == 1
        assert result.total == 2
