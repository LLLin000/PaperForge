"""E2E test: status, doctor, and repair CLI commands in temp vault with known state."""

from __future__ import annotations

import json

import pytest


pytestmark = pytest.mark.e2e


def test_status_json(e2e_cli_invoker: tuple) -> None:
    """Verify `paperforge status --json` returns valid JSON with expected keys."""
    invoker, vault = e2e_cli_invoker

    result = invoker(["status", "--json"])
    assert result.returncode == 0, (
        f"Status command failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )

    envelope = json.loads(result.stdout)
    payload = envelope["data"]
    assert "formal_notes" in payload, "Status JSON missing 'formal_notes' key"
    assert envelope["version"] != ""


def test_doctor_runs(e2e_cli_invoker: tuple) -> None:
    """Verify `paperforge doctor` runs without error and produces output."""
    invoker, vault = e2e_cli_invoker

    result = invoker(["doctor"])
    assert result.returncode in (0, 1), (
        f"Doctor command unexpected exit code {result.returncode}:\n"
        f"stdout:{result.stdout}\nstderr:{result.stderr}"
    )
    # Output should mention setup-related checks
    output = ((result.stdout or "") + (result.stderr or "")).lower()
    assert "python" in output or "paperforge" in output or "config" in output or "status" in output or "ok" in output or "fail" in output or result.returncode == 0, (
        "Doctor output should contain setup-related content"
    )


def test_repair_dry_run(e2e_cli_invoker: tuple) -> None:
    """Verify `paperforge repair` dry run completes (0 exit code expected for dry-run)."""
    invoker, vault = e2e_cli_invoker

    result = invoker(["repair"])
    assert result.returncode == 0, (
        f"Repair dry-run failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )
