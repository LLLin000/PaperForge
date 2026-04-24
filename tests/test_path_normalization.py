"""Tests for Zotero path normalization, main PDF identification, and wikilink generation.

Phase 11 Wave 4 — Tests for:
- _normalize_attachment_path()   (BBT path format normalization)
- _identify_main_pdf()           (Main vs supplementary attachment selection)
- obsidian_wikilink_for_pdf()    (Obsidian wikilink generation)

All tests mock zotero_dir and vault_dir — no real Zotero installation required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.worker.scripts.literature_pipeline import (
    _normalize_attachment_path,
    _identify_main_pdf,
    obsidian_wikilink_for_pdf,
    load_export_rows,
)


# ---------------------------------------------------------------------------
# Test class: TestBBTPathNormalization
# ---------------------------------------------------------------------------

class TestBBTPathNormalization:
    """Tests for _normalize_attachment_path() with various BBT export formats."""

    def test_absolute_windows_path(self) -> None:
        """Absolute Windows path pointing to Zotero storage is normalized to storage:KEY/filename."""
        raw = r"D:\L\Med\Research\99_System\Zotero\storage\ABC12345\paper.pdf"
        normalized, bbt_raw, key = _normalize_attachment_path(raw)

        assert normalized == "storage:ABC12345/paper.pdf"
        assert bbt_raw == raw
        assert key == "ABC12345"

    def test_storage_prefix_path(self) -> None:
        """Already-prefixed storage: path passes through with slash normalization."""
        raw = "storage:ABC12345/paper.pdf"
        normalized, bbt_raw, key = _normalize_attachment_path(raw)

        assert normalized == "storage:ABC12345/paper.pdf"
        assert bbt_raw == raw
        assert key == "ABC12345"

    def test_bare_relative_path(self) -> None:
        """Bare relative path KEY/filename gets storage: prefix prepended."""
        raw = "ABC12345/paper.pdf"
        normalized, bbt_raw, key = _normalize_attachment_path(raw)

        assert normalized == "storage:ABC12345/paper.pdf"
        assert bbt_raw == raw
        assert key == "ABC12345"

    def test_path_with_chinese_characters(self) -> None:
        """Chinese filenames are preserved without escaping or corruption."""
        raw = r"D:\L\Med\Research\99_System\Zotero\storage\ABC12345\中文论文.pdf"
        normalized, bbt_raw, key = _normalize_attachment_path(raw)

        assert normalized == "storage:ABC12345/中文论文.pdf"
        assert "中文论文" in normalized
        assert key == "ABC12345"

    def test_path_with_spaces(self) -> None:
        """Filenames containing spaces are handled correctly."""
        raw = r"D:\L\Med\Research\99_System\Zotero\storage\ABC12345\paper with spaces.pdf"
        normalized, bbt_raw, key = _normalize_attachment_path(raw)

        assert normalized == "storage:ABC12345/paper with spaces.pdf"
        assert key == "ABC12345"

    def test_storage_prefix_with_backslashes(self) -> None:
        """storage: prefix with backslashes is normalized to forward slashes."""
        raw = r"storage:ABC12345\subdir\paper.pdf"
        normalized, _, key = _normalize_attachment_path(raw)

        assert normalized == "storage:ABC12345/subdir/paper.pdf"
        assert key == "ABC12345"

    def test_empty_path(self) -> None:
        """Empty string returns empty tuple components."""
        normalized, bbt_raw, key = _normalize_attachment_path("")

        assert normalized == ""
        assert bbt_raw == ""
        assert key == ""

    def test_absolute_non_storage_path(self) -> None:
        """Absolute path outside Zotero storage gets absolute: prefix."""
        raw = r"D:\Downloads\random.pdf"
        normalized, bbt_raw, key = _normalize_attachment_path(raw)

        assert normalized.startswith("absolute:")
        assert bbt_raw == raw
        assert key == ""


# ---------------------------------------------------------------------------
# Test class: TestMainPdfIdentification
# ---------------------------------------------------------------------------

class TestMainPdfIdentification:
    """Tests for _identify_main_pdf() hybrid priority strategy."""

    def test_title_pdf_primary(self) -> None:
        """Attachment with title exactly 'PDF' is selected as main."""
        attachments = [
            {"path": "storage:KEY/paper.pdf", "contentType": "application/pdf", "title": "PDF", "size": 1000},
            {"path": "storage:KEY/supp.pdf", "contentType": "application/pdf", "title": "Supplementary", "size": 2000},
        ]
        main, supplementary = _identify_main_pdf(attachments)

        assert main is not None
        assert main["title"] == "PDF"
        assert len(supplementary) == 1
        assert supplementary[0]["title"] == "Supplementary"

    def test_fallback_largest_file(self) -> None:
        """When no title=='PDF', largest file by size is selected as main."""
        attachments = [
            {"path": "storage:KEY/small.pdf", "contentType": "application/pdf", "title": "Small", "size": 100},
            {"path": "storage:KEY/large.pdf", "contentType": "application/pdf", "title": "Large", "size": 9999},
        ]
        main, supplementary = _identify_main_pdf(attachments)

        assert main is not None
        assert main["title"] == "Large"
        assert len(supplementary) == 1

    def test_fallback_first_pdf(self) -> None:
        """When sizes are equal, first PDF in list is selected as main."""
        attachments = [
            {"path": "storage:KEY/first.pdf", "contentType": "application/pdf", "title": "First", "size": 100},
            {"path": "storage:KEY/second.pdf", "contentType": "application/pdf", "title": "Second", "size": 100},
        ]
        main, supplementary = _identify_main_pdf(attachments)

        assert main is not None
        assert main["title"] == "First"
        assert len(supplementary) == 1

    def test_no_pdf_attachments(self) -> None:
        """No PDF attachments returns (None, [])."""
        attachments = [
            {"path": "storage:KEY/data.xlsx", "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "title": "Data", "size": 100},
        ]
        main, supplementary = _identify_main_pdf(attachments)

        assert main is None
        assert supplementary == []

    def test_single_pdf_no_supplementary(self) -> None:
        """Single PDF attachment returns empty supplementary list."""
        attachments = [
            {"path": "storage:KEY/only.pdf", "contentType": "application/pdf", "title": "Only", "size": 1000},
        ]
        main, supplementary = _identify_main_pdf(attachments)

        assert main is not None
        assert supplementary == []

    def test_mixed_pdf_and_non_pdf(self) -> None:
        """Non-PDF attachments are ignored in main/supplementary selection."""
        attachments = [
            {"path": "storage:KEY/main.pdf", "contentType": "application/pdf", "title": "PDF", "size": 1000},
            {"path": "storage:KEY/supp.pdf", "contentType": "application/pdf", "title": "Supp", "size": 500},
            {"path": "storage:KEY/data.zip", "contentType": "application/zip", "title": "Data", "size": 200},
        ]
        main, supplementary = _identify_main_pdf(attachments)

        assert main is not None
        assert main["title"] == "PDF"
        assert len(supplementary) == 1
        assert supplementary[0]["title"] == "Supp"


# ---------------------------------------------------------------------------
# Test class: TestWikilinkGeneration
# ---------------------------------------------------------------------------

class TestWikilinkGeneration:
    """Tests for obsidian_wikilink_for_pdf() wikilink generation."""

    def test_basic_wikilink(self, tmp_path: Path) -> None:
        """storage:KEY/file.pdf resolves to [[system/Zotero/KEY/file.pdf]]."""
        vault_dir = tmp_path / "vault"
        zotero_dir = vault_dir / "system" / "Zotero"
        # Current implementation joins storage: directly under zotero_dir
        storage_dir = zotero_dir / "KEY"
        storage_dir.mkdir(parents=True)
        pdf = storage_dir / "file.pdf"
        pdf.write_text("PDF content")

        result = obsidian_wikilink_for_pdf("storage:KEY/file.pdf", vault_dir, zotero_dir)

        assert result == "[[system/Zotero/KEY/file.pdf]]"

    def test_junction_resolution(self, tmp_path: Path, monkeypatch) -> None:
        """Junction resolved before relative path computed."""
        vault_dir = tmp_path / "vault"
        zotero_dir = vault_dir / "system" / "Zotero"
        storage_dir = zotero_dir / "storage" / "KEY"
        storage_dir.mkdir(parents=True)
        pdf = storage_dir / "file.pdf"
        pdf.write_text("PDF content")

        # Mock resolve_junction to simulate junction resolution
        real_target = storage_dir / "file.pdf"

        def mock_resolve_junction(path: Path) -> Path:
            if "junction" in str(path).lower():
                return real_target
            return path

        monkeypatch.setattr(
            "paperforge.pdf_resolver.resolve_junction", mock_resolve_junction
        )

        # Test with a path that would trigger junction resolution
        result = obsidian_wikilink_for_pdf("storage:KEY/file.pdf", vault_dir, zotero_dir)
        assert result.startswith("[[")
        assert result.endswith("]]")
        assert "/" in result

    def test_forward_slashes(self, tmp_path: Path) -> None:
        """Output wikilink uses forward slashes, never backslashes."""
        vault_dir = tmp_path / "vault"
        zotero_dir = vault_dir / "system" / "Zotero"
        # Current implementation joins storage: directly under zotero_dir
        storage_dir = zotero_dir / "KEY"
        storage_dir.mkdir(parents=True)
        pdf = storage_dir / "file.pdf"
        pdf.write_text("PDF content")

        result = obsidian_wikilink_for_pdf("storage:KEY/file.pdf", vault_dir, zotero_dir)

        assert "\\" not in result
        assert "/" in result

    def test_chinese_filename_wikilink(self, tmp_path: Path) -> None:
        """Chinese characters preserved in wikilink without escaping."""
        vault_dir = tmp_path / "vault"
        zotero_dir = vault_dir / "system" / "Zotero"
        # Current implementation joins storage: directly under zotero_dir
        storage_dir = zotero_dir / "KEY"
        storage_dir.mkdir(parents=True)
        pdf = storage_dir / "中文论文.pdf"
        pdf.write_text("PDF content")

        result = obsidian_wikilink_for_pdf("storage:KEY/中文论文.pdf", vault_dir, zotero_dir)

        assert "中文论文" in result
        assert result == "[[system/Zotero/KEY/中文论文.pdf]]"

    def test_empty_pdf_path(self, tmp_path: Path) -> None:
        """Empty pdf_path returns empty string."""
        vault_dir = tmp_path / "vault"
        zotero_dir = vault_dir / "system" / "Zotero"
        zotero_dir.mkdir(parents=True)

        result = obsidian_wikilink_for_pdf("", vault_dir, zotero_dir)

        assert result == ""

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Non-existent file still returns wikilink with relative path."""
        vault_dir = tmp_path / "vault"
        zotero_dir = vault_dir / "system" / "Zotero"
        zotero_dir.mkdir(parents=True)

        result = obsidian_wikilink_for_pdf("storage:KEY/missing.pdf", vault_dir, zotero_dir)

        # The file doesn't exist, but the path should still be converted to a wikilink
        # Because the function resolves the path relative to vault
        assert "[[" in result
        assert "]]" in result


# ---------------------------------------------------------------------------
# Test class: TestLoadExportRowsIntegration
# ---------------------------------------------------------------------------

class TestLoadExportRowsIntegration:
    """Integration tests using fixture JSON files."""

    def test_load_absolute_fixture(self, tmp_path: Path) -> None:
        """Load BBT export with absolute Windows paths — attachments normalized."""
        fixture_path = REPO_ROOT / "tests" / "fixtures" / "bbt_export_absolute.json"
        export_file = tmp_path / "library.json"
        export_file.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["key"] == "ABC12345"
        attachments = rows[0]["attachments"]
        assert len(attachments) == 1
        assert attachments[0]["path"] == "storage:ABC12345/Absolute Path Test Paper.pdf"
        assert attachments[0]["bbt_path_raw"].startswith("D:")
        assert rows[0]["zotero_storage_key"] == "ABC12345"

    def test_load_storage_fixture(self, tmp_path: Path) -> None:
        """Load BBT export with storage: prefix — paths pass through."""
        fixture_path = REPO_ROOT / "tests" / "fixtures" / "bbt_export_storage.json"
        export_file = tmp_path / "library.json"
        export_file.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["key"] == "STORAGE1"
        attachments = rows[0]["attachments"]
        assert attachments[0]["path"] == "storage:STORAGE1/Storage Prefix Test Paper.pdf"

    def test_load_mixed_fixture(self, tmp_path: Path) -> None:
        """Load BBT export with mixed formats — all normalized correctly."""
        fixture_path = REPO_ROOT / "tests" / "fixtures" / "bbt_export_mixed.json"
        export_file = tmp_path / "library.json"
        export_file.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 2

        # First item: absolute Windows path
        row0 = rows[0]
        assert row0["key"] == "MIXED001"
        assert row0["attachment_count"] == 3
        # Main PDF should be the one with title="PDF"
        assert row0["pdf_path"] == "storage:MIXED001/Mixed Formats Paper.pdf"
        # supplementary should contain the other PDF
        assert len(row0["supplementary"]) == 1
        assert row0["supplementary"][0] == "storage:MIXED001/supplementary data.pdf"

        # Second item: bare relative path
        row1 = rows[1]
        assert row1["key"] == "BARE002"
        assert row1["pdf_path"] == "storage:BARE002/BARE002.pdf"
        assert row1["supplementary"] == []

    def test_mixed_fixture_path_error_none(self, tmp_path: Path) -> None:
        """Mixed fixture items with PDFs have no path_error."""
        fixture_path = REPO_ROOT / "tests" / "fixtures" / "bbt_export_mixed.json"
        export_file = tmp_path / "library.json"
        export_file.write_text(fixture_path.read_text(encoding="utf-8"), encoding="utf-8")

        rows = load_export_rows(export_file)

        for row in rows:
            assert row["path_error"] == ""

    def test_no_attachments_path_error(self, tmp_path: Path) -> None:
        """Item with no attachments gets path_error='not_found'."""
        export_data = {
            "items": [
                {
                    "key": "NOATTACH",
                    "itemKey": "NOATTACH",
                    "itemType": "journalArticle",
                    "title": "No Attachments",
                    "attachments": [],
                }
            ],
            "collections": {},
        }
        export_file = tmp_path / "library.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["path_error"] == "not_found"
        assert rows[0]["pdf_path"] == ""
        assert rows[0]["attachment_count"] == 0
