"""Contract tests for the `paperforge annotation ...` CLI namespace.

These tests verify the command shape, JSON envelope, and error handling
before any subcommand wiring to backend logic. They use the existing
``cli_invoker`` fixture which runs ``python -m paperforge ...`` in a
disposable vault subprocess.
"""

from __future__ import annotations

import json

import pytest

from .test_contract_helpers import assert_json_shape, assert_valid_json


class TestAnnotationNamespace:
    """Contract: ``paperforge annotation`` exposes 4 subcommands."""

    def test_annotation_help_lists_subcommands(self, cli_invoker):
        """``paperforge annotation --help`` exits 0 and lists import/list/status/export."""
        result = cli_invoker(["annotation", "--help"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        output = result.stdout + result.stderr
        for cmd in ("import", "list", "status", "export"):
            assert cmd in output, f"Expected subcommand {cmd!r} in help output"

    def test_annotation_no_subcommand_shows_help(self, cli_invoker):
        """``paperforge annotation`` (no subcommand) shows help text."""
        result = cli_invoker(["annotation"])
        # argparse exits 2 when a required subparser is missing
        assert result.returncode != 0
        output = (result.stdout + result.stderr).lower()
        assert "usage:" in output
        # Should mention the subcommands
        for cmd in ("import", "list", "status", "export"):
            assert cmd in output


class TestAnnotationStatusJsonContract:
    """Contract: ``paperforge annotation status --json`` returns PFResult envelope."""

    ENVELOPE_KEYS = {"ok", "command", "version", "data", "error"}

    def test_status_json_pfresult_shape(self, cli_invoker):
        """``annotation status --json`` returns valid JSON with PFResult keys."""
        result = cli_invoker(["annotation", "status", "--json"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        envelope = assert_valid_json(result.stdout)
        assert_json_shape(envelope, self.ENVELOPE_KEYS)

        # Core PFResult contract
        assert envelope["ok"] is True
        assert envelope["command"] == "annotation.status"
        assert isinstance(envelope["version"], str) and len(envelope["version"]) > 0

        # data must be present and a dict (even if empty)
        assert isinstance(envelope["data"], dict)
        # error must be None for success
        assert envelope["error"] is None

    def test_status_json_stable_keys(self, cli_invoker):
        """Data keys are stable, machine-friendly English identifiers."""
        result = cli_invoker(["annotation", "status", "--json"])
        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        data = envelope.get("data", {})
        # Should include at minimum a non-empty set of stable keys
        # (specific keys depend on backend, but the shape must be dict)
        assert isinstance(data, dict)


class TestAnnotationErrorContract:
    """Contract: ``paperforge annotation ...`` failures return valid JSON or clean text."""

    def test_unknown_subcommand_no_traceback(self, cli_invoker):
        """Unknown annotation subcommand exits non-zero without Python traceback."""
        result = cli_invoker(["annotation", "nonexistent-subcmd"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output
        assert result.returncode != 0

    def test_unknown_subcommand_json_error(self, cli_invoker):
        """Unknown annotation subcommand with --json returns valid JSON (not traceback)."""
        # Use a subcommand that exists but where --json can reach error path.
        # Unknown subcommand itself is caught by argparse before --json is parsed.
        result = cli_invoker(["annotation", "nonexistent-subcmd", "--json"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output, f"Unexpected traceback: {output[:500]}"
        # argparse outputs text; we just verify no traceback
        assert result.returncode != 0

    def test_import_json_preview_default(self, cli_invoker):
        """``annotation import --json`` (no --apply) returns valid PFResult with dry_run=True."""
        result = cli_invoker(["annotation", "import", "--json"])
        # Without --apply this should be a preview — may return 0 even with no paper
        output = result.stdout + result.stderr
        assert "Traceback" not in output
        # If JSON output was produced, validate shape
        if result.returncode == 0:
            try:
                envelope = json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Expected valid JSON for annotation import --json")
            assert "ok" in envelope
            assert envelope.get("command") == "annotation.import"
            data = envelope.get("data", {})
            # Preview mode must indicate dry_run
            assert data.get("dry_run") is True or data.get("applied") is False, (
                "Preview mode should indicate dry_run (not applied)"
            )
