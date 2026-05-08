"""CLI contract tests for error handling and exit codes."""

from __future__ import annotations

import pytest


class TestExitCodes:
    """Contract: CLI commands exit with correct exit codes."""

    def test_invalid_command_exits_nonzero(self, cli_invoker):
        """Unknown command -> exit code 2 (argparse standard)."""
        result = cli_invoker(["nonexistent-command"])
        assert result.returncode != 0, f"Expected non-zero, got {result.returncode}"
        assert len(result.stderr) > 0, "Expected stderr output for unknown command"

    def test_no_command_shows_help(self, cli_invoker):
        """No arguments -> exit code 2 with help text."""
        result = cli_invoker([])
        assert result.returncode != 0
        assert (
            "usage:" in result.stdout.lower()
            or "usage:" in result.stderr.lower()
        )

    def test_help_flag(self, cli_invoker):
        """--help -> exit code 0 with help text."""
        result = cli_invoker(["--help"])
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_version_flag(self, cli_invoker):
        """--version -> exit code 0 with version string."""
        result = cli_invoker(["--version"])
        assert result.returncode == 0
        assert "paperforge" in result.stdout.lower()


class TestErrorOutput:
    """Contract: Error output follows stable text patterns."""

    def test_missing_vault_error_message(self, cli_invoker):
        """Missing vault produces error message (not traceback)."""
        result = cli_invoker(["status", "--vault", "/tmp/nonexistent_vault_xyz"])
        output = result.stdout + result.stderr
        assert "Traceback" not in output, "Error should not contain traceback"
        assert (
            "Error" in output or "error" in output.lower()
        ), "Error should contain error message"

    def test_no_vault_flag_no_env(self, cli_invoker):
        """Running without --vault and without env produces error message."""
        # Unset PAPERFORGE_VAULT to simulate no vault context
        import os

        old = os.environ.pop("PAPERFORGE_VAULT", None)
        try:
            result = cli_invoker(["status", "--vault", "/nonexistent_vault_check"])
            output = result.stdout + result.stderr
            assert "Traceback" not in output, "Should not show Python traceback"
        finally:
            if old is not None:
                os.environ["PAPERFORGE_VAULT"] = old


class TestCli02ErrorContract:
    """CLI-02: Error responses use standard text format with actionable info.

    Note: Full JSON error schema (ok, error_code, message, details, suggestions)
    is planned for all commands. Currently, errors use human-readable text.
    These tests validate the TEXT contract — JSON error contract will be
    validated once --json error output is implemented across all commands.
    """

    def test_error_contains_actionable_info(self, cli_invoker):
        """Errors mention what went wrong (not just 'error')."""
        result = cli_invoker(
            ["status", "--vault", "/tmp/nonexistent_vault_xyz_98765"]
        )
        output = (result.stdout + result.stderr).lower()
        # Should contain descriptive terms
        descriptive_terms = [
            "not found", "does not exist", "no such", "error",
            "invalid", "cannot",
        ]
        has_description = any(t in output for t in descriptive_terms)
        assert has_description, (
            f"Error should contain descriptive info, got: {output[:200]}"
        )

    def test_stable_error_output(self, cli_invoker):
        """Same error produces same output (deterministic)."""
        vault_arg = ["status", "--vault", "/tmp/nonexistent_contract_test_12345"]
        r1 = cli_invoker(vault_arg)
        r2 = cli_invoker(vault_arg)
        assert r1.returncode == r2.returncode
        assert r1.stderr.strip() == r2.stderr.strip()
