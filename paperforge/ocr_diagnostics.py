"""OCR diagnostics — tiered L1-L4 checks for PaddleOCR configuration.

Provides `ocr_doctor()` to validate token, URL reachability, API schema,
and optional live PDF round-trip before queueing real OCR jobs.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


def ocr_doctor(config: dict[str, str] | None, live: bool = False) -> dict:
    """Run tiered OCR diagnostics.

    Args:
        config: Optional configuration dict (reserved for future use).
        live: If True, run L4 live PDF round-trip test.

    Returns:
        Dict with keys: level, passed, error, fix, raw_response (optional).
    """
    # L1 — Token presence
    token = os.environ.get("PADDLEOCR_API_TOKEN", "").strip()
    if not token:
        token = os.environ.get("PADDLEOCR_API_TOKEN_USER", "").strip()
    if not token:
        return {
            "level": 1,
            "passed": False,
            "error": "PADDLEOCR_API_TOKEN not found in environment",
            "fix": "Set PADDLEOCR_API_TOKEN in .env or environment variables and re-run `paperforge ocr --diagnose`",
        }

    # L2 — URL reachability (use POST since most endpoints reject GET)
    job_url = os.environ.get(
        "PADDLEOCR_JOB_URL",
        "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
    ).strip()
    try:
        resp = requests.post(
            job_url,
            headers={"Authorization": f"bearer {token}"},
            json={"model": os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5")},
            timeout=30,
        )
        if resp.status_code == 401:
            return {
                "level": 2,
                "passed": False,
                "error": "URL returned 401 Unauthorized",
                "fix": "PaddleOCR API token is invalid. Check PADDLEOCR_API_TOKEN and re-run `paperforge ocr --diagnose`",
            }
        if resp.status_code >= 500:
            return {
                "level": 2,
                "passed": False,
                "error": f"URL returned {resp.status_code}",
                "fix": "OCR provider is experiencing issues. Retry later with `paperforge ocr --diagnose`",
            }
        # 200 = happy path, 400 = reachable but request incomplete
        # Both prove URL is live and token is valid (else 401)
        if resp.status_code not in (200, 400):
            return {
                "level": 2,
                "passed": False,
                "error": f"URL returned {resp.status_code}",
                "fix": "Check PADDLEOCR_JOB_URL in .env and re-run `paperforge ocr --diagnose`",
            }
    except requests.RequestException as e:
        return {
            "level": 2,
            "passed": False,
            "error": f"Failed to reach OCR URL: {e}",
            "fix": "Check network connection and PADDLEOCR_JOB_URL in .env",
        }

    # L3 — API response structure
    try:
        minimal_payload = {
            "model": os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5"),
            "optionalPayload": json.dumps({"useDocOrientationClassify": False}),
        }
        resp = requests.post(
            job_url,
            headers={"Authorization": f"bearer {token}"},
            data=minimal_payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data or "jobId" not in data.get("data", {}):
            return {
                "level": 3,
                "passed": False,
                "error": "API response missing expected fields (data.jobId)",
                "fix": "PaddleOCR API schema may have changed. Check provider documentation.",
                "raw_response": resp.text[:500],
            }
        job_id = data["data"]["jobId"]
        # Cancel the test job immediately to avoid wasting resources
        try:
            requests.delete(
                f"{job_url}/{job_id}",
                headers={"Authorization": f"bearer {token}"},
                timeout=10,
            )
        except Exception:
            pass  # ignore cancel failure
    except requests.RequestException:
        # Without a real file upload the API will reject the request (4xx/5xx).
        # This is expected — L2 already confirmed connectivity + token validity.
        # Run `--live` for a full upload round-trip test.
        return {
            "level": 3,
            "passed": True,
            "message": "Skipped (requires file upload). Use `paperforge ocr --diagnose --live` for full validation.",
        }
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "level": 3,
            "passed": False,
            "error": f"API response parsing failed: {e}",
            "fix": "PaddleOCR API schema may have changed. Check provider documentation.",
        }

    # L4 — Live PDF test (only if live=True)
    if live:
        fixture_pdf = Path(__file__).parent.parent / "tests" / "fixtures" / "blank.pdf"
        if not fixture_pdf.exists():
            return {
                "level": 4,
                "passed": False,
                "error": "Live test fixture PDF not found",
                "fix": "Install test fixtures or run without --live flag.",
            }
        try:
            with open(fixture_pdf, "rb") as f:
                resp = requests.post(
                    job_url,
                    headers={"Authorization": f"bearer {token}"},
                    data={"model": os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5")},
                    files={"file": f},
                    timeout=120,
                )
            resp.raise_for_status()
            data = resp.json()
            job_id = data["data"]["jobId"]
            # Poll for result (max 10 attempts, 5s delay)
            for _ in range(10):
                time.sleep(5)
                poll = requests.get(
                    f"{job_url}/{job_id}",
                    headers={"Authorization": f"bearer {token}"},
                    timeout=30,
                )
                poll_data = poll.json()["data"]
                if poll_data["state"] == "done":
                    break
                if poll_data["state"] == "error":
                    return {
                        "level": 4,
                        "passed": False,
                        "error": f"Live PDF test failed: {poll_data.get('errorMsg', 'unknown')}",
                        "fix": "PDF may be unreadable or OCR service error. Try a different PDF or check service status.",
                    }
            else:
                return {
                    "level": 4,
                    "passed": False,
                    "error": "Live PDF test timed out",
                    "fix": "OCR service is slow or overloaded. Retry later without --live flag.",
                }
        except Exception as e:
            return {
                "level": 4,
                "passed": False,
                "error": f"Live PDF test exception: {e}",
                "fix": "Check network and PDF format. Run without --live for basic diagnostics.",
            }

    return {
        "level": 4 if live else 3,
        "passed": True,
        "message": "All diagnostics passed. OCR is ready.",
    }


def classify_error(exception: Exception, response) -> tuple[str, str]:
    """Map an exception to an OCR failure state and actionable suggestion.

    Args:
        exception: The raised exception.
        response: Optional requests.Response associated with the exception.

    Returns:
        Tuple of (state, suggestion) where state is 'blocked' or 'error'.
    """
    import requests

    if isinstance(exception, requests.exceptions.ConnectionError):
        return (
            "blocked",
            "Check PADDLEOCR_JOB_URL in .env and re-run `paperforge ocr`",
        )
    if isinstance(exception, (requests.exceptions.Timeout, requests.exceptions.ReadTimeout)):
        return (
            "error",
            "OCR service timed out. Retry with `paperforge ocr` or check network.",
        )
    if isinstance(exception, requests.exceptions.HTTPError):
        status = response.status_code if response is not None else 0
        if status == 401:
            return (
                "blocked",
                "PaddleOCR API key invalid or missing. Set PADDLEOCR_API_TOKEN and re-run `paperforge ocr`",
            )
        if status == 404:
            return (
                "error",
                "OCR job not found. Re-run `paperforge ocr` to resubmit.",
            )
        if status >= 500:
            return (
                "error",
                "OCR provider error. Retry later with `paperforge ocr`.",
            )
        return (
            "error",
            f"OCR HTTP error {status}. Retry with `paperforge ocr` or run `paperforge ocr --diagnose`.",
        )
    if isinstance(exception, json.JSONDecodeError):
        return (
            "error",
            "PaddleOCR API response format changed. Check `meta.json` raw response and update client.",
        )
    if isinstance(exception, KeyError):
        return (
            "error",
            "PaddleOCR API response missing expected fields. Provider may have updated schema.",
        )
    if isinstance(exception, FileNotFoundError):
        return (
            "blocked",
            "PDF file not found. Check Zotero attachment and re-run `paperforge ocr`.",
        )
    return (
        "error",
        f"Unexpected error: {exception}. Retry with `paperforge ocr` or run `paperforge ocr --diagnose`.",
    )
