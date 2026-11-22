"""paperforge.__main__ — entry point for `python -m paperforge`."""

import os
import sys
import threading
import time
import traceback

from paperforge.cli import main


def _start_parent_watchdog() -> None:
    """Self-terminate managed worker if its supervising parent daemon dies unexpectedly.

    Provides belt-and-suspenders orphan protection across macOS/Linux/Windows
    alongside OS-level Job Objects (Windows), PR_SET_PDEATHSIG (Linux), and
    kqueue EVFILT_PROC reaper (macOS).
    """
    raw = os.environ.get("PAPERFORGE_PARENT_PID", "").strip()
    if not raw.isdigit():
        return
    parent_pid = int(raw)
    if parent_pid <= 1 or parent_pid == os.getpid():
        return

    initial_ppid = os.getppid() if hasattr(os, "getppid") else None

    def _watch() -> None:
        while True:
            time.sleep(0.5)
            if initial_ppid == parent_pid and hasattr(os, "getppid"):
                if os.getppid() != parent_pid:
                    os._exit(143)
            if os.name != "nt":
                try:
                    os.kill(parent_pid, 0)
                except ProcessLookupError:
                    os._exit(143)
                except PermissionError:
                    pass

    t = threading.Thread(target=_watch, name="pf-parent-watchdog", daemon=True)
    t.start()


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    _start_parent_watchdog()
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — transport contract: never rc 0 silently
        # CLI transport contract (#130 review P0): an unhandled exception must
        # never surface as "exit 0 with empty/non-JSON stdout" — machine
        # callers (plugin, agent, probe, automation) treat rc 0 as success.
        traceback.print_exc(file=sys.stderr)
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
