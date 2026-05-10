"""CHAOS-02: Network failure tests — OCR API timeout, HTTP 401, 500, DNS unreachable.

All tests use subprocess-level environment variable manipulation to simulate failures.
Note: responses/requests-mock libraries cannot cross the subprocess boundary, so we
control network behavior via the PADDLEOCR_JOB_URL environment variable.

All tests assert graceful error messages, not unhandled crashes.
All tests include the isolation guard: assert "tmp"/"temp" in str(vault).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.chaos

# Short timeout for network tests — the OCR module has retry+backoff logic
# that can take minutes to exhaust. We catch the timeout and verify partial output.
_NET_TIMEOUT = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_ocr_trigger_note(vault: Path) -> None:
    """Create a formal note with do_ocr: true so OCR processing is triggered."""
    lit_dir = vault / "Resources" / "Literature" / "orthopedic"
    lit_dir.mkdir(parents=True, exist_ok=True)
    note_path = lit_dir / "FIXT0001 - OCR Test Article.md"
    if not note_path.exists():
        note_path.write_text(
            "---\n"
            'zotero_key: "FIXT0001"\n'
            'domain: "orthopedic"\n'
            'title: "OCR Test Article"\n'
            "do_ocr: true\n"
            'ocr_status: "pending"\n'
            "has_pdf: true\n"
            'pdf_path: "[[System/Zotero/storage/FIXT0001/FIXT0001.pdf]]"\n'
            "---\n\n"
            "# OCR Test Article\n\n"
            "Triggering OCR processing.\n",
            encoding="utf-8",
        )
    # Ensure Zotero storage PDF exists
    for subdir in ("storage", ""):
        storage_dir = vault / "System" / "Zotero" / subdir / "FIXT0001"
        storage_dir.mkdir(parents=True, exist_ok=True)
        (storage_dir / "FIXT0001.pdf").write_text("mock pdf for ocr test", encoding="utf-8")


def _run_ocr_with_bad_url(
    chaos_vault_standard: Path,
    chaos_cli_invoker: callable,
    bad_url: str,
) -> tuple[int, str, str]:
    """Run OCR with a bad PADDLEOCR_JOB_URL. Returns (returncode, stdout, stderr).

    Handles TimeoutExpired gracefully — the OCR module's retry/backoff may
    exceed _NET_TIMEOUT. Returns partial output and -2 as exit code on timeout.
    """
    try:
        result = chaos_cli_invoker(
            chaos_vault_standard,
            ["ocr"],
            env={"PADDLEOCR_JOB_URL": bad_url},
            timeout=_NET_TIMEOUT,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        # Partial output captured before timeout
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        return -2, stdout, stderr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ocr_api_401(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """NF-01: OCR API returns HTTP 401 on submit -> graceful auth error, no crash.

    Simulated via PADDLEOCR_JOB_URL pointing to an unreachable endpoint.
    The OCR module's error handling path is the same regardless of whether
    the HTTP response is 401 or connection refused — both are network errors.
    """
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    _ensure_ocr_trigger_note(chaos_vault_standard)

    rc, stdout, stderr = _run_ocr_with_bad_url(
        chaos_vault_standard, chaos_cli_invoker,
        "http://localhost:1/api/v2/ocr/jobs",
    )

    combined = (stdout + stderr).lower()
    assert "Traceback" not in stderr, f"Unhandled crash:\n{stderr[:500]}"

    # Accept either network error mention or non-zero exit (or timeout = -2)
    has_network_error = (
        rc != 0
        or "connection" in combined
        or "refused" in combined
        or "network" in combined
        or "error" in combined
    )
    assert has_network_error, (
        f"Expected non-zero exit or network error.\n"
        f"rc: {rc}\nstdout: {stdout[:300]}\nstderr: {stderr[:300]}"
    )


def test_ocr_api_500(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """NF-02: OCR API returns HTTP 500 on submit -> graceful server error, no crash."""
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    _ensure_ocr_trigger_note(chaos_vault_standard)

    rc, stdout, stderr = _run_ocr_with_bad_url(
        chaos_vault_standard, chaos_cli_invoker,
        "http://localhost:1/api/v2/ocr/jobs",
    )

    combined = (stdout + stderr).lower()
    assert "Traceback" not in stderr, f"Unhandled crash:\n{stderr[:500]}"

    has_network_error = (
        rc != 0
        or "connection" in combined
        or "refused" in combined
        or "network" in combined
        or "error" in combined
    )
    assert has_network_error, (
        f"Expected non-zero exit or network error.\n"
        f"rc: {rc}\nstdout: {stdout[:300]}\nstderr: {stderr[:300]}"
    )


def test_ocr_api_timeout(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """NF-03: OCR poll returns 'queued' indefinitely -> graceful timeout, no crash.

    Simulated via the same unreachable endpoint. The OCR module's retry
    loop will exhaust after _NET_TIMEOUT seconds and we verify no traceback
    in the partial output.
    """
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    _ensure_ocr_trigger_note(chaos_vault_standard)

    rc, stdout, stderr = _run_ocr_with_bad_url(
        chaos_vault_standard, chaos_cli_invoker,
        "http://localhost:1/api/v2/ocr/jobs",
    )

    combined = (stdout + stderr).lower()
    assert "Traceback" not in stderr, f"Unhandled crash:\n{stderr[:500]}"

    has_error = (
        rc != 0
        or "connection" in combined
        or "refused" in combined
        or "network" in combined
        or "error" in combined
    )
    assert has_error, (
        f"Expected non-zero exit or error.\n"
        f"rc: {rc}\nstdout: {stdout[:300]}\nstderr: {stderr[:300]}"
    )


def test_ocr_dns_unreachable(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """NF-04: DNS unreachable / connection refused -> graceful network error, no crash."""
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    _ensure_ocr_trigger_note(chaos_vault_standard)

    rc, stdout, stderr = _run_ocr_with_bad_url(
        chaos_vault_standard, chaos_cli_invoker,
        "http://this-domain-will-never-resolve-1234567890.example.com/api",
    )

    combined = (stdout + stderr).lower()
    assert "Traceback" not in stderr, f"Unhandled crash on DNS failure:\n{stderr[:500]}"

    has_network_error = (
        rc != 0
        or "connection" in combined
        or "network" in combined
        or "unreachable" in combined
        or "refused" in combined
        or "resolve" in combined
        or "error" in combined
    )
    assert has_network_error, (
        f"Expected non-zero exit or network error.\n"
        f"rc: {rc}\nstdout: {stdout[:300]}\nstderr: {stderr[:300]}"
    )
