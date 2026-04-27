"""Tests for selection-sync PDF reporting (Plan 02-04).

Verifies that run_selection_sync() sets ocr_status: nopdf when PDFs are missing
and preserves pending/done for valid PDFs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


class TestSelectionSyncPdf:
    """Tests for selection-sync PDF preflight reporting."""

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
        resources = vault / "03_Resources"
        resources.mkdir()
        (resources / "LiteratureControl" / "library-records").mkdir(parents=True)
        (resources / "Literature").mkdir(parents=True)
        (vault / "paperforge.json").write_text("{}", encoding="utf-8")
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
            "extra": "",
        }

    def test_no_pdf_sets_nopdf(self, tmp_path: Path) -> None:
        """Export item with no PDF attachments → ocr_status: nopdf."""
        vault = self._make_vault(tmp_path)

        with patch("paperforge.worker.sync.pipeline_paths") as mock_paths:
            mock_paths.return_value = {
                "exports": vault / "99_System" / "PaperForge" / "exports",
                "ocr": vault / "99_System" / "PaperForge" / "ocr",
                "library_records": vault / "03_Resources" / "LiteratureControl" / "library-records",
                "literature": vault / "03_Resources" / "Literature",
            }
            with (
                patch(
                    "paperforge.worker.sync.load_domain_config",
                    return_value={"domains": [{"export_file": "test.json", "domain": "TestDomain"}]},
                ),
                patch("paperforge.worker.base_views.ensure_base_views"),
                patch(
                    "paperforge.worker.sync.load_export_rows",
                    return_value=[self._mock_export_item("NO_PDF", has_pdf=False)],
                ),
            ):
                from paperforge.worker.sync import (
                    run_selection_sync,
                )

                run_selection_sync(vault)

        record_path = vault / "03_Resources" / "LiteratureControl" / "library-records" / "TestDomain" / "NO_PDF.md"
        assert record_path.exists()
        content = record_path.read_text(encoding="utf-8")
        assert 'ocr_status: "nopdf"' in content
        assert "has_pdf: false" in content

    def test_missing_pdf_sets_nopdf(self, tmp_path: Path) -> None:
        """Export item with PDF path to missing file → ocr_status: nopdf."""
        vault = self._make_vault(tmp_path)
        missing_pdf = str(tmp_path / "missing.pdf")

        with patch("paperforge.worker.sync.pipeline_paths") as mock_paths:
            mock_paths.return_value = {
                "exports": vault / "99_System" / "PaperForge" / "exports",
                "ocr": vault / "99_System" / "PaperForge" / "ocr",
                "library_records": vault / "03_Resources" / "LiteratureControl" / "library-records",
                "literature": vault / "03_Resources" / "Literature",
            }
            with (
                patch(
                    "paperforge.worker.sync.load_domain_config",
                    return_value={"domains": [{"export_file": "test.json", "domain": "TestDomain"}]},
                ),
                patch("paperforge.worker.base_views.ensure_base_views"),
                patch(
                    "paperforge.worker.sync.load_export_rows",
                    return_value=[self._mock_export_item("MISSING", has_pdf=True, pdf_path=missing_pdf)],
                ),
            ):
                from paperforge.worker.sync import (
                    run_selection_sync,
                )

                run_selection_sync(vault)

        record_path = vault / "03_Resources" / "LiteratureControl" / "library-records" / "TestDomain" / "MISSING.md"
        assert record_path.exists()
        content = record_path.read_text(encoding="utf-8")
        assert 'ocr_status: "nopdf"' in content

    def test_valid_pdf_sets_pending(self, tmp_path: Path) -> None:
        """Export item with existing PDF → ocr_status: pending."""
        vault = self._make_vault(tmp_path)
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        with patch("paperforge.worker.sync.pipeline_paths") as mock_paths:
            mock_paths.return_value = {
                "exports": vault / "99_System" / "PaperForge" / "exports",
                "ocr": vault / "99_System" / "PaperForge" / "ocr",
                "library_records": vault / "03_Resources" / "LiteratureControl" / "library-records",
                "literature": vault / "03_Resources" / "Literature",
            }
            with (
                patch(
                    "paperforge.worker.sync.load_domain_config",
                    return_value={"domains": [{"export_file": "test.json", "domain": "TestDomain"}]},
                ),
                patch("paperforge.worker.base_views.ensure_base_views"),
                patch(
                    "paperforge.worker.sync.load_export_rows",
                    return_value=[self._mock_export_item("VALID", has_pdf=True, pdf_path=str(pdf))],
                ),
            ):
                from paperforge.worker.sync import (
                    run_selection_sync,
                )

                run_selection_sync(vault)

        record_path = vault / "03_Resources" / "LiteratureControl" / "library-records" / "TestDomain" / "VALID.md"
        assert record_path.exists()
        content = record_path.read_text(encoding="utf-8")
        assert 'ocr_status: "pending"' in content
        assert "pdf_path:" in content

    def test_existing_record_updated(self, tmp_path: Path) -> None:
        """Existing record with pending gets updated to nopdf when PDF removed."""
        vault = self._make_vault(tmp_path)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "TestDomain"
        records_dir.mkdir(parents=True, exist_ok=True)
        record_path = records_dir / "CHANGED.md"
        record_path.write_text(
            "---\nocr_status: pending\nhas_pdf: true\npdf_path: '[[old.pdf]]'\n---\n",
            encoding="utf-8",
        )

        with patch("paperforge.worker.sync.pipeline_paths") as mock_paths:
            mock_paths.return_value = {
                "exports": vault / "99_System" / "PaperForge" / "exports",
                "ocr": vault / "99_System" / "PaperForge" / "ocr",
                "library_records": vault / "03_Resources" / "LiteratureControl" / "library-records",
                "literature": vault / "03_Resources" / "Literature",
            }
            with (
                patch(
                    "paperforge.worker.sync.load_domain_config",
                    return_value={"domains": [{"export_file": "test.json", "domain": "TestDomain"}]},
                ),
                patch("paperforge.worker.base_views.ensure_base_views"),
                patch(
                    "paperforge.worker.sync.load_export_rows",
                    return_value=[self._mock_export_item("CHANGED", has_pdf=False)],
                ),
            ):
                from paperforge.worker.sync import (
                    run_selection_sync,
                )

                run_selection_sync(vault)

        content = record_path.read_text(encoding="utf-8")
        assert 'ocr_status: "nopdf"' in content
        assert "has_pdf: false" in content
