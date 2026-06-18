"""Service-level contract tests for annotation read/export/status queries.

These tests exercise the SQL query patterns and helper functions used
by the annotation CLI commands (list/status/export) *without* invoking
the CLI itself.  This keeps verification fast and focused on data
behaviour rather than argument parsing.

Coverage (Plan 01 Task 2):
- list/export reads only from annotations.db;
- paper filtering returns only the selected paper;
- ordering remains stable by page_index, sort_index, id;
- deleted rows are excluded from list by default but included in export;
- provenance fields (source_library_id, source_annotation_key, ...)
  remain present for Zotero-sourced rows;
- _rows_to_list / _rows_to_export helper contract.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from paperforge.commands.annotation import _rows_to_list, _rows_to_export


# ---------------------------------------------------------------------------
# Seed helpers — share a single row template so field changes stay local
# ---------------------------------------------------------------------------

_NOW = "2024-06-01T12:00:00Z"

# fmt: off
_ANNOTATION_COLS = (
    "id, paper_id, source, source_library_id, "
    "source_annotation_key, source_attachment_key, source_parent_key, "
    "type, page_index, page_label, selected_text, comment, color, "
    "sort_index, tags_json, position_json, selector_json, "
    "sync_state, is_readonly, created_at, updated_at, deleted_at"
)
_PLACEHOLDERS = "?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?"
# fmt: on


def _seed(conn: sqlite3.Connection) -> None:
    """Insert test rows covering two papers, multiple pages, deleted rows."""
    rows = [
        # Paper A — page 0, sort 0 (deleted)
        (
            "zotero:1:ATT_A:A_A1", "PAPER_A", "zotero", "1",
            "A_A1", "ATT_A", "PARENT_A",
            "highlight", 0, "1", "text A1", "comment A1",
            "#ffd400", "0", '["tag-a"]',
            '{"pageIndex":0}', "{}", "imported", 1, _NOW, _NOW, _NOW,
        ),
        # Paper A — page 0, sort 1 (active, second on same page)
        (
            "zotero:1:ATT_A:A_A2", "PAPER_A", "zotero", "1",
            "A_A2", "ATT_A", "PARENT_A",
            "note", 0, "1", "text A2", "",
            "#ff6666", "1", '[]',
            "{}", "{}", "imported", 1, _NOW, _NOW, None,
        ),
        # Paper A — page 1, sort 0 (active)
        (
            "zotero:1:ATT_A:A_A3", "PAPER_A", "zotero", "1",
            "A_A3", "ATT_A", "PARENT_A",
            "highlight", 1, "2", "text A3", "comment A3",
            "#2ea8ff", "0", '["tag-b"]',
            '{"pageIndex":1}', "{}", "imported", 1, _NOW, _NOW, None,
        ),
        # Paper B — page 0, sort 0 (active)
        (
            "zotero:2:ATT_B:B_B1", "PAPER_B", "zotero", "2",
            "B_B1", "ATT_B", "PARENT_B",
            "underline", 0, "1", "text B", "comment B",
            "#00ff00", "0", '[]',
            "{}", "{}", "imported", 1, _NOW, _NOW, None,
        ),
    ]
    conn.executemany(
        f"INSERT INTO annotations ({_ANNOTATION_COLS}) VALUES ({_PLACEHOLDERS})",
        rows,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ann_with_data(ann_db_path: Path) -> sqlite3.Connection:
    """Return a connection to an annotations.db seeded with multi-paper data.
    
    The connection is closed during teardown so the parent ``ann_db_path``
    fixture can safely unlink the temp file.
    """
    conn = sqlite3.connect(str(ann_db_path))
    conn.row_factory = sqlite3.Row
    _seed(conn)
    yield conn
    conn.close()


# ===================================================================
# Paper filtering
# ===================================================================


class TestPaperFilter:
    """list/export must return only the requested paper's annotations."""

    def test_list_returns_only_requested_paper(
        self, ann_with_data: sqlite3.Connection
    ):
        """Querying for PAPER_A returns only PAPER_A rows."""
        rows = ann_with_data.execute(
            """SELECT * FROM annotations
               WHERE paper_id = ? AND deleted_at IS NULL
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        paper_ids = {r["paper_id"] for r in rows}
        assert paper_ids == {"PAPER_A"}, (
            f"Expected only PAPER_A, got {paper_ids}"
        )

    def test_export_returns_only_requested_paper(
        self, ann_with_data: sqlite3.Connection
    ):
        """Export query (includes deleted rows) returns only one paper."""
        rows = ann_with_data.execute(
            """SELECT * FROM annotations
               WHERE paper_id = ?
               ORDER BY page_index, sort_index, id""",
            ("PAPER_B",),
        ).fetchall()
        paper_ids = {r["paper_id"] for r in rows}
        assert paper_ids == {"PAPER_B"}

    def test_different_paper_has_zero_intersection(
        self, ann_with_data: sqlite3.Connection
    ):
        """No single row matches both PAPER_A and PAPER_B."""
        a_rows = set(
            r["id"]
            for r in ann_with_data.execute(
                "SELECT id FROM annotations WHERE paper_id = ?", ("PAPER_A",)
            ).fetchall()
        )
        b_rows = set(
            r["id"]
            for r in ann_with_data.execute(
                "SELECT id FROM annotations WHERE paper_id = ?", ("PAPER_B",)
            ).fetchall()
        )
        assert a_rows.isdisjoint(b_rows), "Papers share annotation rows"


# ===================================================================
# Ordering stability
# ===================================================================


class TestOrdering:
    """Results must be ordered by page_index, then sort_index, then id."""

    def test_list_returns_stable_order(
        self, ann_with_data: sqlite3.Connection
    ):
        """PAPER_A rows sorted by page_index, sort_index, id."""
        rows = ann_with_data.execute(
            """SELECT id, page_index, sort_index FROM annotations
               WHERE paper_id = ? AND deleted_at IS NULL
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        # Expected order:
        #   A_A2  (page=0, sort=1) — A_A1 is deleted, excluded
        #   A_A3  (page=1, sort=0)
        assert len(rows) == 2
        assert rows[0]["id"] == "zotero:1:ATT_A:A_A2"
        assert rows[1]["id"] == "zotero:1:ATT_A:A_A3"

    def test_export_order_unchanged(
        self, ann_with_data: sqlite3.Connection
    ):
        """Export (includes deleted) preserves sort order."""
        rows = ann_with_data.execute(
            """SELECT id, page_index, sort_index FROM annotations
               WHERE paper_id = ?
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        # Expected order (deleted A_A1 has page=0,sort=0 — first):
        #   A_A1  (page=0, sort=0)  — deleted
        #   A_A2  (page=0, sort=1)
        #   A_A3  (page=1, sort=0)
        ids = [r["id"] for r in rows]
        assert ids == [
            "zotero:1:ATT_A:A_A1",
            "zotero:1:ATT_A:A_A2",
            "zotero:1:ATT_A:A_A3",
        ], f"Unexpected export order: {ids}"


# ===================================================================
# Deleted-row behaviour
# ===================================================================


class TestDeletedRows:
    """List excludes deleted; export and status include them."""

    def test_list_excludes_deleted(
        self, ann_with_data: sqlite3.Connection
    ):
        """List query filters out deleted_at IS NOT NULL."""
        rows = ann_with_data.execute(
            """SELECT id FROM annotations
               WHERE paper_id = ? AND deleted_at IS NULL
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        ids = {r["id"] for r in rows}
        assert "zotero:1:ATT_A:A_A1" not in ids, (
            "Deleted row must not appear in list query"
        )

    def test_export_includes_deleted(
        self, ann_with_data: sqlite3.Connection
    ):
        """Export query includes all rows, including deleted."""
        rows = ann_with_data.execute(
            """SELECT id, deleted_at FROM annotations
               WHERE paper_id = ?
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        ids = {r["id"] for r in rows}
        assert "zotero:1:ATT_A:A_A1" in ids, (
            "Deleted row must appear in export query"
        )
        # Verify the deleted row has a non-null deleted_at
        deleted_row = [
            r for r in rows if r["id"] == "zotero:1:ATT_A:A_A1"
        ][0]
        assert deleted_row["deleted_at"] is not None

    def test_status_counts_deleted(
        self, ann_with_data: sqlite3.Connection
    ):
        """Status counts deleted rows separately."""
        total = ann_with_data.execute(
            "SELECT COUNT(*) as c FROM annotations"
        ).fetchone()["c"]
        deleted = ann_with_data.execute(
            "SELECT COUNT(*) as c FROM annotations WHERE deleted_at IS NOT NULL"
        ).fetchone()["c"]
        assert total == 4
        assert deleted == 1


# ===================================================================
# Provenance fields
# ===================================================================


class TestProvenanceFields:
    """Zotero-sourced rows must retain source provenance fields."""

    PROVENANCE_COLS = {
        "source_library_id",
        "source_annotation_key",
        "source_attachment_key",
        "source_parent_key",
        "source_modified_at",
    }

    def test_list_includes_provenance_via_export_helper(
        self, ann_with_data: sqlite3.Connection
    ):
        """_rows_to_export includes all provenance columns."""
        rows = ann_with_data.execute(
            """SELECT * FROM annotations
               WHERE paper_id = ? AND deleted_at IS NULL
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        exported = _rows_to_export(rows)
        for ann in exported:
            for col in self.PROVENANCE_COLS:
                assert col in ann, (
                    f"Provenance column '{col}' missing from export row {ann['id']}"
                )

    def test_list_omits_detail_in_scan_helper(
        self, ann_with_data: sqlite3.Connection
    ):
        """_rows_to_list includes only scan-level fields (no deep provenance)."""
        rows = ann_with_data.execute(
            """SELECT * FROM annotations
               WHERE paper_id = ? AND deleted_at IS NULL
               ORDER BY page_index, sort_index, id""",
            ("PAPER_A",),
        ).fetchall()
        listed = _rows_to_list(rows)
        for ann in listed:
            # Scan fields that SHOULD be present
            for field in ("id", "type", "page", "selected_text", "color", "source"):
                assert field in ann, f"Scan field '{field}' missing"
            # Detail fields that should NOT be in the lightweight list
            for field in ("source_library_id", "source_annotation_key", "source_modified_at",
                          "tags_json", "position_json", "selector_json"):
                assert field not in ann, (
                    f"Scan output should NOT contain '{field}'"
                )


# ===================================================================
# _rows_to_list / _rows_to_export helper contract
# ===================================================================


class TestRowHelpers:
    """Contract tests for the row-to-JSON helper functions."""

    def test_rows_to_list_keys(self, ann_with_data: sqlite3.Connection):
        """_rows_to_list produces expected scan-level keys."""
        rows = ann_with_data.execute(
            "SELECT * FROM annotations LIMIT 1"
        ).fetchall()
        result = _rows_to_list(rows)
        assert len(result) == 1
        ann = result[0]
        expected = {
            "id", "type", "page", "page_label", "selected_text",
            "comment", "color", "source", "is_readonly",
        }
        assert set(ann.keys()) == expected, (
            f"_rows_to_list keys mismatch: expected {expected}, got {set(ann.keys())}"
        )

    def test_rows_to_export_keys(self, ann_with_data: sqlite3.Connection):
        """_rows_to_export produces expected full-export keys."""
        rows = ann_with_data.execute(
            "SELECT * FROM annotations LIMIT 1"
        ).fetchall()
        result = _rows_to_export(rows)
        assert len(result) == 1
        ann = result[0]
        # Core identifier fields
        for col in ("id", "paper_id", "source", "type"):
            assert col in ann
        # Provenance
        for col in ("source_library_id", "source_annotation_key",
                    "source_attachment_key", "source_parent_key",
                    "source_modified_at"):
            assert col in ann
        # Position / tags
        for col in ("tags_json", "position_json", "selector_json"):
            assert col in ann
        # State
        for col in ("sync_state", "is_readonly", "created_at",
                    "updated_at", "deleted_at"):
            assert col in ann

    def test_is_readonly_boolean(self, ann_with_data: sqlite3.Connection):
        """is_readonly is converted to bool in both helpers."""
        rows = ann_with_data.execute(
            "SELECT * FROM annotations LIMIT 1"
        ).fetchall()
        listed = _rows_to_list(rows)
        exported = _rows_to_export(rows)
        assert isinstance(listed[0]["is_readonly"], bool)
        assert isinstance(exported[0]["is_readonly"], bool)

    def test_empty_rows(self):
        """Both helpers return empty list for empty input."""
        assert _rows_to_list([]) == []
        assert _rows_to_export([]) == []


# ===================================================================
# Source counts (status behaviour)
# ===================================================================


class TestSourceCounts:
    """Status source_counts must reflect per-source annotation counts."""

    def test_source_counts_correct(self, ann_with_data: sqlite3.Connection):
        """GROUP BY source returns correct counts."""
        source_rows = ann_with_data.execute(
            "SELECT source, COUNT(*) as c FROM annotations GROUP BY source"
        ).fetchall()
        counts = {r["source"]: r["c"] for r in source_rows}
        assert counts.get("zotero") == 4, (
            f"Expected 4 zotero rows, got {counts}"
        )

    def test_readonly_count(self, ann_with_data: sqlite3.Connection):
        """COUNT of is_readonly=1 returns correct value."""
        ro = ann_with_data.execute(
            "SELECT COUNT(*) as c FROM annotations WHERE is_readonly = 1"
        ).fetchone()["c"]
        assert ro == 4  # All seeded rows are read-only Zotero imports

    def test_distinct_paper_count(self, ann_with_data: sqlite3.Connection):
        """COUNT(DISTINCT paper_id) returns unique papers with annotations."""
        papers = ann_with_data.execute(
            "SELECT COUNT(DISTINCT paper_id) as c FROM annotations"
        ).fetchone()["c"]
        assert papers == 2
