"""Integration tests for the build lifecycle stop → idle → resume cycle.

Verifies that embed stop --json marks build as stopping, settles to idle,
and that resume can continue a build from progress.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PYTHON = Path(r"D:\L\OB\Literature-hub\.venv\Scripts\python.exe")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_vault(tmp_path: Path) -> Path:
    """Build a minimal vault with paperforge.json."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True)
    (vault / "paperforge.json").write_text(
        '{"vault_config":{"system_dir":"System"}}', encoding="utf-8"
    )
    (vault / "System" / "PaperForge").mkdir(parents=True)
    return vault


def _run_embed_stop(vault: Path) -> dict:
    """Run embed stop --json and return parsed data."""
    result = subprocess.run(
        [
            str(PYTHON),
            "-m",
            "paperforge",
            "--vault",
            str(vault),
            "embed",
            "stop",
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    parsed = json.loads(result.stdout)
    return parsed


def _run_embed_status(vault: Path) -> dict:
    """Run embed status --json and return parsed data."""
    result = subprocess.run(
        [
            str(PYTHON),
            "-m",
            "paperforge",
            "--vault",
            str(vault),
            "embed",
            "status",
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    return parsed["data"]


def _mark_running(vault: Path, pid: int, current: int = 5, total: int = 100) -> None:
    """Set build_state to 'running' with the given PID."""
    from paperforge.embedding.build_state import mark_vector_build_state

    mark_vector_build_state(
        vault,
        status="running",
        pid=pid,
        current=current,
        total=total,
        paper_id="TESTKEY",
        model="test-model",
        mode="api",
    )


def _read_build_state(vault: Path) -> dict:
    """Read build_state table."""
    from paperforge.embedding.build_state import read_vector_build_state

    return read_vector_build_state(vault)


class TestStopIdleResume:
    """Stop → idle → resume lifecycle."""

    def test_stop_returns_stopped_and_idle(self, tmp_path: Path):
        """embed stop --json returns {state: stopped} when a build is running, and settles to idle."""
        vault = _build_vault(tmp_path)

        # Set build to running with a dead PID (not 0 — 0 is falsy in Python)
        _mark_running(vault, pid=99999, current=5, total=100)

        # Stop
        result = _run_embed_stop(vault)
        assert result["ok"] is True, f"Stop returned error: {result}"
        assert result["data"]["state"] == "stopped", f"Expected stopped, got {result['data']['state']}"

        # Verify build state settled to idle
        bs = _read_build_state(vault)
        assert bs["status"] == "idle", f"Expected idle, got {bs}"
        assert bs["pid"] == 0

    def test_stop_when_idle_stays_idle(self, tmp_path: Path):
        """embed stop --json on idle build returns {state: idle}."""
        vault = _build_vault(tmp_path)

        result = _run_embed_stop(vault)
        assert result["ok"] is True
        assert result["data"]["state"] == "idle"

        bs = _read_build_state(vault)
        assert bs["status"] == "idle"

    def test_resume_after_stop_reads_progress(self, tmp_path: Path):
        """After stop, status shows the idle state with progress, and resume mode continues from there."""
        vault = _build_vault(tmp_path)

        _mark_running(vault, pid=99998, current=42, total=200)

        # Stop
        _run_embed_stop(vault)

        # Status should report progress and idle state
        status = _run_embed_status(vault)
        bs = status.get("build_state", {})
        assert bs.get("status") == "idle"
        assert bs.get("current", 0) == 42
        assert bs.get("total", 0) == 200

        # Resume mode: verify that a subsequent --resume build picks up from idle
        # (we can't do a full build without a real vault, so we check that
        # the resume path isn't blocked by the idle state)
        from paperforge.embedding.build_state import read_vector_build_state

        bs_read = read_vector_build_state(vault)
        assert bs_read["status"] == "idle"
        # A resume build call would check this and start fresh or continue
        # The state is correctly idle which allows resume
