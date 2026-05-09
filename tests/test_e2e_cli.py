"""End-to-end CLI tests for PaperForge.

Invokes paperforge CLI commands as subprocesses (same path as the Obsidian plugin).
Catches bugs in the subprocess boundary that pure Python API tests miss:
- Python interpreter resolution
- Working directory behavior
- JSON stdout parsing
- Exit code propagation
- CLI argument parsing
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a CLI command as subprocess and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "paperforge"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


class TestCliSync:
    """E2E: paperforge sync via subprocess."""

    def test_sync_runs_cleanly(self, test_vault: Path) -> None:
        """Sync completes with exit code 0 and produces index."""
        result = _run(["sync"], test_vault)
        assert result.returncode == 0, f"sync failed: {result.stderr[:500]}"

        # Index file should exist
        idx = test_vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json"
        assert idx.exists(), "index file should exist after sync"
        data = json.loads(idx.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "items" in data
        assert len(data["items"]) > 0

    def test_sync_produces_formal_note(self, test_vault: Path) -> None:
        """After sync, at least one workspace note exists with correct frontmatter."""
        _run(["sync"], test_vault)

        lit_dir = test_vault / "03_Resources" / "Literature"
        ws_notes = list(lit_dir.rglob("TSTONE001 - *.md"))
        assert len(ws_notes) > 0, "no workspace note found after sync"

        text = ws_notes[0].read_text(encoding="utf-8")
        assert "zotero_key:" in text
        assert "do_ocr:" in text
        assert "ocr_status:" in text
        assert "pdf_path:" in text
        assert "[[" in text and "]]" in text  # wikilink


class TestCliStatus:
    """E2E: paperforge status --json via subprocess."""

    def test_status_json_is_valid(self, test_vault: Path) -> None:
        """status --json produces valid PFResult with expected keys."""
        _run(["sync"], test_vault)
        result = _run(["status", "--json"], test_vault)

        assert result.returncode == 0
        envelope = json.loads(result.stdout)
        assert isinstance(envelope, dict)
        assert envelope["ok"] is True
        assert envelope["command"] == "status"
        assert "version" in envelope
        assert "total_papers" in envelope["data"]

    def test_status_json_counts_are_correct(self, test_vault: Path) -> None:
        """After sync, status reports at least 1 paper."""
        _run(["sync"], test_vault)
        result = _run(["status", "--json"], test_vault)

        envelope = json.loads(result.stdout)
        assert envelope["data"]["total_papers"] >= 1


class TestCliDoctor:
    """E2E: paperforge doctor via subprocess."""

    def test_doctor_runs_cleanly(self, test_vault: Path) -> None:
        """Doctor completes with exit code 0 or 1 (diagnostic, not crash)."""
        result = _run(["doctor"], test_vault)
        assert result.returncode in (0, 1), f"doctor crashed: {result.stderr[:500]}"

    def test_doctor_outputs_verdict(self, test_vault: Path) -> None:
        """Doctor output contains [OK], [WARN], or [FAIL] verdict."""
        result = _run(["doctor"], test_vault)
        stdout = result.stdout or ""
        assert any(tag in stdout for tag in ["[OK]", "[WARN]", "[FAIL]"]), (
            f"No verdict in doctor output. stdout={stdout[:200]} stderr={(result.stderr or '')[:200]}"
        )


class TestCliDeepReading:
    """E2E: paperforge deep-reading (queue check) via subprocess."""

    def test_deep_reading_runs_cleanly(self, test_vault: Path) -> None:
        """deep-reading completes without crash."""
        _run(["sync"], test_vault)
        result = _run(["deep-reading"], test_vault)
        assert result.returncode == 0, f"deep-reading failed: {result.stderr[:500]}"


class TestCliFullPipeline:
    """E2E: full sync -> status -> doctor pipeline via subprocess."""

    def test_full_pipeline_consistency(self, test_vault: Path) -> None:
        """Run sync, then verify index -> status -> doctor are all consistent."""
        # sync
        sync_result = _run(["sync"], test_vault)
        assert sync_result.returncode == 0

        # status --json — read the index the same way the dashboard does
        status_result = _run(["status", "--json"], test_vault)
        assert status_result.returncode == 0
        envelope = json.loads(status_result.stdout)
        assert envelope["data"]["total_papers"] >= 1
        assert envelope["version"] != ""

        # doctor — should produce a verdict (may pass or warn)
        doctor_result = _run(["doctor"], test_vault)
        assert any(tag in doctor_result.stdout for tag in ["[OK]", "[WARN]", "[FAIL]"])

        # Verify frontmatter file is readable
        lit_dir = test_vault / "03_Resources" / "Literature"
        ws_notes = list(lit_dir.rglob("TSTONE001 - *.md"))
        assert len(ws_notes) > 0
        text = ws_notes[0].read_text(encoding="utf-8")
        assert "has_pdf: true" in text

    def test_missing_vault_does_not_crash(self, tmp_path: Path) -> None:
        """Sync in a bare directory does not crash (auto-creates config)."""
        result = _run(["sync"], tmp_path)
        assert result.returncode in (0, 1), f"unexpected crash: {result.stderr[:500]}"
        assert "traceback" not in result.stderr.lower()
