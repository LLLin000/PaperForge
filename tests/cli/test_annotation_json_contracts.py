"""Consolidated success contract tests for all ``paperforge annotation --json`` commands.

Exercises the full CLI surface: import, list, status, export.
Reads as the final contract matrix for Phase 3.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from paperforge.annotation.schema import ANNOTATION_SCHEMA_VERSION, ensure_schema
from .test_contract_helpers import assert_valid_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PF_RESULT_KEYS = {"ok", "command", "version", "data", "error"}


def _seed_annotations_db(db_path: Path) -> None:
    """Create and populate annotations.db with test data."""
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
        now = "2024-01-15T10:00:00Z"
        rows = [
            (
                "zotero:1:ATTACH_A:ANNOT_1", "PAPER_A", "zotero", "1",
                "ANNOT_1", "ATTACH_A", "PARENT_A",
                "highlight", 0, "1", "selected text A1", "comment A1",
                "#ffd400", 0, '["tag1"]',
                '{"pageIndex":0,"rects":[{"x":0,"y":0,"w":100,"h":20}]}',
                "{}", "imported", 1, now, now, None,
            ),
            (
                "zotero:1:ATTACH_A:ANNOT_2", "PAPER_A", "zotero", "1",
                "ANNOT_2", "ATTACH_A", "PARENT_A",
                "note", 1, "2", "selected text A2", "",
                "#ff6666", 1, '[]',
                "{}", "{}", "imported", 1, now, now, None,
            ),
            (
                "zotero:2:ATTACH_B:ANNOT_3", "PAPER_B", "zotero", "2",
                "ANNOT_3", "ATTACH_B", "PARENT_B",
                "highlight", 0, "1", "selected text B", "comment B",
                "#2ea8ff", 0, '["review"]',
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
    """Run paperforge CLI in the given vault."""
    cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", timeout=60
    )


# ---------------------------------------------------------------------------
# Cross-cutting: PFResult contract for ALL commands
# ---------------------------------------------------------------------------


class TestAnnotationCommandContract:
    """Every ``annotation --json`` command returns a valid PFResult envelope."""

    COMMANDS = [
        ("annotation.status",  ["annotation", "status", "--json"]),
        ("annotation.list",    ["annotation", "list", "--paper", "PAPER_A", "--json"]),
        ("annotation.export",  ["annotation", "export", "--paper", "PAPER_A", "--json"]),
    ]

    @pytest.mark.parametrize("command_name,args", COMMANDS)
    def test_all_commands_return_pfresult(self, vault_builder, command_name, args):
        """Every read-only subcommand returns valid PFResult JSON with ok=true and data as dict."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)
        result = _invoke_cli(vault, args)
        output = result.stdout + result.stderr
        assert "Traceback" not in output
        # Must parse as JSON
        envelope = assert_valid_json(result.stdout)
        # Must have PFResult keys
        missing = _PF_RESULT_KEYS - set(envelope.keys())
        assert not missing, f"{command_name}: missing PFResult keys: {missing}"
        assert envelope["command"] == command_name, (
            f"Expected command {command_name!r}, got {envelope.get('command')!r}"
        )
        assert isinstance(envelope["version"], str) and len(envelope["version"]) > 0
        assert isinstance(envelope["data"], dict)
        assert envelope["error"] is None

    def test_import_returns_pfresult(self, vault_builder):
        """Import returns valid PFResult JSON (may be error without Zotero DB)."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)
        result = _invoke_cli(vault, ["annotation", "import", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output
        envelope = assert_valid_json(result.stdout)
        missing = _PF_RESULT_KEYS - set(envelope.keys())
        assert not missing, f"annotation.import: missing PFResult keys: {missing}"
        assert envelope["command"] == "annotation.import"
        assert isinstance(envelope["version"], str) and len(envelope["version"]) > 0
        # Import without --paper is an error (data=None), that's valid PFResult


# ---------------------------------------------------------------------------
# Import success contracts
# ---------------------------------------------------------------------------


class TestAnnotationImportContract:
    """``annotation import --json`` contract (without real Zotero DB)."""

    def test_import_returns_pfresult_without_paper(self, vault_builder):
        """Import without --paper returns valid PFResult error JSON."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "import", "--json"])
        envelope = json.loads(result.stdout)
        assert "Traceback" not in (result.stdout + result.stderr)
        # PFResult envelope
        assert set(envelope.keys()) == _PF_RESULT_KEYS
        assert envelope["command"] == "annotation.import"
        assert isinstance(envelope["version"], str) and len(envelope["version"]) > 0
        # Without --paper, this is an error — data may be None
        if envelope["ok"] is False:
            assert envelope["error"] is not None
            assert "code" in envelope["error"]
            assert "message" in envelope["error"]

    def test_import_with_paper_returns_pfresult(self, vault_builder):
        """Import with --paper but without Zotero DB returns error JSON."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, [
            "annotation", "import", "--json", "--paper", "PAPER_A"
        ])
        envelope = json.loads(result.stdout)
        assert "Traceback" not in (result.stdout + result.stderr)
        assert set(envelope.keys()) == _PF_RESULT_KEYS
        assert envelope["command"] == "annotation.import"
        # Missing Zotero DB should give actionable error
        if envelope["ok"] is False:
            assert envelope["error"] is not None
            assert "code" in envelope["error"]
            assert isinstance(envelope["error"]["message"], str) and len(envelope["error"]["message"]) > 0


# ---------------------------------------------------------------------------
# Status success contracts
# ---------------------------------------------------------------------------


class TestAnnotationStatusSuccess:
    """``annotation status --json`` success states."""

    def test_status_populated(self, vault_builder):
        """Status returns correct counts from seeded DB."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        envelope = json.loads(result.stdout)
        data = envelope["data"]
        assert data["schema_version"] == ANNOTATION_SCHEMA_VERSION
        assert data["total_annotations"] >= 3
        assert data["db_available"] is True
        assert isinstance(data["source_counts"], dict)
        assert isinstance(data["readonly_count"], int)
        assert isinstance(data["deleted_count"], int)

    def test_status_empty_db(self, vault_builder):
        """Status on vault with no annotations.db returns graceful empty."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        envelope = json.loads(result.stdout)
        data = envelope["data"]
        assert data["db_available"] is False
        assert data["total_annotations"] == 0
        assert data["schema_version"] == 0

    def test_status_keys_contract(self, vault_builder):
        """Status data keys are stable and machine-friendly."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        data = json.loads(result.stdout)["data"]
        required = {"db_path", "schema_version", "total_annotations",
                     "source_counts", "readonly_count", "deleted_count",
                     "db_available", "total_papers_with_annotations"}
        missing = required - set(data.keys())
        assert not missing, f"Missing status keys: {missing}"


# ---------------------------------------------------------------------------
# List success contracts
# ---------------------------------------------------------------------------


class TestAnnotationListSuccess:
    """``annotation list --json`` success states."""

    def test_list_ordered_by_page(self, vault_builder):
        """List returns annotations ordered by page_index, sort_index, id."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "list", "--paper", "PAPER_A", "--json"])
        envelope = json.loads(result.stdout)
        data = envelope["data"]
        anns = data["annotations"]
        assert len(anns) >= 2
        # Verify ascending page order
        pages = [a["page"] for a in anns]
        assert pages == sorted(pages), f"Annotations not ordered by page: {pages}"

    def test_list_scan_fields(self, vault_builder):
        """List returns lightweight scan fields only."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "list", "--paper", "PAPER_B", "--json"])
        ann = json.loads(result.stdout)["data"]["annotations"][0]
        expected_fields = {"id", "type", "page", "selected_text", "comment",
                           "color", "source", "is_readonly"}
        missing = expected_fields - set(ann.keys())
        assert not missing, f"Missing list scan fields: {missing}"
        # Should NOT contain heavy fields
        heavy = {"position_json", "selector_json", "tags_json"}
        assert heavy.isdisjoint(ann.keys()), (
            f"List should not contain heavy fields, got: {heavy & set(ann.keys())}"
        )

    def test_list_no_annotations_returns_empty(self, vault_builder):
        """List for paper with no annotations returns empty."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "list", "--paper", "MISSING", "--json"])
        envelope = json.loads(result.stdout)
        assert envelope["data"]["total"] == 0
        assert envelope["data"]["annotations"] == []


# ---------------------------------------------------------------------------
# Export success contracts
# ---------------------------------------------------------------------------


class TestAnnotationExportSuccess:
    """``annotation export --json`` success states."""

    def test_export_full_payload(self, vault_builder):
        """Export returns full annotation fields for a paper."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "export", "--paper", "PAPER_B", "--json"])
        envelope = json.loads(result.stdout)
        data = envelope["data"]
        assert data["paper"] == "PAPER_B"
        assert data["total"] == 1
        assert data["format_version"] == "1.0"

        ann = data["annotations"][0]
        required_fields = {
            "id", "paper_id", "source", "type", "page_index",
            "page_label", "selected_text", "comment", "color",
            "sort_index", "tags_json", "position_json",
            "selector_json", "sync_state", "is_readonly",
            "created_at", "updated_at",
            "source_library_id", "source_annotation_key",
            "source_attachment_key", "source_parent_key",
        }
        missing = required_fields - set(ann.keys())
        assert not missing, f"Missing export fields: {missing}"

    def test_export_has_format_version(self, vault_builder):
        """Export response includes format_version."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "export", "--paper", "PAPER_B", "--json"])
        data = json.loads(result.stdout)["data"]
        assert "format_version" in data, "Missing format_version in export data"
        assert isinstance(data["format_version"], str)

    def test_export_empty_paper(self, vault_builder):
        """Export for paper with no annotations returns empty."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        _seed_annotations_db(db_path)

        result = _invoke_cli(vault, ["annotation", "export", "--paper", "NO_ANN", "--json"])
        envelope = json.loads(result.stdout)
        assert envelope["data"]["total"] == 0
        assert envelope["data"]["annotations"] == []
