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
    env["PAPERFORGE_SETUP_TEST_HOLD_SECONDS"] = "10"
    proc = subprocess.Popen(
        [sys.executable, "-m", "paperforge", "--vault", str(tmp_path),
         "setup", "--json", "--skip-checks"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
        # POSIX: put the child in its own session so killpg(proc.pid) targets
        # the child's group; without this the kill was a no-op on Linux and
        # the child ran to completion (rc=0).
        start_new_session=True,
    )
    # Give it a moment to start streaming, then hard-kill.
    time.sleep(0.2)
    killed = False
    if proc.poll() is None:
        killed = True
        try:
            if sys.platform == "win32":
                proc.kill()  # TerminateProcess
            elif hasattr(os, "killpg"):
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            killed = False
        try:
            stdout, _stderr = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, _stderr = proc.communicate(timeout=30)
    else:
        stdout, _stderr = proc.communicate(timeout=30)

    assert proc.returncode != 0, (proc.returncode, stdout[-500:])
    # Only a genuinely killed run proves the honest-terminal contract; a
    # process that exited on its own is not an injection and cannot be
    # claimed as one. Require that we actually drove the kill.
    assert killed, "child exited before injection; race not exercised"

    assert proc.returncode != 0, "hard-killed child must not report success"
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line).get("event"))
        except json.JSONDecodeError:
            continue
    # A fake success terminal would be `result`; a crash must not emit one.
    assert "result" not in events, events
