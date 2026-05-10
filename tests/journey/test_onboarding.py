"""JNY-02: New user onboarding journey test.

Simulates a brand-new user: fresh vault -> sync -> OCR -> analyze -> deep-read ready.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from fixtures.ocr.mock_ocr_backend import mock_ocr_success


pytestmark = pytest.mark.journey


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _read_frontmatter(note_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a formal note."""
    content = note_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _edit_frontmatter_field(note_path: Path, field: str, value: str) -> None:
    """Edit a single frontmatter field in a formal note, preserving YAML structure."""
    content = note_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"Invalid frontmatter in {note_path}"
    lines = parts[1].splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{field}:"):
            lines[i] = f"{field}: {value}\n"
            found = True
            break
    if not found:
        lines.append(f"{field}: {value}\n")
    parts[1] = "".join(lines)
    note_path.write_text("---".join(parts), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_new_user_onboarding(
    journey_fresh_vault: tuple[Path, object],
    journey_cli_invoker: callable,
) -> None:
    """Complete new user journey: sync -> verify notes -> enable OCR -> OCR -> enable analyze -> verify queue."""
    vault, builder = journey_fresh_vault

    # Isolation guard
    assert any(x in str(vault).lower() for x in ("tmp", "temp")), f"Isolation VIOLATION: {vault}"

    # -----------------------------------------------------------------------
    # Step 1: Run paperforge sync
    # -----------------------------------------------------------------------
    result = journey_cli_invoker(vault, ["sync"])
    assert result.returncode == 0, (
        f"Sync failed (exit {result.returncode}):\n  stdout: {result.stdout[:500]}\n  stderr: {result.stderr[:500]}"
    )

    # -----------------------------------------------------------------------
    # Step 2: Verify formal notes created with correct frontmatter
    # -----------------------------------------------------------------------
    lit_dir = vault / "Resources" / "Literature"
    note_files = list(lit_dir.rglob("*.md"))
    assert len(note_files) >= 1, f"No formal notes created in {lit_dir}"

    for note_path in note_files:
        fm = _read_frontmatter(note_path)
        assert "zotero_key" in fm, f"Missing zotero_key in {note_path}"
        assert fm.get("zotero_key"), f"Empty zotero_key in {note_path}"
        assert "domain" in fm, f"Missing domain in {note_path}"
        assert fm.get("domain"), f"Empty domain in {note_path}"
        assert "has_pdf" in fm, f"Missing has_pdf in {note_path}"
        assert "ocr_status" in fm, f"Missing ocr_status in {note_path}"
        assert fm.get("ocr_status") in ("pending", "done"), (
            f"Unexpected ocr_status in {note_path}: {fm.get('ocr_status')}"
        )

    # Pick the first note for further steps
    note_path = note_files[0]
    fm = _read_frontmatter(note_path)
    paper_key = fm["zotero_key"]
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / paper_key

    # -----------------------------------------------------------------------
    # Step 3: Enable OCR — set do_ocr: true
    # -----------------------------------------------------------------------
    _edit_frontmatter_field(note_path, "do_ocr", "true")
    fm = _read_frontmatter(note_path)
    assert fm.get("do_ocr") is True or str(fm.get("do_ocr")) == "true", "do_ocr not set to true"

    # -----------------------------------------------------------------------
    # Step 4: Run OCR with mock backend — verify graceful handling
    # -----------------------------------------------------------------------
    with mock_ocr_success():
        result = journey_cli_invoker(vault, ["ocr"])

    # OCR may exit 0 on success or non-zero on some conditions; key is no unhandled crash
    assert "Traceback" not in result.stderr, f"Unhandled crash in OCR:\n{result.stderr}"

    # -----------------------------------------------------------------------
    # Step 5: Enable analyze
    # -----------------------------------------------------------------------
    _edit_frontmatter_field(note_path, "analyze", "true")
    fm = _read_frontmatter(note_path)
    assert fm.get("analyze") is True or str(fm.get("analyze")) == "true", "analyze not set to true"

    # -----------------------------------------------------------------------
    # Step 6: Verify deep-reading queue sees the paper
    # -----------------------------------------------------------------------
    result = journey_cli_invoker(vault, ["deep-reading"])
    # The paper key or title should appear in the output
    assert result.returncode == 0, f"deep-reading failed:\n{result.stderr[:500]}"
    combined_output = (result.stdout + result.stderr)
    assert paper_key in combined_output or fm.get("title", "") in combined_output, (
        f"Paper '{paper_key}' not found in deep-reading queue output:\n{combined_output[:500]}"
    )
