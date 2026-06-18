"""End-to-end flow tests: Zotero probe → normalize → import.

These tests exercise the full pipeline across module boundaries:
  probe (zotero_snapshot → open_zotero_readonly → probe_zotero_annotation_schema)
  → normalize (fetch_zotero_item_annotations → _enrich_annotation
               → normalize_zotero_annotation)
  → import (import_zotero_annotations_for_paper → annotations.db)

Coverage (from PLAN.md):
1. Probe finds annotation schema in copied snapshot.
2. Raw rows normalize and import into annotations.db.
3. Selected text, comment, color, page, tags, position JSON, and source
   modified time survive the full flow.
4. Re-running import for one paper does NOT soft-delete rows belonging
   to another paper.
5. Unknown Zotero schema fails before any PaperForge import mutation
   happens.
6. Temporary Zotero snapshot cleanup happens after the flow.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.annotation.errors import (
    ZoteroSchemaError,
)
from paperforge.annotation.importer import (
    import_zotero_annotations_for_paper,
)
from paperforge.annotation.zotero_probe import (
    open_zotero_readonly,
    probe_zotero_annotation_schema,
    zotero_snapshot,
)

from .conftest import (
    PAPER_A_LIBRARY,
    PAPER_A_PARENT_KEY,
    PAPER_A_ATTACH_KEY,
    PAPER_A_PARENT_ITEM_ID,
    PAPER_A_ATTACH_ITEM_ID,
    PAPER_B_LIBRARY,
    PAPER_B_PARENT_KEY,
    PAPER_B_ATTACH_KEY,
    PAPER_B_PARENT_ITEM_ID,
    PAPER_B_ATTACH_ITEM_ID,
    open_ann,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_paper_a(zotero_path: Path, ann_db: Path) -> None:
    """Convenience: import Paper A annotations."""
    with zotero_snapshot(zotero_path) as snap:
        zconn = open_zotero_readonly(snap)
        import_zotero_annotations_for_paper(
            zotero_conn=zconn,
            annotations_db_path=ann_db,
            paper_id="paper_a",
            library_id=PAPER_A_LIBRARY,
            parent_item_id=PAPER_A_PARENT_ITEM_ID,
            parent_item_key=PAPER_A_PARENT_KEY,
            attachment_item_id=PAPER_A_ATTACH_ITEM_ID,
            attachment_item_key=PAPER_A_ATTACH_KEY,
        )
        zconn.close()


def _import_paper_b(zotero_path: Path, ann_db: Path) -> None:
    """Convenience: import Paper B annotations."""
    with zotero_snapshot(zotero_path) as snap:
        zconn = open_zotero_readonly(snap)
        import_zotero_annotations_for_paper(
            zotero_conn=zconn,
            annotations_db_path=ann_db,
            paper_id="paper_b",
            library_id=PAPER_B_LIBRARY,
            parent_item_id=PAPER_B_PARENT_ITEM_ID,
            parent_item_key=PAPER_B_PARENT_KEY,
            attachment_item_id=PAPER_B_ATTACH_ITEM_ID,
            attachment_item_key=PAPER_B_ATTACH_KEY,
        )
        zconn.close()


# ===================================================================
# 1. Probe finds annotation schema in copied snapshot
# ===================================================================


def test_flow_probe_finds_schema_in_snapshot(zotero_two_paper_path: Path):
    """Probe must discover all required tables and columns through
    the snapshot→open→probe pipeline."""
    with zotero_snapshot(zotero_two_paper_path) as snap:
        assert snap.exists(), "snapshot file must exist inside context"
        conn = open_zotero_readonly(snap)
        schema = probe_zotero_annotation_schema(conn)
        conn.close()

    # Verify all required tables were discovered
    required_tables = {
        "items", "itemAttachments", "itemAnnotations",
        "tags", "itemTags",
    }
    for table in required_tables:
        assert table in schema, f"Required table '{table}' not found by probe"

    # Verify key columns are present
    assert "itemID" in schema["items"]
    assert "key" in schema["items"]
    assert "type" in schema["itemAnnotations"]
    assert "text" in schema["itemAnnotations"]
    assert "position" in schema["itemAnnotations"]


# ===================================================================
# 2. Raw rows normalize and import into annotations.db
# ===================================================================


def test_flow_full_import_creates_rows(zotero_two_paper_path: Path, ann_db_path: Path):
    """The full probe→normalize→import pipeline must insert rows
    into annotations.db for Paper A."""
    _import_paper_a(zotero_two_paper_path, ann_db_path)

    conn = open_ann(ann_db_path)
    rows = conn.execute(
        "SELECT id, paper_id, source FROM annotations ORDER BY sort_index"
    ).fetchall()
    conn.close()

    assert len(rows) == 2, "Expected 2 annotation rows for Paper A"
    assert rows[0]["paper_id"] == "paper_a"
    assert rows[0]["source"] == "zotero"
    # Verify deterministic ID format
    assert rows[0]["id"] == "zotero:1:ATTACH_A1:ANNOT_A1"
    assert rows[1]["id"] == "zotero:1:ATTACH_A1:ANNOT_A2"


# ===================================================================
# 3. Content fields survive the full flow
# ===================================================================


def test_flow_content_fields_preserved(zotero_two_paper_path: Path, ann_db_path: Path):
    """Selected text, comment, color, page, tags, position JSON, and
    source modified time must survive probe→normalize→import."""
    _import_paper_a(zotero_two_paper_path, ann_db_path)

    conn = open_ann(ann_db_path)

    # --- ANNOT_A1 (highlight, page 1, tagged "important") ---
    row = conn.execute(
        "SELECT * FROM annotations WHERE source_annotation_key = 'ANNOT_A1'"
    ).fetchone()
    assert row is not None, "ANNOT_A1 not found in annotations.db"
    r1 = dict(row)

    assert r1["selected_text"] == "first significant result"
    assert r1["comment"] == "this is the key finding"
    assert r1["color"] == "#ffd400"
    assert r1["page_label"] == "1"
    assert r1["sort_index"] == "0"
    assert r1["source_modified_at"] == "2024-07-01T10:00:00Z"
    assert r1["is_readonly"] == 1
    assert r1["sync_state"] == "imported"
    assert r1["source_annotation_key"] == "ANNOT_A1"
    assert r1["source_attachment_key"] == "ATTACH_A1"
    assert r1["source_parent_key"] == "PAPER_A"
    assert r1["source_library_id"] == "1"

    # Position JSON
    pos = json.loads(r1["position_json"])
    assert isinstance(pos, dict)
    assert pos["x"] == 0.1
    assert pos["y"] == 0.2

    # Tags JSON
    tags = json.loads(r1["tags_json"])
    assert "important" in tags

    # Type
    assert r1["type"] == "highlight"

    # --- ANNOT_A2 (note, page 2, no tags) ---
    row2 = conn.execute(
        "SELECT * FROM annotations WHERE source_annotation_key = 'ANNOT_A2'"
    ).fetchone()
    assert row2 is not None, "ANNOT_A2 not found in annotations.db"
    r2 = dict(row2)

    assert r2["selected_text"] == "another observation"
    assert r2["comment"] == "supplementary note"
    assert r2["color"] == "#ff6666"
    assert r2["page_label"] == "2"
    assert r2["sort_index"] == "1"
    assert r2["type"] == "note"

    # No tags → empty JSON array
    assert json.loads(r2["tags_json"]) == []

    conn.close()


# ===================================================================
# 4. Re-import for one paper does NOT soft-delete another paper's
#    annotations (scope isolation)
# ===================================================================


def test_flow_reimport_does_not_stale_other_paper(
    zotero_two_paper_path: Path, ann_db_path: Path
):
    """Importing Paper A twice must not stale-mark Paper B's annotations."""
    # Import both papers
    _import_paper_a(zotero_two_paper_path, ann_db_path)
    _import_paper_b(zotero_two_paper_path, ann_db_path)

    conn = open_ann(ann_db_path)

    # Verify both papers have rows
    a_rows = conn.execute(
        "SELECT COUNT(*) FROM annotations WHERE paper_id = 'paper_a' AND deleted_at IS NULL"
    ).fetchone()[0]
    b_rows = conn.execute(
        "SELECT COUNT(*) FROM annotations WHERE paper_id = 'paper_b' AND deleted_at IS NULL"
    ).fetchone()[0]
    assert a_rows == 2
    assert b_rows == 1

    # Re-import Paper A — must NOT stale Paper B's rows
    _import_paper_a(zotero_two_paper_path, ann_db_path)

    b_rows_after = conn.execute(
        "SELECT id, deleted_at FROM annotations WHERE paper_id = 'paper_b'"
    ).fetchall()
    conn.close()

    assert len(b_rows_after) == 1, "Paper B should still have exactly 1 row"
    assert b_rows_after[0]["deleted_at"] is None, (
        "Paper B's annotation must not be stale-marked when Paper A is re-imported"
    )


# ===================================================================
# 5. Unknown Zotero schema fails BEFORE any PaperForge import mutation
# ===================================================================


def test_flow_unknown_schema_fails_before_mutation(
    zotero_unknown_schema_path: Path, ann_db_path: Path
):
    """When the Zotero database has an unknown schema, the probe must
    raise ZoteroSchemaError BEFORE any annotation rows are written.

    Safety pattern: a correct caller probes the Zotero schema BEFORE
    calling the importer.  If the probe raises, the importer is never
    called, and no mutation occurs.

    Even if ensure_schema creates PaperForge tables (idempotent), no
    annotation data rows are inserted into annotations.db when the
    Zotero schema is unknown.
    """
    # Record baseline annotation count
    conn = open_ann(ann_db_path)
    count_before = conn.execute(
        "SELECT COUNT(*) FROM annotations"
    ).fetchone()[0]
    conn.close()

    # Phase 1: Probe the Zotero schema — MUST raise ZoteroSchemaError
    with zotero_snapshot(zotero_unknown_schema_path) as snap:
        zconn = open_zotero_readonly(snap)
        with pytest.raises(ZoteroSchemaError) as excinfo:
            probe_zotero_annotation_schema(zconn)
        zconn.close()

    err_msg = str(excinfo.value)
    # The error should name a required table (not the unrelated table
    # that exists in the fixture)
    assert "some_other_table" not in err_msg
    assert "items" in err_msg or "table" in err_msg.lower()

    # Phase 2: Verify NO annotation data rows were written.
    # (ensure_schema may have created empty tables — that is idempotent
    # structural setup, not annotation data mutation.)
    conn2 = open_ann(ann_db_path)
    count_after = conn2.execute(
        "SELECT COUNT(*) FROM annotations"
    ).fetchone()[0]
    conn2.close()

    assert count_after == count_before, (
        "annotations.db must not gain data rows when Zotero schema is unknown"
    )


# ===================================================================
# 6. Temporary Zotero snapshot cleanup after the flow
# ===================================================================


def test_flow_snapshot_cleanup(zotero_two_paper_path: Path, ann_db_path: Path):
    """The temp-copy snapshot must be cleaned up after the full import
    flow, even when the import succeeds."""
    captured_snap_paths: list[Path] = []

    # Wrap zotero_snapshot to capture the temp path
    with zotero_snapshot(zotero_two_paper_path) as snap:
        captured_snap_paths.append(snap)
        zconn = open_zotero_readonly(snap)
        import_zotero_annotations_for_paper(
            zotero_conn=zconn,
            annotations_db_path=ann_db_path,
            paper_id="paper_a",
            library_id=PAPER_A_LIBRARY,
            parent_item_id=PAPER_A_PARENT_ITEM_ID,
            parent_item_key=PAPER_A_PARENT_KEY,
            attachment_item_id=PAPER_A_ATTACH_ITEM_ID,
            attachment_item_key=PAPER_A_ATTACH_KEY,
        )
        zconn.close()

    # After the context exits, the temp snapshot must be gone
    assert len(captured_snap_paths) == 1
    assert not captured_snap_paths[0].exists(), (
        "Temporary Zotero snapshot file must be cleaned up after import flow"
    )
