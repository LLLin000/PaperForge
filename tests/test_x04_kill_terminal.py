"""X04 — hard-kill during a long task never yields a fake success terminal."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


def test_X04_hard_killed_setup_emits_no_success_terminal(tmp_path: Path) -> None:
    """Injection point: SIGKILL/TerminateProcess of the child mid-run.

    Grace period is ~1s; the run must NOT fabricate a `result` terminal
    on stdout (the LongTaskClient contract). Residual gap: hard-kill timing
    means we assert absence-of-success, not a specific cancel terminal."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path.cwd())
    proc = subprocess.Popen(
        [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
         "setup", "--json", "--skip-checks"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    # Give it a moment to start streaming, then hard-kill.
    time.sleep(0.2)
    if sys.platform == "win32":
        proc.kill()  # TerminateProcess
    else:
        os.killpg(proc.pid, signal.SIGKILL) if hasattr(os, "killpg") else proc.kill()
    try:
        stdout, _stderr = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _stderr = proc.communicate(timeout=30)

    assert proc.returncode != 0, "hard-killed child must not report success"
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line).get("event"))
        except json.JSONDecodeError:
            continue
    # A fake success terminal would be `result`; a crash must not emit one.
    assert "result" not in events, events
