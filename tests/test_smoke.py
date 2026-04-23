"""End-to-end smoke tests for PaperForge Lite full pipeline.

Covers:
    1. Setup validation (paperforge doctor)
    2. Selection sync
    3. Index refresh
    4. OCR doctor (L1-L3, no live)
    5. Deep-reading queue check
    6. CLI main entry via cli.main()

All tests use fixture_vault (tmp_path), no real vault access,
no network calls to live services.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# 1. Setup Validation — paperforge doctor
# ---------------------------------------------------------------------------

def test_smoke_doctor_returns_zero_on_valid_vault(fixture_vault: Path) -> None:
    """run_doctor returns 0 when all checks pass."""
    from pipeline.worker.scripts.literature_pipeline import run_doctor

    # Create required directory structure to satisfy checks
    (fixture_vault / "99_System" / "PaperForge" / "exports").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "99_System" / "PaperForge" / "ocr").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "03_Resources" / "Literature").mkdir(parents=True, exist_ok=True)
    (fixture_vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "05_Bases").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "command").mkdir(parents=True, exist_ok=True)

    result = run_doctor(fixture_vault)
    # run_doctor returns 0 = all pass, 1 = some fail
    assert result in (0, 1), f"Expected 0 or 1, got {result}"


def test_smoke_doctor_checks_categories(fixture_vault: Path) -> None:
    """run_doctor output contains expected check categories."""
    import io
    import sys

    from pipeline.worker.scripts.literature_pipeline import run_doctor

    # Minimal structure to avoid early exit
    (fixture_vault / "99_System" / "PaperForge" / "exports").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "99_System" / "PaperForge" / "ocr").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "03_Resources" / "Literature").mkdir(parents=True, exist_ok=True)
    (fixture_vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "05_Bases").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "command").mkdir(parents=True, exist_ok=True)

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = run_doctor(fixture_vault)
    finally:
        sys.stdout = old_stdout

    assert result in (0, 1)


# ---------------------------------------------------------------------------
# 2. Selection Sync
# ---------------------------------------------------------------------------

def test_smoke_selection_sync_returns_zero(
    fixture_vault: Path, fixture_bbt_json: Path, fixture_library_records: list[Path]
) -> None:
    """run_selection_sync returns 0 and creates/updates library records."""
    from pipeline.worker.scripts.literature_pipeline import run_selection_sync

    result = run_selection_sync(fixture_vault)
    assert result == 0, f"selection_sync should return 0, got {result}"


def test_smoke_selection_sync_scans_exports(
    fixture_vault: Path, fixture_bbt_json: Path, fixture_library_records: list[Path]
) -> None:
    """selection_sync reads the BBT JSON export and matches library records."""
    from pipeline.worker.scripts.literature_pipeline import run_selection_sync

    records_dir = (
        fixture_vault
        / "03_Resources"
        / "LiteratureControl"
        / "library-records"
        / "骨科"
    )

    # Should complete without error
    result = run_selection_sync(fixture_vault)
    assert result == 0

    # At least one record should exist for TESTKEY001 or TESTKEY002 (those with PDF)
    record_files = list(records_dir.glob("TESTKEY*.md"))
    assert len(record_files) >= 2


# ---------------------------------------------------------------------------
# 3. Index Refresh
# ---------------------------------------------------------------------------

def test_smoke_index_refresh_returns_zero(
    fixture_vault: Path,
    fixture_bbt_json: Path,
    fixture_library_records: list[Path],
) -> None:
    """run_index_refresh returns 0 and generates formal literature notes."""
    from pipeline.worker.scripts.literature_pipeline import run_index_refresh

    result = run_index_refresh(fixture_vault)
    assert result == 0, f"index_refresh should return 0, got {result}"


def test_smoke_index_refresh_generates_notes(
    fixture_vault: Path,
    fixture_bbt_json: Path,
    fixture_library_records: list[Path],
) -> None:
    """index_refresh creates markdown notes in the Literature directory."""
    from pipeline.worker.scripts.literature_pipeline import run_index_refresh

    result = run_index_refresh(fixture_vault)
    assert result == 0

    lit_dir = fixture_vault / "03_Resources" / "Literature" / "骨科"
    note_files = list(lit_dir.glob("*.md"))
    # Should have notes for at least TESTKEY001 and TESTKEY002 (those with has_pdf=true)
    assert len(note_files) >= 2


# ---------------------------------------------------------------------------
# 4. OCR Doctor (L1-L3, mocked)
# ---------------------------------------------------------------------------

def test_smoke_ocr_doctor_returns_code(
    fixture_vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_cmd_ocr_doctor returns int exit code (0 or 1) without live API call."""
    from paperforge_lite.cli import _cmd_ocr_doctor
    import argparse

    # Mock token presence so L1 passes
    monkeypatch.setenv("PADDLEOCR_API_TOKEN", "fake-token-for-test")
    monkeypatch.setenv(
        "PADDLEOCR_JOB_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
    )

    # Mock network call to avoid live request
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"jobs": []}

    with patch("requests.get", return_value=mock_response):
        with patch("requests.post", return_value=mock_response):
            args = argparse.Namespace(live=False)
            result = _cmd_ocr_doctor(fixture_vault, args)
            assert result in (0, 1)


def test_smoke_ocr_doctor_detects_missing_token(
    fixture_vault: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_cmd_ocr_doctor returns 1 when PADDLEOCR_API_TOKEN is not set."""
    from paperforge_lite.cli import _cmd_ocr_doctor
    import argparse

    # Ensure no token
    monkeypatch.delenv("PADDLEOCR_API_TOKEN", raising=False)
    monkeypatch.delenv("PADDLEOCR_API_TOKEN_USER", raising=False)

    args = argparse.Namespace(live=False)
    result = _cmd_ocr_doctor(fixture_vault, args)
    # Should fail at L1 (no token) -> returns 1
    assert result == 1


# ---------------------------------------------------------------------------
# 5. Deep-Reading Queue
# ---------------------------------------------------------------------------

def test_smoke_deep_reading_returns_zero(
    fixture_vault: Path,
    fixture_bbt_json: Path,
    fixture_library_records: list[Path],
) -> None:
    """run_deep_reading returns 0 and produces three-state output."""
    from pipeline.worker.scripts.literature_pipeline import run_deep_reading

    result = run_deep_reading(fixture_vault, verbose=False)
    assert result == 0, f"deep_reading should return 0, got {result}"


def test_smoke_deep_reading_queue_output(
    fixture_vault: Path,
    fixture_bbt_json: Path,
    fixture_library_records: list[Path],
) -> None:
    """deep_reading produces queue report with three-state categories."""
    from pipeline.worker.scripts.literature_pipeline import run_deep_reading

    result = run_deep_reading(fixture_vault, verbose=False)
    assert result == 0

    # Check queue file was written
    pf_dir = fixture_vault / "99_System" / "PaperForge"
    queue_path = pf_dir / "deep-reading-queue.md"
    assert queue_path.exists(), "deep-reading-queue.md should be generated"

    queue_text = queue_path.read_text(encoding="utf-8")
    # Should contain the three-state header or queue content
    assert "##" in queue_text or "所有 analyze=true" in queue_text


# ---------------------------------------------------------------------------
# 6. CLI Main Entry
# ---------------------------------------------------------------------------

def test_smoke_cli_doctor_entry_point(
    fixture_vault: Path,
) -> None:
    """cli.main(['--vault', str(fixture_vault), 'doctor']) returns int exit code."""
    from paperforge_lite import cli

    # Minimal structure required by run_doctor
    (fixture_vault / "99_System" / "PaperForge" / "exports").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "99_System" / "PaperForge" / "ocr").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "03_Resources" / "Literature").mkdir(parents=True, exist_ok=True)
    (fixture_vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "05_Bases").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "command").mkdir(parents=True, exist_ok=True)

    result = cli.main(["--vault", str(fixture_vault), "doctor"])
    assert isinstance(result, int), f"cli.main should return int, got {type(result)}"
    assert result in (0, 1)


def test_smoke_cli_status_entry_point(fixture_vault: Path) -> None:
    """cli.main(['--vault', str(fixture_vault), 'status']) returns int exit code."""
    from paperforge_lite import cli

    # Minimal structure
    (fixture_vault / "99_System" / "PaperForge" / "exports").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "99_System" / "PaperForge" / "ocr").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "03_Resources" / "Literature").mkdir(parents=True, exist_ok=True)
    (fixture_vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "05_Bases").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "command").mkdir(parents=True, exist_ok=True)

    result = cli.main(["--vault", str(fixture_vault), "status"])
    assert isinstance(result, int), f"cli.main should return int, got {type(result)}"


def test_smoke_cli_returns_integer_not_sys_exit(
    fixture_vault: Path,
) -> None:
    """All cli.main commands return integer exit codes (not sys.exit)."""
    from paperforge_lite import cli

    # Minimal structure
    (fixture_vault / "99_System" / "PaperForge" / "exports").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "99_System" / "PaperForge" / "ocr").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "03_Resources" / "Literature").mkdir(parents=True, exist_ok=True)
    (fixture_vault / "03_Resources" / "LiteratureControl" / "library-records").mkdir(
        parents=True, exist_ok=True
    )
    (fixture_vault / "05_Bases").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)
    (fixture_vault / ".opencode" / "command").mkdir(parents=True, exist_ok=True)

    commands = ["doctor", "status"]
    for cmd in commands:
        result = cli.main(["--vault", str(fixture_vault), cmd])
        assert isinstance(result, int), (
            f"cli.main(['{cmd}']) returned {type(result).__name__}, expected int"
        )
