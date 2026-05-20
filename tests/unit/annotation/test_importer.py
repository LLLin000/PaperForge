"""Tests for annotation import/reconciliation logic."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _make_probe_annotation(overrides: dict | None = None) -> dict:
    """Build a synthetic probe-style annotation dict."""
    base = {
        "libraryID": 1,
        "annotationKey": "TESTKEY1",
        "annotationTypeInt": 1,
        "annotationType": "highlight",
        "attachmentKey": "ATTACH01",
        "parentItemKey": "PAPER001",
        "isExternal": False,
        "selectedText": "Test selected text.",
        "comment": "Test comment",
        "color": "#ffd400",
        "pageLabel": "3",
        "sortIndex": "00002|000000|00000",
        "position": {"pageIndex": 2, "rects": [[72, 520, 540, 536]]},
        "tags": ["tag1"],
        "authorName": "",
        "dateAdded": "2025-01-01 00:00:00",
        "dateModified": "2025-01-02 00:00:00",
        "version": 1,
        "attachment_path": "storage:ATTACH01/paper.pdf",
        "attachment_link_mode": 0,
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.fixture
def ann_db(tmp_path: Path):
    """Provide a fresh annotation database with schema applied."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection
    from paperforge.annotation.schema import ensure_schema

    db_path = get_annotations_db_path(tmp_path)
    conn = get_annotations_connection(db_path, read_only=False)
    ensure_schema(conn)
    yield conn
    conn.close()


class TestImporter:
    """Tests for annotation import and reconciliation."""

    def test_first_import_inserts_rows(self, ann_db):
        from paperforge.annotation.importer import run_import

        anns = [_make_probe_annotation()]
        result = run_import(ann_db, anns, source="zotero_db")

        assert result["imported"] == 1
        assert result["updated"] == 0
        assert result["deleted"] == 0

        row = ann_db.execute(
            "SELECT * FROM annotations WHERE zotero_key = 'TESTKEY1'"
        ).fetchone()
        assert row is not None
        assert row["source"] == "zotero_db"
        assert row["sync_state"] == "zotero_synced"
        assert row["selected_text"] == "Test selected text."
        assert row["comment"] == "Test comment"

    def test_reimport_unchanged_is_noop(self, ann_db):
        from paperforge.annotation.importer import run_import

        anns = [_make_probe_annotation()]
        run_import(ann_db, anns, source="zotero_db")
        first_row = ann_db.execute(
            "SELECT updated_at FROM annotations WHERE zotero_key = 'TESTKEY1'"
        ).fetchone()

        # Reimport with same version
        run_import(ann_db, anns, source="zotero_db")
        second_row = ann_db.execute(
            "SELECT updated_at FROM annotations WHERE zotero_key = 'TESTKEY1'"
        ).fetchone()

        assert first_row["updated_at"] == second_row["updated_at"]

    def test_reimport_with_changes_updates(self, ann_db):
        from paperforge.annotation.importer import run_import

        anns = [_make_probe_annotation()]
        run_import(ann_db, anns, source="zotero_db")

        changed = _make_probe_annotation({"comment": "Updated comment", "version": 2})
        result = run_import(ann_db, [changed], source="zotero_db")

        assert result["updated"] == 1
        row = ann_db.execute(
            "SELECT comment, source_version FROM annotations WHERE zotero_key = 'TESTKEY1'"
        ).fetchone()
        assert row["comment"] == "Updated comment"
        assert row["source_version"] == 2

    def test_missing_annotation_soft_deletes(self, ann_db):
        from paperforge.annotation.importer import run_import

        anns = [
            _make_probe_annotation({"annotationKey": "KEEP"}),
            _make_probe_annotation({"annotationKey": "DELETE"}),
        ]
        run_import(ann_db, anns, source="zotero_db")

        # Reimport with only 'KEEP' — 'DELETE' should be soft-deleted
        result = run_import(
            ann_db,
            [_make_probe_annotation({"annotationKey": "KEEP"})],
            source="zotero_db",
        )

        assert result["deleted"] == 1
        deleted_row = ann_db.execute(
            "SELECT deleted_at FROM annotations WHERE zotero_key = 'DELETE'"
        ).fetchone()
        assert deleted_row["deleted_at"] is not None

        keep_row = ann_db.execute(
            "SELECT deleted_at FROM annotations WHERE zotero_key = 'KEEP'"
        ).fetchone()
        assert keep_row["deleted_at"] is None

    def test_does_not_affect_other_sources(self, ann_db):
        """Importing zotero_db annotations should not touch paperforge-source rows."""
        from paperforge.annotation.importer import run_import

        # Insert a local paperforge annotation directly
        local_id = str(uuid.uuid4())
        ann_db.execute(
            """INSERT INTO annotations (id, paper_id, type, source, sync_state, created_at, updated_at)
               VALUES (?, 'PAPER001', 'highlight', 'paperforge', 'local', '2025-01-01', '2025-01-01')""",
            (local_id,),
        )
        ann_db.commit()

        # Run zotero import
        run_import(
            ann_db,
            [_make_probe_annotation()],
            source="zotero_db",
        )

        # Local annotation should remain
        row = ann_db.execute(
            "SELECT source, sync_state FROM annotations WHERE id = ?", (local_id,)
        ).fetchone()
        assert row["source"] == "paperforge"
        assert row["sync_state"] == "local"
