"""Tests for OCR state in canonical index entries.

Verifies that build_index() produces correct OCR status and workflow fields
in canonical index entries for papers with/without PDFs.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


class TestCanonicalIndexOcrState:
    """Tests for OCR state reporting in canonical index."""

    def _make_vault(self, tmp_path: Path) -> Path:
        """Create a minimal vault structure."""
        vault = tmp_path / "vault"
        vault.mkdir()
        system = vault / "99_System"
        system.mkdir()
        exports = system / "PaperForge" / "exports"
        exports.mkdir(parents=True)
        (exports / "test.json").write_text("[]", encoding="utf-8")
        (system / "PaperForge" / "ocr").mkdir(parents=True)
        (system / "PaperForge" / "indexes").mkdir(parents=True)
        resources = vault / "03_Resources"
        resources.mkdir()
        (resources / "Literature").mkdir(parents=True)
        (vault / "paperforge.json").write_text(
            json.dumps({
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                    "base_dir": "05_Bases",
                }
            }),
            encoding="utf-8",
        )
        return vault

    def _mock_export_item(self, key: str, has_pdf: bool = True, pdf_path: str = "") -> dict:
        """Build a mock export item dict."""
        attachments = []
        if has_pdf and pdf_path:
            attachments.append({"contentType": "application/pdf", "path": pdf_path})
        return {
            "key": key,
            "title": "Test Paper",
            "year": 2024,
            "doi": "10.1234/test",
            "attachments": attachments,
            "collections": [],
            "creators": [],
            "publicationTitle": "",
            "journal": "Test Journal",
            "extra": "",
            "authors": ["Smith J"],
        }

    def _base_mock_paths(self, vault: Path) -> dict:
        return {
            "exports": vault / "99_System" / "PaperForge" / "exports",
            "ocr": vault / "99_System" / "PaperForge" / "ocr",
            "literature": vault / "03_Resources" / "Literature",
            "index": vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json",
            "bases": vault / "05_Bases",
            "library_records": vault / "03_Resources" / "LiteratureControl" / "library-records",
        }

    def test_no_pdf_sets_pending_ocr(self, tmp_path: Path) -> None:
        """Export item with no PDF → ocr_status stays pending."""
        vault = self._make_vault(tmp_path)
        with (
            patch("paperforge.worker._utils.pipeline_paths") as mock_paths,
            patch("paperforge.worker.sync.load_domain_config") as mock_domain,
            patch("paperforge.worker.sync.load_export_rows") as mock_export,
            patch("paperforge.worker.asset_index.migrate_legacy_index", return_value=0),
        ):
            mock_export.return_value = [self._mock_export_item("NO_PDF", has_pdf=False)]
            mock_paths.return_value = self._base_mock_paths(vault)
            mock_domain.return_value = {"domains": [{"export_file": "test.json", "domain": "TestDomain"}]}
            from paperforge.worker.asset_index import build_index
            build_index(vault)

        index_path = vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((e for e in index.get("items", []) if e.get("zotero_key") == "NO_PDF"), None)
        assert entry is not None, "NO_PDF should be in canonical index"
        assert entry["has_pdf"] is False
        assert entry["do_ocr"] is False  # no PDF → no OCR needed
        assert entry["ocr_status"] == "pending"

    def test_pdf_without_ocr_meta_sets_pending(self, tmp_path: Path) -> None:
        """Export item with PDF but no OCR meta → ocr_status: pending."""
        vault = self._make_vault(tmp_path)
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        with (
            patch("paperforge.worker._utils.pipeline_paths") as mock_paths,
            patch("paperforge.worker.sync.load_domain_config") as mock_domain,
            patch("paperforge.worker.sync.load_export_rows") as mock_export,
            patch("paperforge.worker.asset_index.migrate_legacy_index", return_value=0),
        ):
            mock_export.return_value = [self._mock_export_item("VALID", has_pdf=True, pdf_path=str(pdf))]
            mock_paths.return_value = self._base_mock_paths(vault)
            mock_domain.return_value = {"domains": [{"export_file": "test.json", "domain": "TestDomain"}]}
            from paperforge.worker.asset_index import build_index
            build_index(vault)

        index_path = vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((e for e in index.get("items", []) if e.get("zotero_key") == "VALID"), None)
        assert entry is not None, "VALID should be in canonical index"
        assert entry["has_pdf"] is True
        assert entry["do_ocr"] is False  # do_ocr defaults to False (user-controlled)
        assert entry["ocr_status"] == "pending"

    def test_pdf_with_ocr_done_meta(self, tmp_path: Path) -> None:
        """Export item with PDF and OCR meta.json (ocr_status=done) → index shows done."""
        vault = self._make_vault(tmp_path)
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "OCR_DONE"
        ocr_dir.mkdir(parents=True)
        # Create valid OCR fixture: meta.json, fulltext.md, json/result.json
        (ocr_dir / "fulltext.md").write_text(
            "<!-- page 1 -->\n" + "Abstract content.\n" * 30 + "<!-- page 2 -->\n" + "Methods and results.\n" * 30,
            encoding="utf-8",
        )
        (ocr_dir / "json").mkdir()
        (ocr_dir / "json" / "result.json").write_text(
            json.dumps({"pages": 2, "text": "x" * 1200}),
            encoding="utf-8",
        )
        (ocr_dir / "meta.json").write_text(
            json.dumps({
                "ocr_status": "done",
                "zotero_key": "OCR_DONE",
                "page_count": 2,
                "markdown_path": str(ocr_dir / "fulltext.md"),
            }),
            encoding="utf-8",
        )
        with (
            patch("paperforge.worker._utils.pipeline_paths") as mock_paths,
            patch("paperforge.worker.sync.load_domain_config") as mock_domain,
            patch("paperforge.worker.sync.load_export_rows") as mock_export,
            patch("paperforge.worker.asset_index.migrate_legacy_index", return_value=0),
        ):
            mock_export.return_value = [self._mock_export_item("OCR_DONE", has_pdf=True, pdf_path=str(pdf))]
            mock_paths.return_value = self._base_mock_paths(vault)
            mock_domain.return_value = {"domains": [{"export_file": "test.json", "domain": "TestDomain"}]}
            from paperforge.worker.asset_index import build_index
            build_index(vault)

        index_path = vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((e for e in index.get("items", []) if e.get("zotero_key") == "OCR_DONE"), None)
        assert entry is not None, "OCR_DONE should be in canonical index"
        assert entry["has_pdf"] is True
        assert entry["do_ocr"] is True
        assert entry["ocr_status"] == "done"
