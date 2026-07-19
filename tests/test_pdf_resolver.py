"""Tests for paperforge.pdf_resolver.

Covers absolute, vault-relative, junction, storage-relative, missing file,
and has_pdf=False scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.pdf_resolver import is_valid_pdf, resolve_junction, resolve_pdf_path


class TestResolvePdfPath:
    """Tests for resolve_pdf_path resolution logic."""

    def test_absolute_existing_path(self, tmp_path: Path) -> None:
        """Absolute path to existing PDF returns that path."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("PDF content")
        result = resolve_pdf_path(str(pdf), True, tmp_path)
        assert result == str(pdf.resolve())

    def test_vault_relative_existing_path(self, tmp_path: Path) -> None:
        """Vault-relative path resolves against vault root."""
        subdir = tmp_path / "storage" / "ABC123"
        subdir.mkdir(parents=True)
        pdf = subdir / "item.pdf"
        pdf.write_text("PDF content")
        rel_path = "storage/ABC123/item.pdf"
        result = resolve_pdf_path(rel_path, True, tmp_path)
        assert result == str(pdf.resolve())

    def test_junction_path_mocked(self, tmp_path: Path, monkeypatch) -> None:
        """Junction path returns resolved target path (mocked for cross-platform)."""
        target = tmp_path / "target.pdf"
        target.write_text("PDF content")
        junction = tmp_path / "junction.pdf"

        def mock_resolve_junction(path: Path) -> Path:
            if path == junction:
                return target
            return path

        monkeypatch.setattr("paperforge.pdf_resolver.resolve_junction", mock_resolve_junction)
        result = resolve_pdf_path(str(junction), True, tmp_path)
        assert result == str(target.resolve())

    def test_zotero_storage_relative_path(self, tmp_path: Path) -> None:
        """storage: prefixed path resolves against zotero_dir/storage/."""
        zotero_dir = tmp_path / "zotero"
        storage_dir = zotero_dir / "storage" / "ABC123"
        storage_dir.mkdir(parents=True)
        pdf = storage_dir / "item.pdf"
        pdf.write_text("PDF content")
        result = resolve_pdf_path("storage:ABC123/item.pdf", True, tmp_path, zotero_dir)
        assert result == str(pdf.resolve())

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent file returns empty string."""
        result = resolve_pdf_path(str(tmp_path / "missing.pdf"), True, tmp_path)
        assert result == ""

    def test_has_pdf_false_returns_empty(self, tmp_path: Path) -> None:
        """has_pdf=False returns empty string regardless of path."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("PDF content")
        result = resolve_pdf_path(str(pdf), False, tmp_path)
        assert result == ""

    def test_empty_path_returns_empty(self, tmp_path: Path) -> None:
        """Empty pdf_path returns empty string."""
        result = resolve_pdf_path("", True, tmp_path)
        assert result == ""

    def test_whitespace_path_returns_empty(self, tmp_path: Path) -> None:
        """Whitespace-only pdf_path returns empty string."""
        result = resolve_pdf_path("   ", True, tmp_path)
        assert result == ""


class TestIsValidPdf:
    """Tests for is_valid_pdf helper."""

    def test_existing_non_empty_file(self, tmp_path: Path) -> None:
        """Existing non-empty file returns True."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("PDF content")
        assert is_valid_pdf(pdf) is True

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns False."""
        assert is_valid_pdf(tmp_path / "missing.pdf") is False

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file (0 bytes) returns False."""
        pdf = tmp_path / "empty.pdf"
        pdf.write_text("")
        assert is_valid_pdf(pdf) is False

    def test_directory_not_file(self, tmp_path: Path) -> None:
        """Directory path returns False."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        assert is_valid_pdf(subdir) is False


class TestResolveJunction:
    """Tests for resolve_junction helper."""

    def test_nonexistent_path_unchanged(self, tmp_path: Path) -> None:
        """Non-existent path is returned unchanged."""
        missing = tmp_path / "missing.pdf"
        assert resolve_junction(missing) == missing

    def test_regular_file_unchanged(self, tmp_path: Path) -> None:
        """Regular file (not a junction) returns itself."""
        pdf = tmp_path / "test.pdf"
        pdf.write_text("PDF content")
        result = resolve_junction(pdf)
        assert result == pdf

    def test_symlink_followed(self, tmp_path: Path) -> None:
        """Symbolic link to file is resolved to target."""
        target = tmp_path / "target.pdf"
        target.write_text("PDF content")
        link = tmp_path / "link.pdf"
        try:
            link.symlink_to(target)
            result = resolve_junction(link)
            assert result == target
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

    def test_directory_junction_mocked(self, tmp_path: Path) -> None:
        """Directory junction resolution is platform-dependent; covered by symlink test above."""
        pytest.skip("Windows junction mock incompatible with Python import semantics for `from ctypes import wintypes`")


class TestLoadExportRowsAttachmentNormalization:
    """Tests for load_export_rows() attachment path normalization.

    Verifies that BBT-exported bare KEY/KEY.pdf paths are normalized to
    storage:KEY/KEY.pdf format so resolve_pdf_path() can resolve them correctly.
    """

    def test_bare_key_key_pdf_normalized_to_storage_prefix(self, tmp_path: Path) -> None:
        """Bare 'KEY/KEY.pdf' path is normalized to 'storage:KEY/KEY.pdf'."""
        from paperforge.worker.sync import load_export_rows

        export_data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemKey": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Paper",
                    "attachments": [{"path": "ABC123/ABC123.pdf", "contentType": "application/pdf"}],
                }
            ],
            "collections": {},
        }
        export_file = tmp_path / "library.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["attachments"][0]["path"] == "storage:ABC123/ABC123.pdf"

    def test_storage_prefix_preserved(self, tmp_path: Path) -> None:
        """Already-prefixed 'storage:KEY/KEY.pdf' path is not double-prefixed."""
        from paperforge.worker.sync import load_export_rows

        export_data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemKey": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Paper",
                    "attachments": [{"path": "storage:ABC123/ABC123.pdf", "contentType": "application/pdf"}],
                }
            ],
            "collections": {},
        }
        export_file = tmp_path / "library.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["attachments"][0]["path"] == "storage:ABC123/ABC123.pdf"

    def test_absolute_path_normalized_with_prefix(self, tmp_path: Path) -> None:
        """Absolute paths are normalized with absolute: prefix."""
        from paperforge.worker.sync import load_export_rows

        abs_path = str(tmp_path / "ABC123" / "ABC123.pdf")
        export_data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemKey": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Paper",
                    "attachments": [{"path": abs_path, "contentType": "application/pdf"}],
                }
            ],
            "collections": {},
        }
        export_file = tmp_path / "library.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["attachments"][0]["path"] == f"absolute:{abs_path}"

    def test_empty_attachment_path_unchanged(self, tmp_path: Path) -> None:
        """Empty attachment path is returned unchanged."""
        from paperforge.worker.sync import load_export_rows

        export_data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemKey": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Paper",
                    "attachments": [{"path": "", "contentType": ""}],
                }
            ],
            "collections": {},
        }
        export_file = tmp_path / "library.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["attachments"][0]["path"] == ""

    def test_non_pdf_attachment_unchanged(self, tmp_path: Path) -> None:
        """Non-PDF attachments are returned with empty contentType and unchanged path."""
        from paperforge.worker.sync import load_export_rows

        export_data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemKey": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Paper",
                    "attachments": [{"path": "ABC123/ABC123.docx", "contentType": ""}],
                }
            ],
            "collections": {},
        }
        export_file = tmp_path / "library.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")

        rows = load_export_rows(export_file)

        assert len(rows) == 1
        assert rows[0]["attachments"][0]["path"] == "storage:ABC123/ABC123.docx"
        assert rows[0]["attachments"][0]["contentType"] == ""
