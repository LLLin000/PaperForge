"""CLI contract tests for `paperforge annotation list/status/export --json`.

Tests verify read-only command behavior against a pre-populated
annotations.db.  Uses ``vault_builder`` to create a disposable vault
and seeds annotations.db manually before CLI invocation.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from paperforge.annotation.schema import ANNOTATION_SCHEMA_VERSION, ensure_schema
from .test_contract_helpers import assert_json_shape, assert_valid_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PF_RESULT_KEYS = {"ok", "command", "version", "data", "error"}


def _seed_annotations_db(db_path: Path) -> None:
    """Create and populate annotations.db with test data for two papers."""
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)

        now = "2024-01-15T10:00:00Z"
        rows = [
            # Paper A: two annotations
            (
                "zotero:1:ATTACH_A:ANNOT_1", "PAPER_A", "zotero", "1",
                "ANNOT_1", "ATTACH_A", "PARENT_A",
                "highlight", 0, "1", "selected text A1", "comment A1",
                "#ffd400", "0", '["tag1"]',
                '{"pageIndex":0,"rects":[{"x":0,"y":0,"w":100,"h":20}]}',
                "{}", "imported", 1, now, now, None,
            ),
            (
                "zotero:1:ATTACH_A:ANNOT_2", "PAPER_A", "zotero", "1",
                "ANNOT_2", "ATTACH_A", "PARENT_A",
                "note", 1, "2", "selected text A2", "",
                "#ff6666", "1", '[]',
                "{}", "{}", "imported", 1, now, now, None,
            ),
            # Paper B: one annotation
            (
                "zotero:2:ATTACH_B:ANNOT_3", "PAPER_B", "zotero", "2",
                "ANNOT_3", "ATTACH_B", "PARENT_B",
                "highlight", 0, "1", "selected text B", "comment B",
                "#2ea8ff", "0", '["review"]',
                '{"pageIndex":0,"rects":[{"x":10,"y":10,"w":50,"h":15}]}',
                "{}", "imported", 1, now, now, None,
            ),
        ]
        conn.executemany(
            """INSERT INTO annotations (
                id, paper_id, source, source_library_id,
                source_annotation_key, source_attachment_key, source_parent_key,
                type, page_index, page_label, selected_text, comment, color,
                sort_index, tags_json, position_json, selector_json,
                sync_state, is_readonly, created_at, updated_at, deleted_at
            ) VALUES (?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?)""",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _invoke_cli(vault: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run paperforge CLI in the given vault and return the result."""
    cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", timeout=60
    )


# ---------------------------------------------------------------------------
# Status tests
# ---------------------------------------------------------------------------


class TestStatusJson:
    """Contract: ``annotation status --json`` returns DB/schema/count health."""

    def test_status_empty_vault(self, vault_builder):
        """Status on empty vault returns valid PFResult with empty-state counts."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr[:200]}"
        envelope = assert_valid_json(result.stdout)
        assert_json_shape(envelope, _PF_RESULT_KEYS)
        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.status"
        assert envelope["error"] is None
        data = envelope["data"]
        assert isinstance(data, dict)
        # Should report healthy empty state
        assert data.get("schema_version") is not None
        assert data.get("total_annotations") == 0

    def test_status_with_data(self, vault_builder):
        """Status on populated vault returns correct counts."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        data = envelope["data"]
        assert data["schema_version"] == ANNOTATION_SCHEMA_VERSION
        assert data["total_annotations"] == 3
        assert isinstance(data.get("source_counts"), dict)
        assert data["source_counts"].get("zotero") == 3

    def test_status_keys_stable(self, vault_builder):
        """Status JSON keys are stable machine-friendly identifiers."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        assert isinstance(envelope["data"], dict)
        # Core keys must be present (use set check)
        core_keys = {"db_path", "schema_version", "total_annotations",
                     "source_counts", "readonly_count", "deleted_count"}
        assert core_keys.issubset(envelope["data"].keys()), (
            f"Missing keys: {core_keys - set(envelope['data'].keys())}"
        )


# ---------------------------------------------------------------------------
# List tests
# ---------------------------------------------------------------------------


class TestListJson:
    """Contract: ``annotation list --json`` returns ordered lightweight rows."""

    def test_list_requires_paper(self, vault_builder):
        """List without --paper returns error JSON (not traceback)."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "list", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output

    def test_list_returns_annotations(self, vault_builder):
        """List returns ordered annotations for a paper."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "list", "--paper", "PAPER_A", "--json"])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.list"

        data = envelope["data"]
        assert data["paper"] == "PAPER_A"
        assert data["total"] == 2
        assert len(data["annotations"]) == 2

        # Lightweight scan fields
        ann = data["annotations"][0]
        scan_fields = {"id", "type", "page", "selected_text", "comment",
                       "color", "source", "is_readonly"}
        assert scan_fields.issubset(ann.keys()), (
            f"Missing scan fields: {scan_fields - set(ann.keys())}"
        )

    def test_list_no_annotations(self, vault_builder):
        """List for paper with no annotations returns empty list."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "list", "--paper", "NONEXISTENT", "--json"])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        data = envelope["data"]
        assert data["total"] == 0
        assert data["annotations"] == []


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExportJson:
    """Contract: ``annotation export --json`` returns full paper-scoped payload."""

    def test_export_requires_paper(self, vault_builder):
        """Export without --paper returns error JSON (not traceback)."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "export", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output

    def test_export_returns_full_payload(self, vault_builder):
        """Export returns complete annotation content for a paper."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "export", "--paper", "PAPER_B", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr[:200]}"
        envelope = json.loads(result.stdout)
        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.export"

        data = envelope["data"]
        assert data["paper"] == "PAPER_B"
        assert data["total"] == 1
        assert len(data["annotations"]) == 1

        # Full payload fields
        ann = data["annotations"][0]
        full_fields = {"id", "paper_id", "source", "type", "page_index",
                       "page_label", "selected_text", "comment", "color",
                       "sort_index", "tags_json", "position_json",
                       "selector_json", "sync_state", "is_readonly",
                       "created_at", "updated_at", "deleted_at",
                       "source_library_id", "source_annotation_key",
                       "source_attachment_key", "source_parent_key"}
        missing = full_fields - set(ann.keys())
        assert not missing, f"Missing export fields: {missing}"
