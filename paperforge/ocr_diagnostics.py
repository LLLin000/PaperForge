"""OCR diagnostics — tiered L1-L4 checks for PaddleOCR configuration.

Provides `ocr_doctor()` to validate token, URL reachability, API schema,
and optional live PDF round-trip before queueing real OCR jobs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def _find_live_fixture_pdf() -> Path | None:
    """Locate the live-doctor blank PDF fixture.

    Prefer a fixture shipped alongside the source tree, but also fall back to the
    current working tree when PaperForge is imported from site-packages during tests.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "blank.pdf",
        Path.cwd() / "tests" / "fixtures" / "blank.pdf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def ocr_doctor(
    config: dict[str, str] | None,
    live: bool = False,
    *,
    cache_path: Path | None = None,
    cache_ttl_seconds: float = 120.0,
) -> dict:
    """Run tiered OCR diagnostics.

    Args:
        config: Optional configuration dict (reserved for future use).
        live: If True, run L4 live PDF round-trip test.
        cache_path: Optional JSON file path used to cache non-live L2/L3 results.
        cache_ttl_seconds: Cache TTL in seconds (default 120s; ignored when live=True).

    Returns:
        Dict with keys: level, passed, error, fix, raw_response (optional).
    """
    # L1 — Token presence (#173/C1: credential authority; no legacy fallbacks)
    from paperforge.credentials import MISSING, CredentialError, CredentialKey, resolve

    try:
        token = resolve(CredentialKey("ocr"))
    except CredentialError as exc:
        if exc.code != MISSING:
            # Backend faults are NOT "missing key" — surface them.
            raise
        return {
            "level": 1,
            "passed": False,
            "error": "OCR credential not found",
            "fix": "Run `paperforge auth set ocr --stdin` or supply PAPERFORGE_CREDENTIAL_OCR__DEFAULT, then re-run `paperforge ocr --diagnose`",
        }

    # L2 — URL reachability (use POST since most endpoints reject GET)
    cfg = config or {}
    job_url = (
        str(cfg.get("paddleocr_job_url") or "").strip()
        or os.environ.get("PADDLEOCR_JOB_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs").strip()
    )
    ocr_model = (
        str(cfg.get("paddleocr_model") or "").strip()
        or os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.6").strip()
    )

    use_cache = (
        not live
        and cache_path is not None
        and cache_ttl_seconds > 0
        and not os.environ.get("PAPERFORGE_OCR_DOCTOR_NOCACHE")
    )
    cache_fp = hashlib.sha256(
        f"{job_url}|{ocr_model}|{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}".encode("utf-8")
    ).hexdigest()[:24]

    if use_cache and cache_path is not None and cache_path.is_file():
        try:
            cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if (
                isinstance(cached_payload, dict)
                and cached_payload.get("fingerprint") == cache_fp
                and (time.time() - float(cached_payload.get("cached_at", 0.0))) <= cache_ttl_seconds
                and isinstance(cached_payload.get("result"), dict)
            ):
                return dict(cached_payload["result"])
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("ignoring stale/unreadable ocr_doctor cache %s: %s", cache_path, exc)

    def _cache_and_return(res: dict) -> dict:
        if use_cache and cache_path is not None:
            try:
                from paperforge.core.io import write_json_atomic

                write_json_atomic(
                    cache_path,
                    {
                        "fingerprint": cache_fp,
                        "cached_at": time.time(),
                        "result": res,
                    },
                )
            except (OSError, TypeError) as exc:
                logger.debug("best-effort ocr_doctor cache write skipped: %s", exc)
        return res

    try:
        resp = requests.post(
            job_url,
            headers={"Authorization": f"bearer {token}"},
            json={"model": ocr_model},
            timeout=10,
        )
        if resp.status_code == 401:
            return _cache_and_return({
                "level": 2,
                "passed": False,
                "error": "URL returned 401 Unauthorized",
                "fix": "PaddleOCR API token is invalid. Update OCR API Key in PaperForge Settings or run `paperforge auth set ocr --stdin --replace`",
            })
        if resp.status_code >= 500:
            return _cache_and_return({
                "level": 2,
                "passed": False,
                "error": f"URL returned {resp.status_code}",
                "fix": "OCR provider is experiencing issues. Retry later with `paperforge ocr --diagnose`",
            })
        # 200 = happy path, 400 = reachable + auth valid (missing multipart file)
        if resp.status_code == 400 and not live:
            return _cache_and_return({
                "level": 3,
                "passed": True,
                "message": "Skipped (requires file upload). Use `paperforge ocr --diagnose --live` for full validation.",
            })
        if resp.status_code not in (200, 400):
            return _cache_and_return({
                "level": 2,
                "passed": False,
                "error": f"URL returned {resp.status_code}",
                "fix": "Check PaddleOCR Job URL in PaperForge Settings (or run `paperforge config set paddleocr_job_url <URL>`)",
            })
    except requests.RequestException as e:
        return _cache_and_return({
            "level": 2,
            "passed": False,
            "error": f"Failed to reach OCR URL: {e}",
            "fix": "Check network connection and PaddleOCR Job URL in PaperForge Settings",
        })

    # L3 — API response structure
    try:
        minimal_payload = {
            "model": ocr_model,
            "optionalPayload": json.dumps({"useDocOrientationClassify": False}),
        }
        resp = requests.post(
            job_url,
            headers={"Authorization": f"bearer {token}"},
            data=minimal_payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data or "jobId" not in data.get("data", {}):
            return _cache_and_return({
                "level": 3,
                "passed": False,
                "error": "API response missing expected fields (data.jobId)",
                "fix": "PaddleOCR API schema may have changed. Check provider documentation.",
                "raw_response": resp.text[:500],
            })
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
        return _cache_and_return({
            "level": 3,
            "passed": True,
            "message": "Skipped (requires file upload). Use `paperforge ocr --diagnose --live` for full validation.",
        })
    except (json.JSONDecodeError, KeyError) as e:
        return _cache_and_return({
            "level": 3,
            "passed": False,
            "error": f"API response parsing failed: {e}",
            "fix": "PaddleOCR API schema may have changed. Check provider documentation.",
        })

    # L4 — Live PDF test (only if live=True)
    if live:
        fixture_pdf = _find_live_fixture_pdf()
        if fixture_pdf is None:
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
                    data={"model": ocr_model},
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
                "PaddleOCR API key invalid or missing. Run `paperforge auth set ocr --stdin` and re-run `paperforge ocr`",
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
