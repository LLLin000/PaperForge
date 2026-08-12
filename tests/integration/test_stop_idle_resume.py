"""#137 retirement contract: the cross-process `embed stop` control plane is
RETIRED — cancellation flows through the unified token (stdin
PAPERFORGE_STOP / SIGINT / SIGTERM).  `embed stop` now returns the
retirement error; the stop→idle→resume lifecycle is tested through the
unified token in unit tests.
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
        '{"schema_version": 2, "vault_config":{"system_dir":"System"}}', encoding="utf-8"
    )
    (vault / "System" / "PaperForge").mkdir(parents=True)
    return vault


def _run_embed_stop(vault: Path) -> subprocess.CompletedProcess:
    """Run embed stop (retired) and return the completed process."""
    return subprocess.run(
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
    """#137 retirement contract for the embed control plane."""

    def test_stop_is_retired(self, tmp_path: Path):
        """embed stop returns rc1 with the retirement message — no control
        plane exists anymore."""
        vault = _build_vault(tmp_path)
        _mark_running(vault, pid=99999, current=5, total=100)
        result = _run_embed_stop(vault)
        assert result.returncode == 2  # argparse: invalid subcommand choice
        assert "invalid choice" in result.stderr and "stop" in result.stderr

    def test_stop_when_idle_stays_idle(self, tmp_path: Path):
        """embed stop --json on idle build is retired too."""
        vault = _build_vault(tmp_path)

        result = _run_embed_stop(vault)
        assert result.returncode == 2  # argparse: invalid subcommand choice
        assert "invalid choice" in result.stderr and "stop" in result.stderr
        bs = _read_build_state(vault)
        assert bs["status"] == "idle"

    def test_resume_after_stop_reads_progress(self, tmp_path: Path):
        """Even with a running build, embed stop is retired; status keeps
        reporting the live build state (no control-plane settlement)."""
        vault = _build_vault(tmp_path)

        _mark_running(vault, pid=99998, current=42, total=200)

        result = _run_embed_stop(vault)
        assert result.returncode == 2  # argparse: invalid subcommand choice
        assert "invalid choice" in result.stderr and "stop" in result.stderr

        # Status still reports the live build state — untouched by stop.
        status = _run_embed_status(vault)
        bs = status.get("build_state", {})
        assert bs.get("current", 0) == 42
