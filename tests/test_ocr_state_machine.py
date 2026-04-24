"""Tests for OCR job state transitions in run_ocr().

Covers: pending -> queued/running -> done/error/blocked transitions,
sync_ocr_queue state reconciliation, and cleanup_blocked_ocr_dirs behavior.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


def _make_vault(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create a minimal vault with all required directories."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text("{}", encoding="utf-8")
    ocr_root = vault / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    exports = vault / "PaperForge" / "exports"
    exports.mkdir(parents=True)
    library_records = vault / "Resources" / "Control" / "library-records"
    library_records.mkdir(parents=True)
    literature = vault / "Resources" / "Literature"
    literature.mkdir(parents=True)
    return vault, ocr_root, exports, library_records


def _mock_paths(vault: Path, ocr_root: Path, exports: Path, library_records: Path) -> dict:
    """Build a mock paths dict matching pipeline_paths output."""
    return {
        "vault": vault,
        "ocr": ocr_root,
        "exports": exports,
        "library_records": library_records,
        "literature": vault / "Resources" / "Literature",
        "control": vault / "Resources" / "Control",
        "resources": vault / "Resources",
        "paperforge": vault / "PaperForge",
        "ocr_queue": ocr_root / "ocr-queue.json",
        "bases": vault / "bases",
    }


# ---------------------------------------------------------------------------
# Tests for pending -> queued transition
# ---------------------------------------------------------------------------

class TestPendingToQueuedTransition:
    """Job moves from pending to queued when submitted to the API."""

    def test_pending_job_is_submitted_and_marked_queued(self, tmp_path: Path) -> None:
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY1"
        meta_path = ocr_root / key / "meta.json"
        meta_path.parent.mkdir()
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "pending",
        }), encoding="utf-8")

        lr_dir = library_records / "骨科"
        lr_dir.mkdir(parents=True)
        (lr_dir / f"{key}.md").write_text("""---
zotero_key: TESTKEY1
analyze: false
do_ocr: true
---
# Test""", encoding="utf-8")

        (exports / "骨科.json").write_text(json.dumps([
            {"key": key, "title": "Test Paper", "attachments": [
                {"contentType": "application/pdf", "path": "test.pdf"}
            ]}
        ]), encoding="utf-8")

        # Real PDF file so resolve_pdf_path succeeds
        real_pdf = vault / "test.pdf"
        real_pdf.write_text("PDF content")

        mock_post = MagicMock()
        mock_post.return_value.json.return_value = {"data": {"jobId": "job-123"}}
        mock_post.return_value.raise_for_status = MagicMock()

        with patch("paperforge.worker.ocr.pipeline_paths", return_value=paths):
            with patch("paperforge.worker.ocr.load_control_actions", return_value={key: {"do_ocr": True}}):
                with patch("paperforge.worker.ocr.load_export_rows", return_value=[
                    {"key": key, "attachments": [{"contentType": "application/pdf", "path": "test.pdf"}], "title": "Test"}
                ]):
                    with patch("paperforge.worker.ocr.sync_ocr_queue", return_value=[
                        {"zotero_key": key, "has_pdf": True, "pdf_path": "test.pdf", "queue_status": "pending"}
                    ]):
                        with patch("paperforge.worker.ocr.ensure_ocr_meta", return_value={"zotero_key": key, "ocr_status": "pending"}):
                            with patch("paperforge.worker.ocr.write_json") as mock_write:
                                with patch("paperforge.worker.ocr.requests.post", mock_post):
                                    with patch("paperforge.worker.sync.run_selection_sync"):
                                        with patch("paperforge.worker.sync.run_index_refresh"):
                                            from paperforge.worker.ocr import run_ocr
                                            run_ocr(vault)

        # Check requests.post was called (job submitted)
        assert mock_post.called, "requests.post was not called - job not submitted"

        # Check meta was updated to queued
        meta_calls = [c for c in mock_write.call_args_list
                      if isinstance(c[0][1], dict) and c[0][1].get("zotero_key") == key]
        assert meta_calls, f"No meta write found for key {key}"
        final_meta = meta_calls[-1][0][1]
        assert final_meta.get("ocr_status") == "queued", \
            f"Expected 'queued', got {final_meta.get('ocr_status')}"
        assert final_meta.get("ocr_job_id") == "job-123"


# ---------------------------------------------------------------------------
# Tests for processing -> done transition
# ---------------------------------------------------------------------------

class TestProcessingToDoneTransition:
    """Job moves from running/queued to done when polling returns success."""

    def test_polling_done_transitions_to_done(self, tmp_path: Path) -> None:
        """When polling returns state=done, meta is updated to done."""
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY2"
        meta_path = ocr_root / key / "meta.json"
        meta_path.parent.mkdir()
        # meta.json already has job_id — simulating an already-submitted job
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "queued",
            "ocr_job_id": "job-456",
        }), encoding="utf-8")

        lr_dir = library_records / "骨科"
        lr_dir.mkdir(parents=True)
        (lr_dir / f"{key}.md").write_text("""---
zotero_key: TESTKEY2
do_ocr: true
---
# Test""", encoding="utf-8")

        (exports / "骨科.json").write_text(json.dumps([
            {"key": key, "title": "Test Paper 2", "attachments": [
                {"contentType": "application/pdf", "path": "test2.pdf"}
            ]}
        ]), encoding="utf-8")

        # Real PDF so resolve_pdf_path succeeds
        real_pdf = vault / "test2.pdf"
        real_pdf.write_text("PDF content")

        # Configure poll response: state=done
        poll_response = MagicMock()
        poll_response.json.return_value = {
            "data": {
                "state": "done",
                "resultUrl": {"jsonUrl": "http://example.com/result.json"}
            }
        }
        poll_response.raise_for_status = MagicMock()

        # Use return_value for all calls — same mock is returned each time
        # This is sufficient since we only care about the first poll result
        with patch("paperforge.worker.ocr.pipeline_paths", return_value=paths):
            with patch("paperforge.worker.ocr.load_control_actions", return_value={key: {"do_ocr": True}}):
                with patch("paperforge.worker.ocr.load_export_rows", return_value=[
                    {"key": key, "attachments": [{"contentType": "application/pdf", "path": "test2.pdf"}], "title": "Test"}
                ]):
                    with patch("paperforge.worker.ocr.sync_ocr_queue", return_value=[
                        {"zotero_key": key, "has_pdf": True, "pdf_path": "test2.pdf", "queue_status": "queued"}
                    ]):
                        with patch("paperforge.worker.ocr.write_json") as mock_write:
                            with patch("paperforge.worker.ocr.requests.get", return_value=poll_response):
                                with patch("paperforge.worker.sync.run_selection_sync"):
                                    with patch("paperforge.worker.sync.run_index_refresh"):
                                        from paperforge.worker.ocr import run_ocr
                                        run_ocr(vault)

        meta_calls = [c for c in mock_write.call_args_list
                      if isinstance(c[0][1], dict) and c[0][1].get("zotero_key") == key]
        assert meta_calls, f"No meta write found for key {key}"
        final_meta = meta_calls[-1][0][1]
        assert final_meta.get("ocr_status") == "done", \
            f"Expected 'done', got {final_meta.get('ocr_status')}"


# ---------------------------------------------------------------------------
# Tests for processing -> error transition
# ---------------------------------------------------------------------------

class TestProcessingToErrorTransition:
    """Job moves from running to error when the API returns an error state."""

    def test_api_error_state_transitions_to_error(self, tmp_path: Path) -> None:
        """When polling returns state=error, meta is updated to error."""
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY3"
        meta_path = ocr_root / key / "meta.json"
        meta_path.parent.mkdir()
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "queued",
            "ocr_job_id": "job-789",
        }), encoding="utf-8")

        lr_dir = library_records / "骨科"
        lr_dir.mkdir(parents=True)
        (lr_dir / f"{key}.md").write_text("""---
zotero_key: TESTKEY3
do_ocr: true
---
# Test""", encoding="utf-8")

        (exports / "骨科.json").write_text(json.dumps([
            {"key": key, "title": "Test Paper 3", "attachments": [
                {"contentType": "application/pdf", "path": "test3.pdf"}
            ]}
        ]), encoding="utf-8")

        real_pdf = vault / "test3.pdf"
        real_pdf.write_text("PDF content")

        # Poll returns state=error
        error_response = MagicMock()
        error_response.json.return_value = {
            "data": {
                "state": "error",
                "errorMsg": "Model inference failed"
            }
        }
        error_response.raise_for_status = MagicMock()

        with patch("paperforge.worker.ocr.pipeline_paths", return_value=paths):
            with patch("paperforge.worker.ocr.load_control_actions", return_value={key: {"do_ocr": True}}):
                with patch("paperforge.worker.ocr.load_export_rows", return_value=[
                    {"key": key, "attachments": [{"contentType": "application/pdf", "path": "test3.pdf"}], "title": "Test"}
                ]):
                    with patch("paperforge.worker.ocr.sync_ocr_queue", return_value=[
                        {"zotero_key": key, "has_pdf": True, "pdf_path": "test3.pdf", "queue_status": "queued"}
                    ]):
                        with patch("paperforge.worker.ocr.write_json") as mock_write:
                            with patch("paperforge.worker.ocr.requests.get", return_value=error_response):
                                with patch("paperforge.worker.sync.run_selection_sync"):
                                    with patch("paperforge.worker.sync.run_index_refresh"):
                                        from paperforge.worker.ocr import run_ocr
                                        run_ocr(vault)

        meta_calls = [c for c in mock_write.call_args_list
                      if isinstance(c[0][1], dict) and c[0][1].get("zotero_key") == key]
        assert meta_calls, "No meta write for our key"
        final_meta = meta_calls[-1][0][1]
        assert final_meta.get("ocr_status") == "error", \
            f"Expected 'error', got {final_meta.get('ocr_status')}"
        assert "Model inference failed" in final_meta.get("error", "")


# ---------------------------------------------------------------------------
# Tests for processing -> blocked transition
# ---------------------------------------------------------------------------

class TestProcessingToBlockedTransition:
    """Job transitions to blocked when token is missing or PDF unreadable."""

    def test_missing_token_blocks_job(self, tmp_path: Path) -> None:
        """No PaddleOCR token -> ocr_status: blocked."""
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY4"
        meta_path = ocr_root / key / "meta.json"
        meta_path.parent.mkdir()
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "pending",
        }), encoding="utf-8")

        lr_dir = library_records / "骨科"
        lr_dir.mkdir(parents=True)
        (lr_dir / f"{key}.md").write_text("""---
zotero_key: TESTKEY4
do_ocr: true
---
# Test""", encoding="utf-8")

        (exports / "骨科.json").write_text(json.dumps([
            {"key": key, "title": "Test Paper 4", "attachments": [
                {"contentType": "application/pdf", "path": "test4.pdf"}
            ]}
        ]), encoding="utf-8")

        # Real PDF so resolve_pdf_path succeeds
        real_pdf = vault / "test4.pdf"
        real_pdf.write_text("PDF content")

        # Mock post to raise HTTPError 401 (invalid/expired token).
        # classify_error maps 401 -> 'blocked', so this tests the
        # blocked transition path without needing to manipulate env vars.
        import requests as _req
        _mock_resp = MagicMock()
        _mock_resp.status_code = 401
        _http_err = _req.exceptions.HTTPError("401 Unauthorized")
        _http_err.response = _mock_resp

        mock_post = MagicMock()
        mock_post.side_effect = _http_err

        def make_meta(*args, **kwargs):
            return {"zotero_key": key, "ocr_status": "pending"}

        with patch("paperforge.worker.ocr.pipeline_paths", return_value=paths):
            with patch("paperforge.worker.ocr.load_control_actions", return_value={key: {"do_ocr": True}}):
                with patch("paperforge.worker.ocr.load_export_rows", return_value=[
                    {"key": key, "attachments": [{"contentType": "application/pdf", "path": "test4.pdf"}], "title": "Test"}
                ]):
                    with patch("paperforge.worker.ocr.sync_ocr_queue", return_value=[
                        {"zotero_key": key, "has_pdf": True, "pdf_path": "test4.pdf", "queue_status": "pending"}
                    ]):
                        with patch("paperforge.worker.ocr.ensure_ocr_meta", side_effect=make_meta):
                            with patch("paperforge.worker.ocr.write_json") as mock_write:
                                with patch("paperforge.worker.sync.run_selection_sync"):
                                    with patch("paperforge.worker.sync.run_index_refresh"):
                                        with patch("paperforge.worker.ocr.requests.post", mock_post):
                                            with patch("paperforge.worker.ocr.requests.get", MagicMock()):
                                                from paperforge.worker.ocr import run_ocr
                                                run_ocr(vault)

        meta_calls = [c for c in mock_write.call_args_list
                      if isinstance(c[0][1], dict) and c[0][1].get("zotero_key") == key]
        assert meta_calls, "No meta write for our key"
        final_meta = meta_calls[-1][0][1]
        assert final_meta.get("ocr_status") == "blocked", \
            f"Expected 'blocked' (missing token), got {final_meta.get('ocr_status')}"


# ---------------------------------------------------------------------------
# Tests for sync_ocr_queue state reconciliation
# ---------------------------------------------------------------------------

class TestSyncOcrQueue:
    """sync_ocr_queue correctly reconciles existing queue with target rows."""

    def test_skips_done_and_blocked_from_existing_queue(self, tmp_path: Path) -> None:
        """sync_ocr_queue skips rows with ocr_status done/blocked."""
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY5"
        # Write existing queue file with done status
        ocr_queue_path = ocr_root / "ocr-queue.json"
        ocr_queue_path.write_text(json.dumps([
            {"zotero_key": key, "has_pdf": True, "pdf_path": "test.pdf",
             "queue_status": "done", "queued_at": "2024-01-01T00:00:00Z"}
        ]), encoding="utf-8")

        # meta.json says done
        meta_path = ocr_root / key / "meta.json"
        meta_path.parent.mkdir()
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "done",
        }), encoding="utf-8")

        target_rows = [
            {"zotero_key": key, "has_pdf": True, "pdf_path": "test.pdf"}
        ]

        from paperforge.worker.ocr import sync_ocr_queue
        result = sync_ocr_queue(paths, target_rows)

        # done should be skipped
        assert not any(r["zotero_key"] == key for r in result), \
            "done status should be skipped"


# ---------------------------------------------------------------------------
# Tests for cleanup_blocked_ocr_dirs
# ---------------------------------------------------------------------------

class TestCleanupBlockedOcrDirs:
    """cleanup_blocked_ocr_dirs removes empty blocked directories."""

    def test_removes_blocked_dir_without_payload(self, tmp_path: Path) -> None:
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY6"
        blocked_dir = ocr_root / key
        blocked_dir.mkdir()
        meta_path = blocked_dir / "meta.json"
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "blocked",
        }), encoding="utf-8")
        # No fulltext.md or json/result.json -> should be removed

        from paperforge.worker.ocr import cleanup_blocked_ocr_dirs
        cleanup_blocked_ocr_dirs(paths)

        assert not blocked_dir.exists(), \
            f"Blocked dir {blocked_dir} should have been removed"

    def test_preserves_blocked_dir_with_payload(self, tmp_path: Path) -> None:
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        key = "TESTKEY7"
        blocked_dir = ocr_root / key
        blocked_dir.mkdir()
        meta_path = blocked_dir / "meta.json"
        meta_path.write_text(json.dumps({
            "zotero_key": key,
            "ocr_status": "blocked",
        }), encoding="utf-8")
        # Add fulltext.md as payload
        (blocked_dir / "fulltext.md").write_text("OCR result text", encoding="utf-8")

        from paperforge.worker.ocr import cleanup_blocked_ocr_dirs
        cleanup_blocked_ocr_dirs(paths)

        assert blocked_dir.exists(), \
            f"Blocked dir with payload should be preserved"


# ---------------------------------------------------------------------------
# Tests for state definitions
# ---------------------------------------------------------------------------

class TestOcrJobStates:
    """Valid OCR job states are: pending, queued, running, done, error, blocked, nopdf."""

    def test_all_expected_states_covered(self, tmp_path: Path) -> None:
        """Ensure run_ocr handles all documented states without crashing."""
        vault, ocr_root, exports, library_records = _make_vault(tmp_path)
        paths = _mock_paths(vault, ocr_root, exports, library_records)

        # States to test: pending, queued, running, done, error, blocked, nopdf
        states = ["pending", "queued", "running", "done", "error", "blocked", "nopdf"]
        for state in states:
            key = f"TESTKEY_STATE_{state}"
            meta_path = ocr_root / key / "meta.json"
            meta_path.parent.mkdir()
            meta_path.write_text(json.dumps({
                "zotero_key": key,
                "ocr_status": state,
            }), encoding="utf-8")

            lr_dir = library_records / "骨科"
            lr_dir.mkdir(parents=True, exist_ok=True)
            (lr_dir / f"{key}.md").write_text(f"""---
zotero_key: {key}
do_ocr: true
---
# Test""", encoding="utf-8")

            (exports / "骨科.json").write_text(json.dumps([
                {"key": key, "title": f"Test {state}", "attachments": [
                    {"contentType": "application/pdf", "path": "test.pdf"}
                ]}
            ]), encoding="utf-8")

        # Smoke test: ensure no state raises an unhandled exception
        from paperforge.worker.ocr import run_ocr
        try:
            run_ocr(vault)
        except Exception as e:
            pytest.fail(f"run_ocr raised {type(e).__name__}: {e}")
