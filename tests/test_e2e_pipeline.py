"""End-to-end integration tests for the PaperForge literature pipeline.

Covers: Zotero JSON export -> selection-sync -> index-refresh -> OCR queue -> formal notes.

Uses the existing test_vault fixture from conftest.py which already has:
- paperforge.json with correct paths
- exports/骨科.json with TSTONE001 journal article
- OCR fixture at ocr/TSTONE001/ (ocr_status: done, with fulltext.md and json/result.json)
- Zotero/storage/TSTONE001/TSTONE001.pdf (mock PDF)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from paperforge.config import paperforge_paths
from paperforge.worker._utils import scan_library_records
from paperforge.worker.sync import run_index_refresh, run_selection_sync, update_frontmatter_field


class TestSelectionSyncProducesLibraryRecords:
    """E2E: selection-sync produces correct library records."""

    def test_selection_sync_runs_without_error(self, test_vault: Path) -> None:
        """Verify selection-sync completes without exceptions."""
        count = run_selection_sync(test_vault)
        assert isinstance(count, int)

    def test_library_record_has_required_frontmatter(self, test_vault: Path) -> None:
        """Verify the TSTONE001 library record has all required frontmatter fields."""
        run_selection_sync(test_vault)
        paths = paperforge_paths(test_vault)
        record_path = paths["library_records"] / "骨科" / "TSTONE001.md"
        assert record_path.exists(), "library record should exist after sync"

        text = record_path.read_text(encoding="utf-8")

        # Required fields per AGENTS.md Section 7
        assert 'zotero_key: "TSTONE001"' in text
        assert 'domain: "骨科"' in text
        assert "title:" in text
        assert "year:" in text
        assert "doi:" in text
        assert "has_pdf:" in text
        assert "pdf_path:" in text
        assert "recommend_analyze:" in text
        assert "analyze:" in text
        assert "do_ocr:" in text
        assert "ocr_status:" in text
        assert "deep_reading_status:" in text

    def test_library_record_wikilink_is_valid(self, test_vault: Path) -> None:
        """Verify pdf_path is a valid Obsidian wikilink with forward slashes."""
        run_selection_sync(test_vault)
        paths = paperforge_paths(test_vault)
        record_path = paths["library_records"] / "骨科" / "TSTONE001.md"
        text = record_path.read_text(encoding="utf-8")

        pdf_link_match = re.search(r"pdf_path:\s*\"\[\[(.+?)\]\]\"", text)
        assert pdf_link_match is not None, "pdf_path should be a wikilink"
        pdf_link = pdf_link_match.group(1)

        # Must use forward slashes (per D-03)
        assert "\\" not in pdf_link, f"wikilink should use forward slashes, got: {pdf_link}"
        assert pdf_link.endswith(".pdf"), "wikilink should point to a PDF file"
        assert "TSTONE001" in pdf_link, "wikilink should reference TSTONE001 storage key"

    def test_pdf_with_attachment_has_ocr_status(self, test_vault: Path) -> None:
        """Verify TSTONE001 (has PDF) gets a non-empty ocr_status."""
        run_selection_sync(test_vault)
        paths = paperforge_paths(test_vault)
        record_path = paths["library_records"] / "骨科" / "TSTONE001.md"
        text = record_path.read_text(encoding="utf-8")

        ocr_match = re.search(r"^ocr_status:\s*\"?(\w+)\"?\s*$", text, re.MULTILINE)
        assert ocr_match is not None, "ocr_status should be present"
        ocr_status = ocr_match.group(1)
        assert ocr_status in ("done", "pending", "nopdf"), f"unexpected ocr_status: {ocr_status}"

    def test_first_author_and_journal_present(self, test_vault: Path) -> None:
        """Verify library records include first_author and journal."""
        run_selection_sync(test_vault)
        paths = paperforge_paths(test_vault)
        record_path = paths["library_records"] / "骨科" / "TSTONE001.md"
        text = record_path.read_text(encoding="utf-8")

        fa_match = re.search(r"^first_author:\s*\"?(.+?)\"?$", text, re.MULTILINE)
        assert fa_match is not None, "first_author should be present"
        assert fa_match.group(1).strip(), "first_author should not be empty"

        j_match = re.search(r"^journal:\s*\"?(.+?)\"?$", text, re.MULTILINE)
        assert j_match is not None, "journal should be present"
        assert j_match.group(1).strip(), "journal should not be empty"


class TestIndexRefreshProducesFormalNotes:
    """E2E: index-refresh produces correct formal notes."""

    def test_index_refresh_runs_without_error(self, test_vault: Path) -> None:
        """Verify index-refresh completes without exceptions."""
        count = run_index_refresh(test_vault)
        assert isinstance(count, int)

    def test_formal_note_has_required_frontmatter(self, test_vault: Path) -> None:
        """Verify formal notes have required frontmatter fields per actual implementation."""
        run_index_refresh(test_vault)
        paths = paperforge_paths(test_vault)
        lit_dir = paths["literature"] / "骨科"
        note_files = list(lit_dir.glob("TSTONE001 - *.md"))
        assert len(note_files) >= 1, "formal note should exist for TSTONE001"

        text = note_files[0].read_text(encoding="utf-8")

        # Required frontmatter fields for formal notes (actual implementation)
        assert "title:" in text
        assert "year:" in text
        assert "type:" in text
        assert "journal:" in text
        assert "domain:" in text
        assert "tags:" in text
        assert "pdf_path:" in text

    def test_formal_note_pdf_link_is_wikilink(self, test_vault: Path) -> None:
        """Verify pdf_path in formal notes is a valid Obsidian wikilink."""
        run_index_refresh(test_vault)
        paths = paperforge_paths(test_vault)
        lit_dir = paths["literature"] / "骨科"
        note_files = list(lit_dir.glob("TSTONE001 - *.md"))
        text = note_files[0].read_text(encoding="utf-8")

        pdf_link_match = re.search(r"pdf_path:\s*\"\[\[(.+?)\]\]\"", text)
        assert pdf_link_match is not None, "pdf_path should be a wikilink"

        link = pdf_link_match.group(1)
        assert "\\" not in link, f"wikilink should use forward slashes, got: {link}"
        assert link.endswith(".pdf")

    def test_formal_note_has_abstract_content(self, test_vault: Path) -> None:
        """Verify formal note body contains the abstract from the export JSON."""
        run_index_refresh(test_vault)
        paths = paperforge_paths(test_vault)
        lit_dir = paths["literature"] / "骨科"
        note_files = list(lit_dir.glob("TSTONE001 - *.md"))
        text = note_files[0].read_text(encoding="utf-8")

        # Abstract from 骨科.json: "This study compares the biomechanical properties..."
        assert "biomechanical" in text.lower() or "suture anchor" in text.lower()

    def test_formal_note_filename_uses_slug(self, test_vault: Path) -> None:
        """Verify the formal note filename uses slugified title."""
        run_index_refresh(test_vault)
        paths = paperforge_paths(test_vault)
        lit_dir = paths["literature"] / "骨科"
        note_files = list(lit_dir.glob("TSTONE001 - *.md"))
        assert len(note_files) >= 1
        filename = note_files[0].name
        # Filename should start with key + " - " + slug
        assert filename.startswith("TSTONE001 - ")


class TestOcrQueueStates:
    """E2E: OCR queue and state transitions are correct after pipeline run."""

    def _set_analyze_true(self, test_vault: Path) -> None:
        paths = paperforge_paths(test_vault)
        record_path = paths["library_records"] / "骨科" / "TSTONE001.md"
        text = record_path.read_text(encoding="utf-8")
        record_path.write_text(update_frontmatter_field(text, "analyze", True), encoding="utf-8")

    def test_scan_library_records_returns_tstone001(self, test_vault: Path) -> None:
        """Verify TSTONE001 appears in library records scan with analyze=true."""
        run_selection_sync(test_vault)
        self._set_analyze_true(test_vault)
        records = scan_library_records(test_vault)
        tstone = [r for r in records if r["zotero_key"] == "TSTONE001"]
        assert len(tstone) >= 1, "TSTONE001 should be in library records scan"
        assert tstone[0]["analyze"] is True, "TSTONE001 should have analyze=true"
        assert tstone[0]["domain"] == "骨科"

    def test_tstone001_ocr_status_done(self, test_vault: Path) -> None:
        """Verify TSTONE001 has OCR status 'done' (fixture has meta.json with ocr_status: done)."""
        run_selection_sync(test_vault)
        self._set_analyze_true(test_vault)
        records = scan_library_records(test_vault)
        tstone = [r for r in records if r["zotero_key"] == "TSTONE001"]
        assert len(tstone) >= 1
        assert tstone[0]["ocr_status"] == "done", (
            f"Expected ocr_status=done, got: {tstone[0]['ocr_status']}"
        )

    def test_full_pipeline_consistency(self, test_vault: Path) -> None:
        """Run full pipeline and verify consistency across all stages."""
        # Stage 1: selection-sync produces library record
        run_selection_sync(test_vault)
        paths = paperforge_paths(test_vault)
        record_path = paths["library_records"] / "骨科" / "TSTONE001.md"
        assert record_path.exists(), "Stage 1: library record should exist"

        # Stage 2: index-refresh produces formal note
        run_index_refresh(test_vault)
        lit_dir = paths["literature"] / "骨科"
        note_files = list(lit_dir.glob("TSTONE001 - *.md"))
        assert len(note_files) >= 1, "Stage 2: formal note should exist"

        # Stage 3: Formal note frontmatter matches library record
        note_text = note_files[0].read_text(encoding="utf-8")
        record_text = record_path.read_text(encoding="utf-8")

        # Extract titles from both
        note_title = re.search(r'^title:\s*"(.+?)"', note_text, re.MULTILINE)
        record_title = re.search(r'^title:\s*"(.+?)"', record_text, re.MULTILINE)
        if note_title and record_title:
            assert note_title.group(1) == record_title.group(1), (
                "Formal note title should match library record title"
            )

        # Stage 4: OCR state is consistent
        self._set_analyze_true(test_vault)
        records = scan_library_records(test_vault)
        tstone = [r for r in records if r["zotero_key"] == "TSTONE001"]
        assert len(tstone) >= 1
        assert tstone[0]["ocr_status"] == "done", "Stage 4: OCR status should be done"

        # Stage 5: Formal note links to correct PDF location
        pdf_link_match = re.search(r'pdf_path:\s*"\[\[(.+?)\]\]"', note_text, re.MULTILINE)
        assert pdf_link_match is not None, "Stage 5: pdf_path should be in formal note"
        assert "TSTONE001.pdf" in pdf_link_match.group(1), (
            "Stage 5: pdf_path should reference correct PDF"
        )
