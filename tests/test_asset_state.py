"""Tests for asset_state.py — lifecycle, health, maturity, and next-step derivation.

All four functions are pure — no filesystem access, no vault dependencies.
Test entries are plain dicts matching the canonical index entry shape.
"""

from __future__ import annotations

import pytest

from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_health,
    compute_maturity,
    compute_next_step,
)


class TestComputeLifecycle:
    """compute_lifecycle(entry) -> str"""

    def test_empty_entry_returns_indexed(self) -> None:
        """Empty dict defaults to indexed (has_pdf defaults to False)."""
        result = compute_lifecycle({})
        assert result == "indexed"

    def test_no_pdf_returns_indexed(self) -> None:
        """has_pdf=False always returns indexed regardless of other fields."""
        entry = {
            "has_pdf": False,
            "ocr_status": "done",
            "deep_reading_status": "done",
        }
        result = compute_lifecycle(entry)
        assert result == "indexed"

    def test_pdf_ready(self) -> None:
        """has_pdf=True with ocr_status NOT done → pdf_ready."""
        entry = {
            "has_pdf": True,
            "ocr_status": "pending",
            "deep_reading_status": "pending",
        }
        result = compute_lifecycle(entry)
        assert result == "pdf_ready"

    def test_fulltext_ready(self) -> None:
        """ocr_status='done' with deep_reading NOT done → fulltext_ready."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "pending",
        }
        result = compute_lifecycle(entry)
        assert result == "fulltext_ready"

    def test_deep_read_done_with_missing_ai_path(self) -> None:
        """OCR done AND deep-reading done BUT ai_path is empty → deep_read_done."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "done",
            "ai_path": "",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
        }
        result = compute_lifecycle(entry)
        assert result == "deep_read_done"

    def test_ai_context_ready(self) -> None:
        """All conditions met: OCR done, deep_read done, all workspace paths non-empty."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "done",
            "ai_path": "Literature/骨科/KEY/ai/",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
        }
        result = compute_lifecycle(entry)
        assert result == "ai_context_ready"

    def test_missing_one_workspace_path_returns_deep_read_done(self) -> None:
        """OCR done AND deep_read done but fulltext_path is missing → deep_read_done."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "done",
            "ai_path": "Literature/骨科/KEY/ai/",
            "fulltext_path": "",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
        }
        result = compute_lifecycle(entry)
        assert result == "deep_read_done"

    def test_ocr_done_incomplete_returns_pdf_ready(self) -> None:
        """ocr_status='done_incomplete' does NOT count as done → pdf_ready."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done_incomplete",
            "deep_reading_status": "done",
        }
        result = compute_lifecycle(entry)
        assert result == "pdf_ready"


class TestComputeHealth:
    """compute_health(entry) -> dict[str, str]"""

    def test_empty_entry_all_unhealthy(self) -> None:
        """Empty entry: pdf_health='healthy' (no PDF expected), rest unhealthy."""
        result = compute_health({})
        assert result["pdf_health"] == "healthy"
        assert "OCR pending" in result["ocr_health"]
        assert "Formal note missing" in result["note_health"]
        assert "Missing workspace paths" in result["asset_health"]
        # Verify all four keys exist
        assert set(result.keys()) == {"pdf_health", "ocr_health", "note_health", "asset_health"}

    def test_fully_healthy_entry(self) -> None:
        """Entry with all fields good → all four dimensions report 'healthy'."""
        entry = {
            "has_pdf": True,
            "pdf_path": "[[99_System/Zotero/storage/KEY/file.pdf]]",
            "ocr_status": "done",
            "note_path": "Literature/骨科/KEY - Title.md",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
            "ai_path": "Literature/骨科/KEY/ai/",
        }
        result = compute_health(entry)
        assert result["pdf_health"] == "healthy"
        assert result["ocr_health"] == "healthy"
        assert result["note_health"] == "healthy"
        assert result["asset_health"] == "healthy"

    def test_ocr_failed(self) -> None:
        """ocr_status='failed' → ocr_health contains 'OCR failed'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "failed",
        }
        result = compute_health(entry)
        assert "OCR failed" in result["ocr_health"]

    def test_missing_pdf_path(self) -> None:
        """has_pdf=True but pdf_path='' → pdf_health contains 'PDF path missing'."""
        entry = {
            "has_pdf": True,
            "pdf_path": "",
            "ocr_status": "done",
        }
        result = compute_health(entry)
        assert "PDF path missing" in result["pdf_health"]


class TestComputeMaturity:
    """compute_maturity(entry) -> dict"""

    def test_empty_entry_level_1(self) -> None:
        """Empty entry: level=1, metadata=True, pdf=False, blocking='pdf'."""
        result = compute_maturity({})
        assert result["level"] == 1
        assert result["checks"]["metadata"] is True
        assert result["checks"]["pdf"] is False
        assert result["blocking"] == "pdf"

    def test_pdf_only_level_2(self) -> None:
        """has_pdf=True, ocr pending → level=2, blocking='fulltext'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "pending",
            "deep_reading_status": "pending",
        }
        result = compute_maturity(entry)
        assert result["level"] == 2
        assert result["checks"]["metadata"] is True
        assert result["checks"]["pdf"] is True
        assert result["checks"]["fulltext"] is False
        assert result["blocking"] == "fulltext"

    def test_fulltext_figure_level_4(self) -> None:
        """OCR done, ocr_json_path non-empty, deep_read pending → level=4, blocking='ai'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "ocr_json_path": "99_System/PaperForge/ocr/KEY/result.json",
            "deep_reading_status": "pending",
        }
        result = compute_maturity(entry)
        assert result["level"] == 4
        assert result["checks"]["metadata"] is True
        assert result["checks"]["pdf"] is True
        assert result["checks"]["fulltext"] is True
        assert result["checks"]["figure"] is True
        assert result["checks"]["ai"] is False
        assert result["blocking"] == "ai"

    def test_fully_ready_level_6(self) -> None:
        """All checks pass → level=6, blocking=None."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "ocr_json_path": "99_System/PaperForge/ocr/KEY/result.json",
            "deep_reading_status": "done",
            "ai_path": "Literature/骨科/KEY/ai/",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
        }
        result = compute_maturity(entry)
        assert result["level"] == 6
        assert result["checks"]["metadata"] is True
        assert result["checks"]["pdf"] is True
        assert result["checks"]["fulltext"] is True
        assert result["checks"]["figure"] is True
        assert result["checks"]["ai"] is True
        assert result["checks"]["review"] is True
        assert result["blocking"] is None

    def test_metadata_check_always_true(self) -> None:
        """Empty title/authors still passes metadata check (entry existence is enough)."""
        entry = {
            "title": "",
            "authors": [],
        }
        result = compute_maturity(entry)
        assert result["checks"]["metadata"] is True
        assert result["level"] >= 1

    def test_maturity_calls_lifecycle(self) -> None:
        """compute_maturity delegates to compute_lifecycle internally."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "ocr_json_path": "99_System/PaperForge/ocr/KEY/result.json",
            "deep_reading_status": "done",
            "ai_path": "Literature/骨科/KEY/ai/",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
        }
        result = compute_maturity(entry)
        assert result["checks"]["ai"] is True  # lifecycle is ai_context_ready
        assert result["checks"]["review"] is True


class TestComputeNextStep:
    """compute_next_step(entry) -> str"""

    def test_no_pdf_returns_sync(self) -> None:
        """has_pdf=False → 'sync'."""
        entry = {"has_pdf": False}
        result = compute_next_step(entry)
        assert result == "sync"

    def test_ocr_pending_returns_ocr(self) -> None:
        """has_pdf=True, ocr_status='pending' → 'ocr'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "pending",
        }
        result = compute_next_step(entry)
        assert result == "ocr"

    def test_ocr_failed_returns_ocr(self) -> None:
        """ocr_status='failed' → 'ocr' (retry OCR)."""
        entry = {
            "has_pdf": True,
            "ocr_status": "failed",
        }
        result = compute_next_step(entry)
        assert result == "ocr"

    def test_ocr_processing_returns_ready(self) -> None:
        """ocr_status='processing' → 'ready' (OCR already running)."""
        entry = {
            "has_pdf": True,
            "ocr_status": "processing",
        }
        result = compute_next_step(entry)
        assert result == "ready"

    def test_ready_for_deep_read_returns_pf_deep(self) -> None:
        """OCR done, deep_reading pending → '/pf-deep'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "pending",
        }
        result = compute_next_step(entry)
        assert result == "/pf-deep"

    def test_fully_ready_returns_ready(self) -> None:
        """All done, all paths present → 'ready'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "done",
            "note_path": "Literature/骨科/KEY - Title.md",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
            "ai_path": "Literature/骨科/KEY/ai/",
        }
        result = compute_next_step(entry)
        assert result == "ready"

    def test_missing_note_path_returns_sync(self) -> None:
        """OCR done, deep_read done, but note_path empty → 'sync'."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done",
            "deep_reading_status": "done",
            "note_path": "",
            "fulltext_path": "Literature/骨科/KEY/fulltext.md",
            "deep_reading_path": "Literature/骨科/KEY/deep-reading.md",
            "main_note_path": "Literature/骨科/KEY/KEY - Title.md",
            "ai_path": "Literature/骨科/KEY/ai/",
        }
        result = compute_next_step(entry)
        assert result == "sync"

    def test_ocr_done_incomplete_returns_ocr(self) -> None:
        """ocr_status='done_incomplete' → 'ocr' (retry)."""
        entry = {
            "has_pdf": True,
            "ocr_status": "done_incomplete",
            "deep_reading_status": "done",
        }
        result = compute_next_step(entry)
        assert result == "ocr"
