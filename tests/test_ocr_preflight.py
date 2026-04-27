"""Tests for OCR preflight in run_ocr().

Verifies that missing PDFs are caught before API submission and produce
ocr_status: nopdf.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestOcrPreflight:
    """Tests for PDF preflight behavior in run_ocr()."""

    def _make_vault(self, tmp_path: Path) -> Path:
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "paperforge.json").write_text("{}", encoding="utf-8")
        return vault

    def _mock_paths(self, vault: Path) -> dict:
        return {
            "exports": vault / "exports",
            "ocr": vault / "ocr",
            "ocr_queue": vault / "ocr_queue.json",
            "library_records": vault / "library-records",
            "literature": vault / "literature",
        }

    def test_has_pdf_false_sets_nopdf(self, tmp_path: Path) -> None:
        """has_pdf=False -> ocr_status: nopdf, no API call."""
        vault = self._make_vault(tmp_path)
        mock_paths = self._mock_paths(vault)
        mock_paths["exports"].mkdir()
        mock_paths["ocr"].mkdir()

        with (
            patch(
                "paperforge.worker.ocr.pipeline_paths",
                return_value=mock_paths,
            ),
            patch(
                "paperforge.worker.ocr.load_control_actions",
                return_value={"ABC123": {"do_ocr": True}},
            ),
            patch(
                "paperforge.worker.ocr.load_export_rows",
                return_value=[
                    {
                        "key": "ABC123",
                        "attachments": [],
                        "title": "No PDF Paper",
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.sync_ocr_queue",
                return_value=[
                    {
                        "zotero_key": "ABC123",
                        "has_pdf": False,
                        "pdf_path": "",
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.ensure_ocr_meta",
                return_value={},
            ),
            patch("paperforge.worker.ocr.write_json") as mock_write,
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
        ):
            from paperforge.worker.ocr import (
                run_ocr,
            )

            run_ocr(vault)

        calls = mock_write.call_args_list
        assert any(call[0][1].get("ocr_status") == "nopdf" for call in calls if isinstance(call[0][1], dict))

    def test_missing_pdf_file_sets_nopdf(self, tmp_path: Path) -> None:
        """has_pdf=True but file missing -> ocr_status: nopdf."""
        vault = self._make_vault(tmp_path)
        mock_paths = self._mock_paths(vault)
        mock_paths["exports"].mkdir()
        mock_paths["ocr"].mkdir()

        with (
            patch(
                "paperforge.worker.ocr.pipeline_paths",
                return_value=mock_paths,
            ),
            patch(
                "paperforge.worker.ocr.load_control_actions",
                return_value={"ABC123": {"do_ocr": True}},
            ),
            patch(
                "paperforge.worker.ocr.load_export_rows",
                return_value=[
                    {
                        "key": "ABC123",
                        "attachments": [
                            {
                                "contentType": "application/pdf",
                                "path": str(tmp_path / "nonexistent.pdf"),
                            }
                        ],
                        "title": "Missing PDF Paper",
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.sync_ocr_queue",
                return_value=[
                    {
                        "zotero_key": "ABC123",
                        "has_pdf": True,
                        "pdf_path": str(tmp_path / "nonexistent.pdf"),
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.ensure_ocr_meta",
                return_value={},
            ),
            patch("paperforge.worker.ocr.write_json") as mock_write,
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
        ):
            from paperforge.worker.ocr import (
                run_ocr,
            )

            run_ocr(vault)

        calls = mock_write.call_args_list
        assert any(call[0][1].get("ocr_status") == "nopdf" for call in calls if isinstance(call[0][1], dict))

    def test_valid_pdf_proceeds(self, tmp_path: Path) -> None:
        """Valid resolved PDF -> proceeds to API submission with resolved path."""
        vault = self._make_vault(tmp_path)
        pdf = tmp_path / "test.pdf"
        pdf.write_text("PDF content")
        mock_paths = self._mock_paths(vault)
        mock_paths["exports"].mkdir()
        mock_paths["ocr"].mkdir()

        with (
            patch(
                "paperforge.worker.ocr.pipeline_paths",
                return_value=mock_paths,
            ),
            patch(
                "paperforge.worker.ocr.load_control_actions",
                return_value={"ABC123": {"do_ocr": True}},
            ),
            patch(
                "paperforge.worker.ocr.load_export_rows",
                return_value=[
                    {
                        "key": "ABC123",
                        "attachments": [
                            {
                                "contentType": "application/pdf",
                                "path": str(pdf),
                            }
                        ],
                        "title": "Valid PDF Paper",
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.sync_ocr_queue",
                return_value=[
                    {
                        "zotero_key": "ABC123",
                        "has_pdf": True,
                        "pdf_path": str(pdf),
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.ensure_ocr_meta",
                return_value={},
            ),
            patch("paperforge.worker.ocr.write_json"),
            patch("builtins.open") as mock_open,
            patch("paperforge.worker.ocr.requests.post") as mock_post,
            patch("paperforge.worker.ocr.requests.get") as mock_get,
        ):
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {"data": {"jobId": "123"}}
            mock_post.return_value.raise_for_status = lambda: None
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.return_value = {"data": {"state": "done", "resultUrl": {"jsonUrl": ""}}}
            mock_get.return_value.raise_for_status = lambda: None
            with patch("paperforge.worker.sync.run_selection_sync"), patch("paperforge.worker.sync.run_index_refresh"):
                from paperforge.worker.ocr import (
                    run_ocr,
                )

                run_ocr(vault)

        mock_open.assert_called_once()
        opened_path = mock_open.call_args[0][0]
        assert Path(opened_path).resolve() == pdf.resolve()

    def test_junction_path_resolved(self, tmp_path: Path) -> None:
        """Junction path is resolved before open() call."""
        vault = self._make_vault(tmp_path)
        target = tmp_path / "target.pdf"
        target.write_text("PDF content")
        mock_paths = self._mock_paths(vault)
        mock_paths["exports"].mkdir()
        mock_paths["ocr"].mkdir()

        with (
            patch(
                "paperforge.pdf_resolver.resolve_pdf_path",
                return_value=str(target),
            ),
            patch(
                "paperforge.worker.ocr.pipeline_paths",
                return_value=mock_paths,
            ),
            patch(
                "paperforge.worker.ocr.load_control_actions",
                return_value={"ABC123": {"do_ocr": True}},
            ),
            patch(
                "paperforge.worker.ocr.load_export_rows",
                return_value=[
                    {
                        "key": "ABC123",
                        "attachments": [
                            {
                                "contentType": "application/pdf",
                                "path": str(tmp_path / "junction.pdf"),
                            }
                        ],
                        "title": "Junction PDF Paper",
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.sync_ocr_queue",
                return_value=[
                    {
                        "zotero_key": "ABC123",
                        "has_pdf": True,
                        "pdf_path": str(tmp_path / "junction.pdf"),
                    }
                ],
            ),
            patch(
                "paperforge.worker.ocr.ensure_ocr_meta",
                return_value={},
            ),
            patch("paperforge.worker.ocr.write_json"),
            patch("builtins.open") as mock_open,
            patch("paperforge.worker.ocr.requests.post") as mock_post,
            patch("paperforge.worker.ocr.requests.get") as mock_get,
        ):
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {"data": {"jobId": "123"}}
            mock_post.return_value.raise_for_status = lambda: None
            mock_get.return_value = MagicMock()
            mock_get.return_value.json.return_value = {"data": {"state": "done", "resultUrl": {"jsonUrl": ""}}}
            mock_get.return_value.raise_for_status = lambda: None
            with patch("paperforge.worker.sync.run_selection_sync"), patch("paperforge.worker.sync.run_index_refresh"):
                from paperforge.worker.ocr import (
                    run_ocr,
                )

                run_ocr(vault)

        mock_open.assert_called_once()
        opened_path = mock_open.call_args[0][0]
        assert Path(opened_path).resolve() == target.resolve()
