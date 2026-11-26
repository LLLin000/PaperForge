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


def test_truncated_ndjson_ocr_result_marked_recoverable(tmp_path, monkeypatch) -> None:
    """PF-OCR-009: truncated HTTP NDJSON result keeps job retryable in queued/result_unavailable, not fatal_error."""
    import json
    from paperforge.worker import ocr as worker_ocr
    from tests.conftest import canonical_test_config

    vault = tmp_path / "vault_trunc"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    (vault / "a.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    exports_dir = vault / ".paperforge" / "exports"
    exports_dir.mkdir(parents=True)
    (exports_dir / "library.json").write_text(
        json.dumps([{"key": "TRUNC01", "citation-key": "TRUNC01", "title": "Truncated Paper", "attachments": [{"path": str(vault / "a.pdf"), "contentType": "application/pdf"}]}]),
        encoding="utf-8",
    )
    paper_dir = vault / ".paperforge" / "ocr" / "TRUNC01"
    paper_dir.mkdir(parents=True)
    meta_file = paper_dir / "meta.json"
    meta_file.write_text(
        json.dumps({"zotero_key": "TRUNC01", "ocr_status": "pending", "source_pdf": str(vault / "a.pdf")}),
        encoding="utf-8",
    )

    class _FakeResp:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data
            self.text = text

        def raise_for_status(self):
            return None

        def json(self):
            return self._json

    def fake_post(*a, **k):
        return _FakeResp(json_data={"data": {"jobId": "job-123"}})

    def fake_get(url, *a, **k):
        if "job-123" in url:
            return _FakeResp(
                json_data={"data": {"state": "done", "resultUrl": {"jsonUrl": "https://mock.local/result.jsonl"}}}
            )
        return _FakeResp(text='{"result": {"layoutParsingResults": [{"prunedResult": {"width": 1190')

    monkeypatch.setattr(worker_ocr, "_resolve_paddleocr_token", lambda v: "tok")
    monkeypatch.setattr(worker_ocr.requests, "post", fake_post)
    monkeypatch.setattr(worker_ocr.requests, "get", fake_get)
    monkeypatch.setattr(worker_ocr, "load_control_actions", lambda p: {"TRUNC01": {"do_ocr": True}})
    monkeypatch.setattr("time.sleep", lambda *_: None)

    sink: dict = {}
    rc = worker_ocr.run_ocr(vault, selected_keys={"TRUNC01"}, no_progress=True, result_sink=sink)
    assert rc == 1
    saved = json.loads(meta_file.read_text(encoding="utf-8"))
    assert saved["ocr_status"] == "retryable_error"
    assert saved["retryable"] is True
    assert saved["error_stage"] == "result"
    assert saved["error_type"] == "OCRAPISchemaError"
    assert saved["ocr_job_id"] == "job-123"


def test_unmatched_ocr_rebuild_emits_pferror_without_attribute_error(tmp_path, capsys) -> None:
    """PF-OCR-006 / PF-UX-003: _run_ocr_rebuild unmatched explicit key emits PFError cleanly."""
    from paperforge.commands.ocr import _run_ocr_rebuild
    from tests.conftest import canonical_test_config

    vault = tmp_path / "vault_reb"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    rc = _run_ocr_rebuild(vault, keys=["NOPE01"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "No papers matched for rebuild" in out


