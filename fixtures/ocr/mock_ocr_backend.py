"""Mock OCR backend — replayable PaddleOCR API responses using responses library.

Provides context-managed interceptors for all PaddleOCR API states:
- submit: POST /api/v2/ocr/jobs -> 202 + job_id
- poll: GET /api/v2/ocr/jobs/{id} -> pending/done
- result: GET result_url -> OCR extraction data
- error: 401/400/500 responses
- timeout: poll returns 'queued' forever

Usage:
    from fixtures.ocr.mock_ocr_backend import mock_ocr_success

    with mock_ocr_success():
        # All PaddleOCR HTTP calls are intercepted
        run_ocr(vault, ...)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import responses

FIXTURES_DIR = Path(__file__).resolve().parent


def _load_fixture(name: str) -> dict:
    """Load a named fixture JSON from fixtures/ocr/."""
    path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def mock_ocr_success() -> responses.RequestsMock:
    """Standard success path: submit -> poll -> result.

    Returns a RequestsMock context manager.
    """
    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    _add_submit(rsps)
    _add_poll(rsps, "mock-job-001", "completed")
    _add_result(rsps)
    return rsps


def mock_ocr_pending() -> responses.RequestsMock:
    """Job submitted but still processing (poll returns processing)."""
    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    _add_submit(rsps)
    _add_poll(rsps, "mock-job-001", "processing", progress=0.45)
    return rsps


def mock_ocr_error(status: int = 401) -> responses.RequestsMock:
    """API returns an error on submit."""
    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    rsps.add(
        responses.POST,
        "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        json=_load_fixture("paddleocr_error.json"),
        status=status,
    )
    return rsps


def mock_ocr_timeout() -> responses.RequestsMock:
    """Submit succeeds but job never completes (polls return queued forever)."""
    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    _add_submit(rsps)
    rsps.add(
        responses.GET,
        re.compile(r"https://paddleocr\.aistudio-app\.com/api/v2/ocr/jobs/mock-job-\w+"),
        json={"job_id": "mock-job-timeout-001", "status": "queued", "progress": 0.0},
        status=200,
    )
    return rsps


def _add_submit(rsps: responses.RequestsMock) -> None:
    """Add submit endpoint mock."""
    rsps.add(
        responses.POST,
        "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
        json=_load_fixture("paddleocr_submit.json"),
        status=202,
    )


def _add_poll(
    rsps: responses.RequestsMock,
    job_id: str,
    status: str,
    progress: float = 1.0,
) -> None:
    """Add poll endpoint mock."""
    url = f"https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/{job_id}"
    fixture_key = (
        f"paddleocr_poll_{status}.json"
        if status in ("pending", "done")
        else "paddleocr_poll_done.json"
    )
    try:
        data = _load_fixture(fixture_key)
    except FileNotFoundError:
        data = {"job_id": job_id, "status": status, "progress": progress}
    rsps.add(responses.GET, url, json=data, status=200)


def _add_result(rsps: responses.RequestsMock) -> None:
    """Add result URL endpoint mock."""
    rsps.add(
        responses.GET,
        "https://api.mock/results/mock-job-001",
        json=_load_fixture("paddleocr_result.json"),
        status=200,
    )
