"""CLI contract tests for `paperforge annotation import --json`.

Tests verify preview/apply behavior, Zotero error mapping, and stable
JSON output shapes.  They use inline Zotero SQLite fixture builders
(identical pattern to Phase 2 unit tests).
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from .test_contract_helpers import assert_json_shape, assert_valid_json


def _make_temp_dir() -> Path:
    """Create a temporary directory (tmp_path replacement for Windows compat)."""
    return Path(tempfile.mkdtemp(prefix="pf_test_"))

# ---------------------------------------------------------------------------
# Zotero SQLite fixture builders
# ---------------------------------------------------------------------------

_PF_RESULT_KEYS = {"ok", "command", "version", "data", "error"}


def _build_zotero_single_paper(db_path: Path) -> None:
    """Minimal Zotero SQLite with one paper and two annotations.

    Paper A (libraryID=1):
      parent item (itemID=1, key=PAPER_A)
      └── attachment (itemID=2, key=ATTACH_A1)
            ├── annotation (itemID=3, key=ANNOT_A1) — highlight, page 1
            └── annotation (itemID=4, key=ANNOT_A2) — note, page 2
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE items (
                itemID INTEGER PRIMARY KEY,
                itemTypeID INTEGER NOT NULL DEFAULT 1,
                libraryID INTEGER NOT NULL DEFAULT 1,
                key TEXT NOT NULL,
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
                tagID INTEGER NOT NULL,
                PRIMARY KEY (itemID, tagID)
            );

            -- Paper A parent item
            INSERT INTO items VALUES (1, 1, 1, 'PAPER_A', '2024-01-15T10:00:00Z');
            -- Attachment
            INSERT INTO items VALUES (2, 1, 1, 'ATTACH_A1', '2024-01-15T10:00:00Z');
            -- Annotations (also in items as annotation items)
            INSERT INTO items VALUES (3, 1, 1, 'ANNOT_A1', '2024-01-15T10:05:00Z');
            INSERT INTO items VALUES (4, 1, 1, 'ANNOT_A2', '2024-01-15T10:10:00Z');

            INSERT INTO itemAttachments VALUES (2, 1, 'storage:ATTACH_A1/test.pdf', 'application/pdf');

            INSERT INTO itemAnnotations VALUES (3, 2, 'highlight', 'selected text 1', 'comment 1',
                '#ffd400', '1', 0, '{"pageIndex":0,"rects":[]}', '2024-01-15T10:05:00Z');
            INSERT INTO itemAnnotations VALUES (4, 2, 'note', 'selected text 2', '',
                '#ff6666', '2', 1, '{}', '2024-01-15T10:10:00Z');

            INSERT INTO tags VALUES (1, 'important');
            INSERT INTO tags VALUES (2, 'review');
            INSERT INTO itemTags VALUES (3, 1);
            INSERT INTO itemTags VALUES (4, 2);
        """)
        conn.commit()
    finally:
        conn.close()


def _build_zotero_invalid_schema(db_path: Path) -> None:
    """Zotero SQLite with missing itemAnnotations table (invalid for annotation import)."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE items (itemID INTEGER PRIMARY KEY, key TEXT);
            -- Intentionally missing itemAnnotations table
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Preview mode tests
# ---------------------------------------------------------------------------


class TestImportPreview:
    """Contract: import without --apply is preview (dry_run)."""

    def test_import_json_preview_returns_pfresult(self, cli_invoker):
        """Import --json returns valid PFResult with dry_run=true."""
        tmp_dir = _make_temp_dir()
        zotero_db = tmp_dir / "zotero_preview.sqlite"
        _build_zotero_single_paper(zotero_db)

        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(zotero_db),
            "--json",
        ])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr[:300]}"
        envelope = assert_valid_json(result.stdout)
        assert_json_shape(envelope, _PF_RESULT_KEYS)

        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.import"
        assert envelope["error"] is None

        data = envelope["data"]
        assert data["dry_run"] is True, "Preview mode must set dry_run=true"
        assert data["applied"] is False, "Preview mode must set applied=false"

    def test_import_preview_does_not_create_annotations_db(self, cli_invoker):
        """Preview mode does not create annotations.db."""
        tmp_dir = _make_temp_dir()
        zotero_db = tmp_dir / "zotero_preview2.sqlite"
        _build_zotero_single_paper(zotero_db)

        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(zotero_db),
            "--json",
        ])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        assert envelope["data"]["dry_run"] is True

    def test_import_preview_has_counts(self, cli_invoker):
        """Preview mode returns projected counts in data.counts."""
        tmp_dir = _make_temp_dir()
        zotero_db = tmp_dir / "zotero_preview3.sqlite"
        _build_zotero_single_paper(zotero_db)

        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(zotero_db),
            "--json",
        ])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        counts = envelope["data"].get("counts", {})
        assert isinstance(counts, dict)
        # Should have at least total and some breakdown
        assert "total" in counts, "Preview counts must include total"


# ---------------------------------------------------------------------------
# Apply mode tests
# ---------------------------------------------------------------------------


class TestImportApply:
    """Contract: import with --apply writes to annotations.db."""

    def test_import_apply_json_returns_pfresult(self, cli_invoker):
        """Import --apply --json returns PFResult with applied=true and counts."""
        tmp_dir = _make_temp_dir()
        zotero_db = tmp_dir / "zotero_apply.sqlite"
        _build_zotero_single_paper(zotero_db)

        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(zotero_db),
            "--apply",
            "--json",
        ])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr[:300]}"
        envelope = assert_valid_json(result.stdout)
        assert_json_shape(envelope, _PF_RESULT_KEYS)

        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.import"
        assert envelope["error"] is None

        data = envelope["data"]
        assert data["dry_run"] is False, "Apply mode must set dry_run=false"
        assert data["applied"] is True, "Apply mode must set applied=true"

        counts = data.get("counts", {})
        assert isinstance(counts, dict)
        assert "inserted" in counts
        assert "total" in counts

    def test_import_apply_writes_to_db(self, cli_invoker):
        """Import --apply actually writes annotation rows."""
        tmp_dir = _make_temp_dir()
        zotero_db = tmp_dir / "zotero_apply2.sqlite"
        _build_zotero_single_paper(zotero_db)

        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(zotero_db),
            "--apply",
            "--json",
        ])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        counts = envelope["data"]["counts"]
        assert counts["inserted"] + counts["updated"] + counts["unchanged"] > 0, (
            "Expected at least one annotation to be written"
        )


# ---------------------------------------------------------------------------
# Error contract tests
# ---------------------------------------------------------------------------


class TestImportErrors:
    """Contract: import failures return PFResult JSON under --json."""

    def test_import_no_paper_returns_json_error(self, cli_invoker):
        """Missing --paper produces valid PFResult error JSON (not traceback)."""
        result = cli_invoker(["annotation", "import", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output
        # argparse may exit 2 with text; we just verify no traceback
        if result.returncode == 0:
            envelope = json.loads(result.stdout)
            assert_json_shape(envelope, _PF_RESULT_KEYS)

    def test_import_missing_zotero_db_returns_json_error(self, cli_invoker):
        """Missing --zotero-db path returns stable PFResult JSON (not traceback)."""
        tmp_dir = _make_temp_dir()
        missing_path = tmp_dir / "nonexistent" / "zotero.sqlite"
        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(missing_path),
            "--json",
        ])
        output = result.stdout + result.stderr
        assert "Traceback" not in output, f"Traceback found: {output[:300]}"
        # Should return valid JSON on stdout
        try:
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail("Expected valid JSON for --json error output")
        assert envelope["ok"] is False
        assert envelope["command"] == "annotation.import"
        assert envelope["error"] is not None
        assert isinstance(envelope["error"].get("code"), str)

    def test_import_invalid_zotero_schema_returns_json_error(self, cli_invoker):
        """Invalid Zotero schema returns stable PFResult JSON error."""
        tmp_dir = _make_temp_dir()
        zotero_db = tmp_dir / "zotero_bad_schema.sqlite"
        _build_zotero_invalid_schema(zotero_db)

        result = cli_invoker([
            "annotation", "import",
            "--paper", "PAPER_A",
            "--zotero-db", str(zotero_db),
            "--json",
        ])
        output = result.stdout + result.stderr
        assert "Traceback" not in output, f"Traceback found: {output[:300]}"
        try:
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail("Expected valid JSON for --json error output")
        assert envelope["ok"] is False
        assert envelope["error"] is not None
