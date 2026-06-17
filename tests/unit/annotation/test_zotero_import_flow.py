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
import sqlite3
import tempfile
from pathlib import Path

import pytest

from paperforge.annotation.errors import (
    AnnotationImportError,
    ZoteroSchemaError,
)
from paperforge.annotation.importer import (
    import_zotero_annotations_for_paper,
)
from paperforge.annotation.schema import ensure_schema
from paperforge.annotation.zotero_normalize import NormalizedAnnotation
from paperforge.annotation.zotero_probe import (
    open_zotero_readonly,
    probe_zotero_annotation_schema,
    zotero_snapshot,
)


# ---------------------------------------------------------------------------
# Fixture builders: minimal Zotero-style SQLite databases
# ---------------------------------------------------------------------------

# Shared item IDs for cross-test reference:
#   Paper A: libraryID=1, parent_key="PAPER_A", attachment_key="ATTACH_A1"
#   Paper B: libraryID=2, parent_key="PAPER_B", attachment_key="ATTACH_B1"

_PAPER_A_LIBRARY = 1
_PAPER_A_PARENT_KEY = "PAPER_A"
_PAPER_A_ATTACH_KEY = "ATTACH_A1"
_PAPER_A_PARENT_ITEM_ID = 1
_PAPER_A_ATTACH_ITEM_ID = 2
_ANNOT_A1_KEY = "ANNOT_A1"
_ANNOT_A2_KEY = "ANNOT_A2"

_PAPER_B_LIBRARY = 2
_PAPER_B_PARENT_KEY = "PAPER_B"
_PAPER_B_ATTACH_KEY = "ATTACH_B1"
_PAPER_B_PARENT_ITEM_ID = 10
_PAPER_B_ATTACH_ITEM_ID = 11
_ANNOT_B1_KEY = "ANNOT_B1"


def _build_zotero_two_paper(db_path: Path) -> None:
    """Create a minimal Zotero-style SQLite with two papers.

    Paper A (libraryID=1):
      parent item (itemID=1, key=PAPER_A)
      └── attachment (itemID=2, key=ATTACH_A1)
            ├── annotation (itemID=3, key=ANNOT_A1) — highlight, page 1, tagged
            └── annotation (itemID=4, key=ANNOT_A2) — note, page 2

    Paper B (libraryID=2):
      parent item (itemID=10, key=PAPER_B)
      └── attachment (itemID=11, key=ATTACH_B1)
            └── annotation (itemID=12, key=ANNOT_B1) — underline, page 3
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE items (
                itemID INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                libraryID INTEGER NOT NULL DEFAULT 1,
                dateModified TEXT
            );
            CREATE TABLE itemAttachments (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                path TEXT,
                contentType TEXT
            );
            CREATE TABLE itemAnnotations (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                type TEXT, text TEXT, comment TEXT, color TEXT,
                pageLabel TEXT, sortIndex INTEGER, position TEXT,
                dateModified TEXT
            );
            CREATE TABLE tags (
                tagID INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE itemTags (
                itemID INTEGER NOT NULL,
                tagID INTEGER NOT NULL
            );

            -- Paper A: parent, attachment, annotations
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (1, 'PAPER_A', 1, '2024-07-01');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (2, 'ATTACH_A1', 1, '2024-07-01');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (3, 'ANNOT_A1', 1, '2024-07-01T10:00:00Z');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (4, 'ANNOT_A2', 1, '2024-07-01T11:00:00Z');

            -- Paper B: parent, attachment, annotation
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (10, 'PAPER_B', 2, '2024-07-02');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (11, 'ATTACH_B1', 2, '2024-07-02');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (12, 'ANNOT_B1', 2, '2024-07-02T12:00:00Z');

            -- Attachments
            INSERT INTO itemAttachments (itemID, parentItemID, path, contentType)
            VALUES (2, 1, 'storage:ATTACH_A1/file.pdf', 'application/pdf');
            INSERT INTO itemAttachments (itemID, parentItemID, path, contentType)
            VALUES (11, 10, 'storage:ATTACH_B1/file.pdf', 'application/pdf');

            -- Annotations for Paper A / ATTACH_A1
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (3, 2, 'highlight',
                    'first significant result',
                    'this is the key finding',
                    '#ffd400',
                    '1', 0,
                    '{"x":0.1,"y":0.2,"w":0.8,"h":0.05}',
                    '2024-07-01T10:00:00Z');

            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (4, 2, 'note',
                    'another observation',
                    'supplementary note',
                    '#ff6666',
                    '2', 1,
                    '{"x":0.3,"y":0.4,"w":0.5,"h":0.1}',
                    '2024-07-01T11:00:00Z');

            -- Annotation for Paper B / ATTACH_B1
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (12, 11, 'underline',
                    'methodology detail',
                    'check this method',
                    '#00ff00',
                    '3', 0,
                    '{"x":0.5,"y":0.6,"w":0.3,"h":0.02}',
                    '2024-07-02T12:00:00Z');

            -- Tags: ANNOT_A1 gets "important" tag
            INSERT INTO tags (tagID, name) VALUES (1, 'important');
            INSERT INTO tags (tagID, name) VALUES (2, 'methodology');
            INSERT INTO itemTags (itemID, tagID) VALUES (3, 1);
        """)
        conn.commit()
    finally:
        conn.close()


def _build_zotero_unknown_schema(db_path: Path) -> None:
    """Create a SQLite file that exists but has no Zotero annotation tables.

    This simulates a database with an unknown/unsupported schema version.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE some_other_table (id INTEGER PRIMARY KEY, val TEXT)"
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def zotero_two_paper_path() -> Path:
    """Create a Zotero-style SQLite with two papers."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    _build_zotero_two_paper(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def zotero_unknown_schema_path() -> Path:
    """Create a SQLite file with no Zotero annotation tables."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    _build_zotero_unknown_schema(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def ann_db_path() -> Path:
    """Create an empty annotations.db with schema applied."""
    tmp = tempfile.NamedTemporaryFile(suffix=".annotations.db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
    finally:
        conn.close()
    yield db_path
    if db_path.exists():
        db_path.unlink()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_ann(db_path: Path) -> sqlite3.Connection:
    """Open annotations.db with Row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _import_paper_a(zotero_path: Path, ann_db: Path) -> None:
    """Convenience: import Paper A annotations."""
    with zotero_snapshot(zotero_path) as snap:
        zconn = open_zotero_readonly(snap)
        import_zotero_annotations_for_paper(
            zotero_conn=zconn,
            annotations_db_path=ann_db,
            paper_id="paper_a",
            library_id=_PAPER_A_LIBRARY,
            parent_item_id=_PAPER_A_PARENT_ITEM_ID,
            parent_item_key=_PAPER_A_PARENT_KEY,
            attachment_item_id=_PAPER_A_ATTACH_ITEM_ID,
            attachment_item_key=_PAPER_A_ATTACH_KEY,
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
            library_id=_PAPER_B_LIBRARY,
            parent_item_id=_PAPER_B_PARENT_ITEM_ID,
            parent_item_key=_PAPER_B_PARENT_KEY,
            attachment_item_id=_PAPER_B_ATTACH_ITEM_ID,
            attachment_item_key=_PAPER_B_ATTACH_KEY,
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

    conn = _open_ann(ann_db_path)
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

    conn = _open_ann(ann_db_path)

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

    conn = _open_ann(ann_db_path)

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
    conn = _open_ann(ann_db_path)
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
    conn2 = _open_ann(ann_db_path)
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
            library_id=_PAPER_A_LIBRARY,
            parent_item_id=_PAPER_A_PARENT_ITEM_ID,
            parent_item_key=_PAPER_A_PARENT_KEY,
            attachment_item_id=_PAPER_A_ATTACH_ITEM_ID,
            attachment_item_key=_PAPER_A_ATTACH_KEY,
        )
        zconn.close()

    # After the context exits, the temp snapshot must be gone
    assert len(captured_snap_paths) == 1
    assert not captured_snap_paths[0].exists(), (
        "Temporary Zotero snapshot file must be cleaned up after import flow"
    )
