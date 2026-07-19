from __future__ import annotations


def test_network_error_maps_to_retryable_status() -> None:
    from paperforge.worker.ocr_errors import OCRNetworkError, classify_ocr_error

    result = classify_ocr_error(OCRNetworkError("timeout"), stage="poll")
    assert result["status"] == "retryable_error"
    assert result["retryable"] is True
    assert result["error_type"] == "OCRNetworkError"


def test_postprocess_error_maps_to_fatal_status() -> None:
    from paperforge.worker.ocr_errors import OCRPostprocessError, classify_ocr_error

    result = classify_ocr_error(OCRPostprocessError("bad role graph"), stage="postprocess")
    assert result["status"] == "fatal_error"
    assert result["retryable"] is False
    assert result["error_stage"] == "postprocess"


def test_ocr_queue_statuses_include_error_taxonomy() -> None:
    from paperforge.worker.ocr import OCR_QUEUE_STATUSES

    for status in ["pending", "queued", "running", "done", "done_degraded", "retryable_error", "fatal_error", "nopdf", "blocked"]:
        assert status in OCR_QUEUE_STATUSES


def test_apply_ocr_error_state_updates_queue_and_meta() -> None:
    from paperforge.worker.ocr import apply_ocr_error_state

    row = {"queue_status": "running"}
    meta = {}
    apply_ocr_error_state(row, meta, {"status": "fatal_error", "error_type": "OCRPostprocessError", "error_stage": "postprocess", "retryable": False, "last_error": "bad"})
    assert row["queue_status"] == "fatal_error"
    assert meta["error_type"] == "OCRPostprocessError"


def test_legacy_error_status_maps_to_new_taxonomy_for_readers() -> None:
    from paperforge.worker.ocr_errors import normalize_ocr_status_for_reader

    assert normalize_ocr_status_for_reader("retryable_error") == "error"
    assert normalize_ocr_status_for_reader("fatal_error") == "error"
    assert normalize_ocr_status_for_reader("done_degraded") == "done"


def test_postprocess_failure_does_not_return_to_pending() -> None:
    from paperforge.worker.ocr_errors import OCRPostprocessError, classify_ocr_error

    state = classify_ocr_error(OCRPostprocessError("bad structure"), stage="postprocess")
    assert state["status"] == "fatal_error"
    assert state["retryable"] is False


