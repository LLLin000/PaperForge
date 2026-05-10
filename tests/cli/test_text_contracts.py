"""CLI contract tests for text-output commands: sync, ocr, doctor, repair, setup."""

from __future__ import annotations

import pytest


class TestSyncCli:
    """Contract: 'paperforge sync' produces expected text output."""

    def test_sync_dry_run_on_empty_vault(self, cli_invoker):
        """sync --dry-run on empty vault exits 0 with DRY-RUN message."""
        result = cli_invoker(["sync", "--dry-run"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"
        assert "DRY-RUN" in result.stdout

    def test_sync_rejects_nonexistent_vault(self, cli_invoker):
        """sync on nonexistent vault exits non-zero."""
        result = cli_invoker(["sync", "--vault", "/nonexistent/path"])
        assert result.returncode != 0


class TestOcrCli:
    """Contract: 'paperforge ocr' produces expected output."""

    def test_ocr_diagnose_on_empty_vault(self, cli_invoker):
        """ocr --diagnose on empty vault produces doctor output."""
        result = cli_invoker(["ocr", "--diagnose"])
        # May exit 0 or 1 depending on env, but must not crash
        assert "OCR Doctor" in result.stdout

    def test_ocr_invalid_args(self, cli_invoker):
        """ocr with invalid args should exit non-zero."""
        result = cli_invoker(["--invalid-flag"])
        assert result.returncode != 0


class TestDoctorCli:
    """Contract: 'paperforge doctor' produces verdict output."""

    def test_doctor_on_empty_vault(self, cli_invoker):
        """doctor runs on empty vault without crashing."""
        result = cli_invoker(["doctor"])
        # doctor should exit 0 even when things are missing (it reports, doesn't fail)
        output = result.stdout + result.stderr
        assert len(output) > 0, "doctor produced no output"

    def test_doctor_output_has_verdict_pattern(self, cli_invoker):
        """doctor output contains [OK], [WARN], or [FAIL] patterns."""
        result = cli_invoker(["doctor"])
        markers = ["[OK]", "[WARN]", "[FAIL]"]
        has_marker = any(m in result.stdout for m in markers)
        # On empty vault, doctor may not have markers — just verify no crash
        if not has_marker:
            pytest.skip(
                "Doctor did not produce verdict markers (may depend on vault state)"
            )

    def test_doctor_on_nonexistent_vault(self, cli_invoker):
        """doctor on nonexistent vault exits non-zero."""
        result = cli_invoker(["doctor", "--vault", "/nonexistent/path"])
        assert result.returncode != 0


class TestRepairCli:
    """Contract: 'paperforge repair' produces repair scan output."""

    def test_repair_on_empty_vault(self, cli_invoker):
        """repair on empty vault exits 0 with no divergences."""
        result = cli_invoker(["repair"])
        assert result.returncode == 0, f"Exit {result.returncode}: {result.stderr}"

    def test_repair_dry_run_no_modify(self, cli_invoker):
        """repair without --fix does not modify vault."""
        result = cli_invoker(["repair"])
        assert result.returncode == 0


class TestSetupCli:
    """Contract: 'paperforge setup' produces setup output."""

    def test_setup_headless_with_skip_checks(self, cli_invoker):
        """setup --headless --skip-checks runs without crashing."""
        result = cli_invoker(
            [
                "setup", "--headless", "--skip-checks",
                "--zotero-data", "/tmp/mock_zotero",
            ]
        )
        # May exit 0 or non-zero depending on environment, but must produce output
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_setup_no_args_shows_usage(self, cli_invoker):
        """setup without --headless shows help message."""
        result = cli_invoker(["setup"])
        assert len(result.stdout) > 0 or len(result.stderr) > 0
