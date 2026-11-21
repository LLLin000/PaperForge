"""Unit tests for Wave 2 Low-Memory Global ControlDaemon (`ControlDaemon` & duplex RPC)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from paperforge.commands.daemon import serve_stdio
from paperforge.config import bootstrap_config
from paperforge.services.control_daemon import (
    ControlDaemon,
    get_process_rss_bytes,
    is_pid_alive,
)

pytestmark = pytest.mark.unit


def test_control_daemon_low_memory_rss_and_pid_watchdog_primitives() -> None:
    rss = get_process_rss_bytes()
    assert rss >= 0
    assert is_pid_alive(os.getpid()) is True
    # Very large nonexistent PID should report dead
    assert is_pid_alive(999_999_991) is False

    ctrl = ControlDaemon(parent_pid=os.getpid())
    health = ctrl.health()
    assert health["ok"] is True
    assert health["check_parent"] if "check_parent" in health else ctrl.check_parent_alive() is True

    # Prove cold-start ControlDaemon loads zero heavy modules (isolated from earlier tests in same pytest process)
    cold = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from paperforge.services.control_daemon import ControlDaemon; print(json.dumps(ControlDaemon().health()['heavy_modules_loaded']))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(cold.stdout.strip()) == []


def test_control_daemon_notices_idle_trim_and_exclusive_barrier(tmp_path: Path) -> None:
    pushed: list[dict] = []
    ctrl = ControlDaemon(push_sink=pushed.append)
    vault = tmp_path / "vault"
    vault.mkdir()
    bootstrap_config(vault)

    # Notice ring buffer + duplex push
    n = ctrl.push_notice(
        level="info",
        code="upgrade.available",
        title="发现旧版文献库",
        detail="可一键无感升级",
        vault=str(vault),
    )
    assert any(ev["event"] == "notice.push" and ev["data"]["notice_id"] == n["notice_id"] for ev in pushed)
    assert len(ctrl.list_notices(vault=str(vault))) == 1
    assert ctrl.ack_notice(n["notice_id"]) is True
    assert len(ctrl.list_notices(vault=str(vault))) == 0

    # Exclusive barrier rejects conflicting background job submissions cleanly
    ctrl.acquire_exclusive_barrier(vault, "upgrade_cutover")
    rejected = ctrl.submit_job(vault, "sync")
    assert rejected["accepted"] is False
    assert rejected["reason"] == "vault_upgrade_barrier_active"
    ctrl.release_exclusive_barrier(vault)

    # Bounded cache + idle memory trim
    ctrl.get_or_refresh_vault(vault)
    assert len(ctrl.health()["cached_vaults"]) == 1
    # Force last_access into the past to verify cold-vault eviction + gc
    for entry in ctrl._vault_caches.values():
        entry["last_access"] = time.monotonic() - 200.0
    trimmed = ctrl.trim_idle_memory(150.0)
    assert trimmed["evicted_vaults"] == 1
    assert len(ctrl.health()["cached_vaults"]) == 0


def test_control_daemon_ephemeral_worker_supervision_and_duplex_stdio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    bootstrap_config(vault)
    (vault / ".paperforge" / "indexes").mkdir(parents=True, exist_ok=True)

    pushed: list[dict] = []
    ctrl = ControlDaemon(push_sink=pushed.append)

    # Submit a fast ephemeral worker (`upgrade --heal --json`)
    sub = ctrl.submit_job(vault, "upgrade.heal")
    assert sub["accepted"] is True
    job_id = sub["job"]["job_id"]

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        jobs = ctrl.list_jobs(vault=str(vault))
        if not jobs["active"] and any(r["job_id"] == job_id for r in jobs["recent"]):
            break
        time.sleep(0.1)

    jobs_after = ctrl.list_jobs(vault=str(vault))
    finished = next(r for r in jobs_after["recent"] if r["job_id"] == job_id)
    assert finished["status"] == "succeeded"
    assert any(ev["event"] == "task.updated" for ev in pushed)
    assert (vault / ".paperforge" / "indexes" / ".daemon-state.json").is_file()

    # Verify duplex stdio RPC ops (`daemon.health`, `notice.push`, `notice.list`, `shutdown`)
    requests = "\n".join(
        [
            json.dumps({"id": 1, "op": "daemon.health", "vault": str(vault)}),
            json.dumps(
                {
                    "id": 2,
                    "op": "notice.push",
                    "vault": str(vault),
                    "level": "success",
                    "code": "test.ok",
                    "title": "All good",
                }
            ),
            json.dumps({"id": 3, "op": "shutdown"}),
        ]
    ) + "\n"
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(requests))
    monkeypatch.setattr(sys, "stdout", out_buf)
    monkeypatch.setattr(sys, "stderr", err_buf)

    assert serve_stdio(idle_timeout=0, push_events=True) == 0
    frames = [json.loads(line) for line in out_buf.getvalue().splitlines() if line.strip()]
    push_frames = [f for f in frames if "event" in f and "id" not in f]
    rpc_frames = [f for f in frames if "id" in f]
    assert [r["id"] for r in rpc_frames] == [1, 2, 3]
    assert json.loads(rpc_frames[0]["stdout"])["ok"] is True
    assert any(p["event"] == "notice.push" and p["data"]["code"] == "test.ok" for p in push_frames)
