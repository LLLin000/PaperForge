"""#137 unified cooperative cancellation token.

One cancellation state machine per process; two ingress paths into the same
flag:

- Controller-owned process: stdin ``PAPERFORGE_STOP\\n``
- Terminal user: SIGINT / SIGTERM

Retired with #137: the cross-process ``paperforge embed stop`` control
sidecar contract — stdin cannot reach another process's child.  Orphaned
processes are hard-terminated only.

Safe points are the caller's responsibility (between items, between phases,
before expensive remote calls, before the publication commit — never inside
an atomic publish/transaction).
"""

from __future__ import annotations

import signal
import sys
import threading
from collections.abc import Callable

STOP_TOKEN = "PAPERFORGE_STOP\n"


def make_cancellation_token() -> tuple[Callable[[], bool], Callable[[], None]]:
    """Install one cooperative stop flag fed by stdin + SIGINT + SIGTERM.

    Returns ``(is_stopped, restore)``.  ``is_stopped`` polls the flag;
    ``restore`` uninstalls handlers and stops the stdin reader thread.
    """
    flag: list[bool] = [False]
    active: list[bool] = [True]

    def _set_stopped(*_args) -> None:
        flag[0] = True

    def _stdin_reader() -> None:
        try:
            # Blocking read; the daemon thread ends when the stream closes.
            for line in sys.stdin:
                if line == STOP_TOKEN:
                    flag[0] = True
        except Exception:  # noqa: BLE001 — stdin unavailable in testing/headless
            pass
        finally:
            active[0] = False

    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _set_stopped)
    signal.signal(signal.SIGTERM, _set_stopped)

    reader = threading.Thread(target=_stdin_reader, daemon=True)
    reader.start()

    def restore() -> None:
        if not active[0]:
            return
        active[0] = False
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)

    return (lambda: flag[0], restore)
