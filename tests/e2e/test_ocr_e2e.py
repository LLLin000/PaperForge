"""E2E test: OCR pipeline verification.

Uses the 'full' vault level which includes pre-populated OCR fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e


def test_ocr_fixtures_present(full_vault: Path) -> None:
    """Verify OCR fixture files exist in the full vault level."""
    ocr_dir = full_vault / "System" / "PaperForge" / "ocr" / "FIXT0001"
    assert ocr_dir.exists(), f"OCR directory not found: {ocr_dir}"

    # meta.json exists with ocr_status: done
    meta_path = ocr_dir / "meta.json"
    assert meta_path.exists(), f"meta.json not found: {meta_path}"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta.get("ocr_status") == "done", f"Expected ocr_status 'done', got '{meta.get('ocr_status')}'"

    # extracted_fulltext.md exists (fixture uses this name)
    fulltext_path = ocr_dir / "extracted_fulltext.md"
    assert fulltext_path.exists(), f"extracted_fulltext.md not found: {fulltext_path}"
    assert len(fulltext_path.read_text(encoding="utf-8")) > 0, "extracted_fulltext.md is empty"

    # figure_map.json exists
    figure_map_path = ocr_dir / "figure_map.json"
    assert figure_map_path.exists(), f"figure_map.json not found: {figure_map_path}"


def test_ocr_formal_note_has_ocr_reference(full_vault: Path) -> None:
    """Verify the formal note frontmatter references OCR status."""
    lit_dir = full_vault / "Resources" / "Literature" / "orthopedic"
    note_files = list(lit_dir.rglob("*.md"))
    assert len(note_files) >= 1, f"No formal notes found in {lit_dir}"

    # Read the first note and verify frontmatter
    note_content = note_files[0].read_text(encoding="utf-8")
    frontmatter_start = note_content.find("---\n")
    frontmatter_end = note_content.find("---\n", frontmatter_start + 4)
    assert frontmatter_start >= 0 and frontmatter_end > frontmatter_start, "No valid frontmatter found"

    frontmatter = note_content[frontmatter_start:frontmatter_end + 4]
    assert "do_ocr:" in frontmatter, "Frontmatter missing do_ocr field"
    assert "ocr_status:" in frontmatter, "Frontmatter missing ocr_status field"
