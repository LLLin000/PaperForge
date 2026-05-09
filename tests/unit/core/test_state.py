"""Unit tests for paperforge.core.state — state machine enums and transitions."""
from __future__ import annotations

from paperforge.core.state import (
    ALLOWED_TRANSITIONS,
    Lifecycle,
    OcrStatus,
    PdfStatus,
)


class TestOcrStatus:
    """OcrStatus enum values and legacy mapping."""

    def test_values_match_expected_strings(self) -> None:
        assert OcrStatus.PENDING.value == "pending"
        assert OcrStatus.PROCESSING.value == "processing"
        assert OcrStatus.DONE.value == "done"
        assert OcrStatus.FAILED.value == "failed"

    def test_from_legacy_canonical_pending(self) -> None:
        assert OcrStatus.from_legacy("pending") is OcrStatus.PENDING

    def test_from_legacy_canonical_processing(self) -> None:
        assert OcrStatus.from_legacy("processing") is OcrStatus.PROCESSING

    def test_from_legacy_canonical_done(self) -> None:
        assert OcrStatus.from_legacy("done") is OcrStatus.DONE

    def test_from_legacy_canonical_failed(self) -> None:
        assert OcrStatus.from_legacy("failed") is OcrStatus.FAILED

    def test_from_legacy_queued_maps_to_pending(self) -> None:
        assert OcrStatus.from_legacy("queued") is OcrStatus.PENDING

    def test_from_legacy_running_maps_to_processing(self) -> None:
        assert OcrStatus.from_legacy("running") is OcrStatus.PROCESSING

    def test_from_legacy_error_maps_to_failed(self) -> None:
        assert OcrStatus.from_legacy("error") is OcrStatus.FAILED

    def test_from_legacy_blocked_maps_to_failed(self) -> None:
        assert OcrStatus.from_legacy("blocked") is OcrStatus.FAILED

    def test_from_legacy_nopdf_maps_to_failed(self) -> None:
        assert OcrStatus.from_legacy("nopdf") is OcrStatus.FAILED

    def test_from_legacy_done_incomplete_maps_to_done(self) -> None:
        assert OcrStatus.from_legacy("done_incomplete") is OcrStatus.DONE

    def test_from_legacy_unknown_maps_to_pending(self) -> None:
        assert OcrStatus.from_legacy("nonexistent") is OcrStatus.PENDING

    def test_from_legacy_case_and_whitespace_insensitive(self) -> None:
        assert OcrStatus.from_legacy("  DONE  ") is OcrStatus.DONE
        assert OcrStatus.from_legacy("Queued") is OcrStatus.PENDING

    def test_str_returns_value(self) -> None:
        assert str(OcrStatus.PENDING) == "pending"
        assert str(OcrStatus.DONE) == "done"


class TestPdfStatus:
    """PdfStatus enum values."""

    def test_values_match_expected_strings(self) -> None:
        assert PdfStatus.HEALTHY.value == "healthy"
        assert PdfStatus.BROKEN.value == "broken"
        assert PdfStatus.MISSING.value == "missing"

    def test_str_returns_value(self) -> None:
        assert str(PdfStatus.HEALTHY) == "healthy"
        assert str(PdfStatus.BROKEN) == "broken"
        assert str(PdfStatus.MISSING) == "missing"


class TestLifecycle:
    """Lifecycle enum values."""

    def test_values_match_expected_strings(self) -> None:
        assert Lifecycle.PDF_READY.value == "pdf_ready"
        assert Lifecycle.OCR_READY.value == "ocr_ready"
        assert Lifecycle.ANALYZE_READY.value == "analyze_ready"
        assert Lifecycle.DEEP_READ_DONE.value == "deep_read_done"
        assert Lifecycle.ERROR_STATE.value == "error_state"

    def test_str_returns_value(self) -> None:
        assert str(Lifecycle.PDF_READY) == "pdf_ready"

    def test_enum_equals_string_value(self) -> None:
        """str enum members compare equal to their string value for backward compat."""
        assert Lifecycle.PDF_READY == "pdf_ready"
        assert Lifecycle.DEEP_READ_DONE == "deep_read_done"


class TestAllowedTransitionsOcr:
    """ALLOWED_TRANSITIONS.check_ocr validation."""

    def test_pending_to_processing_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.PENDING, OcrStatus.PROCESSING)
        assert ok is True
        assert msg == ""

    def test_pending_to_failed_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.PENDING, OcrStatus.FAILED)
        assert ok is True
        assert msg == ""

    def test_processing_to_done_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.PROCESSING, OcrStatus.DONE)
        assert ok is True
        assert msg == ""

    def test_processing_to_failed_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.PROCESSING, OcrStatus.FAILED)
        assert ok is True
        assert msg == ""

    def test_done_to_pending_valid_rerun(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.DONE, OcrStatus.PENDING)
        assert ok is True
        assert msg == ""

    def test_failed_to_pending_valid_retry(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.FAILED, OcrStatus.PENDING)
        assert ok is True
        assert msg == ""

    def test_pending_to_done_invalid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.PENDING, OcrStatus.DONE)
        assert ok is False
        assert "Illegal OCR transition" in msg

    def test_done_to_processing_invalid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.DONE, OcrStatus.PROCESSING)
        assert ok is False
        assert "Illegal OCR transition" in msg

    def test_failed_to_done_invalid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.FAILED, OcrStatus.DONE)
        assert ok is False
        assert "Illegal OCR transition" in msg

    def test_invalid_transition_includes_allowed_list(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_ocr(OcrStatus.PENDING, OcrStatus.DONE)
        assert ok is False
        assert "processing" in msg
        assert "failed" in msg


class TestAllowedTransitionsLifecycle:
    """ALLOWED_TRANSITIONS.check_lifecycle validation."""

    def test_pdf_ready_to_ocr_ready_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.PDF_READY, Lifecycle.OCR_READY
        )
        assert ok is True
        assert msg == ""

    def test_pdf_ready_to_error_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.PDF_READY, Lifecycle.ERROR_STATE
        )
        assert ok is True
        assert msg == ""

    def test_ocr_ready_to_analyze_ready_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.OCR_READY, Lifecycle.ANALYZE_READY
        )
        assert ok is True
        assert msg == ""

    def test_analyze_ready_to_deep_read_done_valid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.ANALYZE_READY, Lifecycle.DEEP_READ_DONE
        )
        assert ok is True
        assert msg == ""

    def test_deep_read_done_to_pdf_ready_valid_rerun(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.DEEP_READ_DONE, Lifecycle.PDF_READY
        )
        assert ok is True
        assert msg == ""

    def test_error_state_to_pdf_ready_valid_recover(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.ERROR_STATE, Lifecycle.PDF_READY
        )
        assert ok is True
        assert msg == ""

    def test_pdf_ready_to_deep_read_done_invalid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.PDF_READY, Lifecycle.DEEP_READ_DONE
        )
        assert ok is False
        assert "Illegal lifecycle transition" in msg

    def test_ocr_ready_to_deep_read_done_invalid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.OCR_READY, Lifecycle.DEEP_READ_DONE
        )
        assert ok is False
        assert "Illegal lifecycle transition" in msg

    def test_deep_read_done_to_analyze_ready_invalid(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.DEEP_READ_DONE, Lifecycle.ANALYZE_READY
        )
        assert ok is False
        assert "Illegal lifecycle transition" in msg

    def test_invalid_transition_includes_allowed_list(self) -> None:
        ok, msg = ALLOWED_TRANSITIONS.check_lifecycle(
            Lifecycle.PDF_READY, Lifecycle.DEEP_READ_DONE
        )
        assert ok is False
        assert "ocr_ready" in msg
        assert "error_state" in msg
