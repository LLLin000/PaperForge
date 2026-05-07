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
from paperforge.worker.asset_index import build_index, read_index
from paperforge.worker.sync import run_index_refresh, run_selection_sync


def _find_workspace_note(test_vault: Path, key: str = "TSTONE001") -> Path | None:
    """Find the workspace formal note for a given zotero_key.

    Looks in Literature/<domain>/<key> - <Title>/ directories for the note.
    This is the Phase 38 workspace path (not the flat path).
    """
    paths = paperforge_paths(test_vault)
    for domain_dir in sorted(paths["literature"].iterdir()):
        if not domain_dir.is_dir():
            continue
        for ws_dir in sorted(domain_dir.iterdir()):
            if not ws_dir.is_dir() or not ws_dir.name.startswith(f"{key} - "):
                continue
            notes = list(ws_dir.glob(f"{key} - *.md"))
            if notes:
                return notes[0]
    return None


def _test_note_text(test_vault: Path) -> str:
    """Helper: run index refresh and return workspace note text."""
    run_index_refresh(test_vault)
    note_path = _find_workspace_note(test_vault)
    assert note_path is not None, "workspace note should exist after index refresh"
    return note_path.read_text(encoding="utf-8")


class TestSelectionSyncCompletesCleanly:
    """E2E: selection-sync runs cleanly (Phase 37: library-records deprecated)."""

    def test_selection_sync_runs_without_error(self, test_vault: Path) -> None:
        """Verify selection-sync completes without exceptions."""
        count = run_selection_sync(test_vault)
        assert isinstance(count, int)

    def test_index_refresh_produces_workflow_frontmatter(self, test_vault: Path) -> None:
        """Verify formal notes have required workflow frontmatter after sync pipeline."""
        text = _test_note_text(test_vault)

        assert "zotero_key:" in text
        assert "title:" in text
        assert "year:" in text
        assert "doi:" in text
        assert "has_pdf:" in text
        assert "pdf_path:" in text
        assert "do_ocr:" in text
        assert "analyze:" in text
        assert "ocr_status:" in text
        assert "deep_reading_status:" in text
        assert "first_author:" in text
        assert "journal:" in text
        assert "fulltext_md_path:" in text

    def test_formal_note_pdf_wikilink_is_valid(self, test_vault: Path) -> None:
        """Verify pdf_path is a valid Obsidian wikilink with forward slashes."""
        text = _test_note_text(test_vault)

        pdf_link_match = re.search(r"pdf_path:\s*\"\[\[(.+?)\]\]\"", text)
        assert pdf_link_match is not None, "pdf_path should be a wikilink"
        pdf_link = pdf_link_match.group(1)

        assert "\\" not in pdf_link, f"wikilink should use forward slashes, got: {pdf_link}"
        assert pdf_link.endswith(".pdf"), "wikilink should point to a PDF file"
        assert "TSTONE001" in pdf_link, "wikilink should reference TSTONE001 storage key"

    def test_ocr_status_in_formal_note(self, test_vault: Path) -> None:
        """Verify TSTONE001 gets a non-empty ocr_status in formal note."""
        text = _test_note_text(test_vault)

        ocr_match = re.search(r"^ocr_status:\s*\"?(\w+)\"?\s*$", text, re.MULTILINE)
        assert ocr_match is not None, "ocr_status should be present"
        ocr_status = ocr_match.group(1)
        assert ocr_status in ("done", "pending", "nopdf"), f"unexpected ocr_status: {ocr_status}"

    def test_first_author_and_journal_in_formal_note(self, test_vault: Path) -> None:
        """Verify formal notes include first_author and journal."""
        text = _test_note_text(test_vault)

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
        text = _test_note_text(test_vault)

        # Required frontmatter fields for formal notes (slimmed Phase 37)
        assert "title:" in text
        assert "year:" in text
        assert "journal:" in text
        assert "first_author:" in text
        assert "domain:" in text
        assert "tags:" in text
        assert "has_pdf:" in text
        assert "do_ocr:" in text
        assert "analyze:" in text
        assert "ocr_status:" in text
        assert "deep_reading_status:" in text
        assert "pdf_path:" in text

    def test_formal_note_pdf_link_is_wikilink(self, test_vault: Path) -> None:
        """Verify pdf_path in formal notes is a valid Obsidian wikilink."""
        text = _test_note_text(test_vault)

        pdf_link_match = re.search(r"pdf_path:\s*\"\[\[(.+?)\]\]\"", text)
        assert pdf_link_match is not None, "pdf_path should be a wikilink"

        link = pdf_link_match.group(1)
        assert "\\" not in link, f"wikilink should use forward slashes, got: {link}"
        assert link.endswith(".pdf")

    def test_formal_note_has_abstract_content(self, test_vault: Path) -> None:
        """Verify formal note body contains the abstract from the export JSON."""
        text = _test_note_text(test_vault)

        # Abstract from 骨科.json: "This study compares the biomechanical properties..."
        assert "biomechanical" in text.lower() or "suture anchor" in text.lower()

    def test_formal_note_filename_uses_slug(self, test_vault: Path) -> None:
        """Verify the formal note filename uses slugified title."""
        run_index_refresh(test_vault)
        note_path = _find_workspace_note(test_vault)
        assert note_path is not None
        # Filename should start with key + " - " + slug
        assert note_path.name.startswith("TSTONE001 - ")


class TestOcrQueueStates:
    """E2E: OCR queue and state transitions are correct after pipeline run."""

    def _load_index_entry(self, test_vault: Path, key: str) -> dict | None:
        """Helper: load canonical index and find entry by zotero_key."""
        index = read_index(test_vault)
        if not index or not isinstance(index, dict):
            return None
        for item in index.get("items", []):
            if item.get("zotero_key") == key:
                return item
        return None

    def test_index_entry_has_tstone001_with_ocr_done(self, test_vault: Path) -> None:
        """Verify TSTONE001 appears in canonical index with ocr_status=done."""
        build_index(test_vault)
        entry = self._load_index_entry(test_vault, "TSTONE001")
        assert entry is not None, "TSTONE001 should be in canonical index"
        assert entry["domain"] == "骨科"
        assert entry["ocr_status"] == "done"

    def test_index_entry_ocr_status_done(self, test_vault: Path) -> None:
        """Verify TSTONE001 has OCR status 'done' (fixture has meta.json with ocr_status: done)."""
        build_index(test_vault)
        entry = self._load_index_entry(test_vault, "TSTONE001")
        assert entry is not None
        assert entry["ocr_status"] == "done", (
            f"Expected ocr_status=done, got: {entry['ocr_status']}"
        )

    def test_full_pipeline_consistency(self, test_vault: Path) -> None:
        """Run full pipeline and verify consistency across all stages."""
        # Stage 1: selection-sync runs without error
        run_selection_sync(test_vault)

        # Stage 2: index-refresh produces formal note in workspace
        text = _test_note_text(test_vault)
        note_path = _find_workspace_note(test_vault)
        assert note_path is not None, "Stage 2: formal note should exist in workspace"

        # Stage 3: Formal note frontmatter has core fields
        assert "title:" in text, "Stage 3: title should be in formal note"
        assert "doi:" in text, "Stage 3: doi should be in formal note"
        assert "has_pdf:" in text, "Stage 3: has_pdf should be in formal note"
        assert "do_ocr:" in text, "Stage 3: do_ocr should be in formal note"
        assert "ocr_status:" in text, "Stage 3: ocr_status should be in formal note"

        # Stage 4: Canonical index has correct OCR state
        build_index(test_vault)
        entry = self._load_index_entry(test_vault, "TSTONE001")
        assert entry is not None, "Stage 4: TSTONE001 should be in canonical index"
        assert entry["ocr_status"] == "done", "Stage 4: OCR status should be done"

        # Stage 5: Formal note links to correct PDF location
        pdf_link_match = re.search(r'pdf_path:\s*"\[\[(.+?)\]\]"', text, re.MULTILINE)
        assert pdf_link_match is not None, "Stage 5: pdf_path should be in formal note"
        assert "TSTONE001.pdf" in pdf_link_match.group(1), (
            "Stage 5: pdf_path should reference correct PDF"
        )
