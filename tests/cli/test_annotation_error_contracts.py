"""Consolidated error contract tests for all ``paperforge annotation --json`` commands.

Exercises representative error cases: missing --paper, missing Zotero DB,
unreadable DB, and invalid subcommands.
"""

from __future__ import annotations

import json
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest

from .test_contract_helpers import assert_json_shape, assert_valid_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PF_RESULT_KEYS = {"ok", "command", "version", "data", "error"}

_REQUIRES_PAPER_COMMANDS = [
    ("annotation.list",   ["annotation", "list", "--json"]),
    ("annotation.export", ["annotation", "export", "--json"]),
]


def _invoke_cli(vault: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run paperforge CLI in the given vault."""
    cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", timeout=60
    )


# ---------------------------------------------------------------------------
# Missing --paper parameter
# ---------------------------------------------------------------------------


class TestMissingPaperParam:
    """``list/export --json`` report actionable error when --paper is missing."""

    @pytest.mark.parametrize("command_name,args", _REQUIRES_PAPER_COMMANDS)
    def test_missing_paper_returns_error_json(self, vault_builder, command_name, args):
        """Missing --paper returns valid PFResult error JSON."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, args)
        envelope = assert_valid_json(result.stdout)
        assert_json_shape(envelope, _PF_RESULT_KEYS)
        # Should be an error
        assert envelope["ok"] is False
        assert envelope["command"] == command_name
        assert envelope["error"] is not None, "Expected error detail when --paper missing"
        error = envelope["error"]
        assert "code" in error
        assert "message" in error
        # Must not traceback
        output = result.stdout + result.stderr
        assert "Traceback" not in output

    def test_missing_paper_has_suggestions(self, vault_builder):
        """Error for missing --paper includes suggestions."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "list", "--json"])
        envelope = json.loads(result.stdout)
        error = envelope.get("error", {})
        suggestions = error.get("suggestions", [])
        assert len(suggestions) > 0, "Expected suggestions in missing --paper error"
        assert any("--paper" in s for s in suggestions)


# ---------------------------------------------------------------------------
# Missing annotations.db (not configured)
# ---------------------------------------------------------------------------


class TestMissingAnnotationsDb:
    """Commands handle absent annotations.db gracefully."""

    def test_status_on_empty_vault_returns_empty_state(self, vault_builder):
        """Status on vault without annotations.db returns ok=true with db_available=false."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        envelope = json.loads(result.stdout)
        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.status"
        data = envelope["data"]
        assert data["db_available"] is False
        assert data["total_annotations"] == 0

    def test_list_on_empty_vault_returns_empty(self, vault_builder):
        """List on vault without annotations.db returns ok=true with empty list."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "list", "--paper", "ANY", "--json"])
        envelope = json.loads(result.stdout)
        assert envelope["ok"] is True
        assert envelope["data"]["annotations"] == []
        assert envelope["data"]["total"] == 0

    def test_export_on_empty_vault_returns_empty(self, vault_builder):
        """Export on vault without annotations.db returns ok=true with empty list."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "export", "--paper", "ANY", "--json"])
        envelope = json.loads(result.stdout)
        assert envelope["ok"] is True
        assert envelope["data"]["annotations"] == []
        assert envelope["data"]["total"] == 0


# ---------------------------------------------------------------------------
# Corrupt/invalid annotations.db
# ---------------------------------------------------------------------------


class TestCorruptAnnotationsDb:
    """Commands handle unreadable annotations.db gracefully."""

    def test_status_corrupt_db_returns_error(self, vault_builder):
        """Status on corrupt annotations.db returns ok=false with error."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Write invalid SQLite data
        db_path.write_bytes(b"not a valid sqlite database")

        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output, f"Traceback on corrupt DB: {output[:500]}"

    def test_list_corrupt_db_returns_empty(self, vault_builder):
        """List on corrupt annotations.db returns ok=true fallback."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"garbage data")

        result = _invoke_cli(vault, ["annotation", "list", "--paper", "ANY", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output

    def test_export_corrupt_db_returns_empty(self, vault_builder):
        """Export on corrupt annotations.db returns ok=true fallback."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"garbage")

        result = _invoke_cli(vault, ["annotation", "export", "--paper", "ANY", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output


# ---------------------------------------------------------------------------
# Unknown/missing schema
# ---------------------------------------------------------------------------


class TestMissingSchema:
    """Annotations.db without schema returns graceful results."""

    def test_status_empty_db_no_schema(self, vault_builder):
        """Status on annotations.db with empty schema returns graceful."""
        vault = vault_builder.build("minimal")
        db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Create valid SQLite but no schema tables
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE dummy (x TEXT)")
        conn.close()

        result = _invoke_cli(vault, ["annotation", "status", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output


# ---------------------------------------------------------------------------
# Invalid import usage
# ---------------------------------------------------------------------------


class TestImportErrors:
    """``annotation import --json`` error contracts."""

    def test_import_no_traceback_on_empty_vault(self, vault_builder):
        """Import on empty vault does not traceback."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, ["annotation", "import", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output

    def test_import_unknown_paper_returns_error(self, vault_builder):
        """Import with unknown --paper returns actionable error."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, [
            "annotation", "import", "--json", "--paper", "NONEXISTENT_KEY"
        ])
        output = result.stdout + result.stderr
        assert "Traceback" not in output


# ---------------------------------------------------------------------------
# Error envelope shape
# ---------------------------------------------------------------------------


class TestErrorEnvelope:
    """All error JSON returns stable error envelope with PFResult shape."""

    ERROR_CASES = [
        ("annotation.list",   ["annotation", "list", "--json"]),
        ("annotation.export", ["annotation", "export", "--json"]),
    ]

    @pytest.mark.parametrize("command_name,args", ERROR_CASES)
    def test_error_envelope_shape(self, vault_builder, command_name, args):
        """Error JSON has stable error fields: code, message, details, suggestions."""
        vault = vault_builder.build("minimal")
        result = _invoke_cli(vault, args)
        envelope = json.loads(result.stdout)
        assert envelope["ok"] is False
        assert envelope["command"] == command_name
        error = envelope["error"]
        assert isinstance(error, dict)
        # Must have code and message
        assert "code" in error
        assert "message" in error
        # code should be a stable string identifier
        assert isinstance(error["code"], str)
        assert "@@" not in error["code"], f"Unformatted error code: {error['code']}"
        # message should be a non-empty string
        assert isinstance(error["message"], str) and len(error["message"]) > 0
        # versions are still present in envelope
        assert isinstance(envelope["version"], str) and len(envelope["version"]) > 0
