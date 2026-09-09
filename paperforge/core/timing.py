"""Phase timing for CLI diagnostics.

Contract: timing NEVER touches stdout — stdout is the machine protocol
(PFResult / NDJSON). Records go to stderr, and into ``data["timing"]`` when a
command opts in (sync does).

Emission policy (the "sync is sometimes very slow" workflow):
- unset env: only phases slower than ``SLOW_MS`` (1s) are printed;
- ``PAPERFORGE_TIMING=1``: every phase is printed;
- ``PAPERFORGE_TIMING=0``: nothing is printed (records still collected).
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager

SLOW_MS = 1000.0

_records: list[tuple[str, float]] = []
_command: str = ""
_started: float = 0.0


def _verbose() -> bool:
    return os.environ.get("PAPERFORGE_TIMING", "").strip() == "1"


def _silent() -> bool:
    return os.environ.get("PAPERFORGE_TIMING", "").strip() == "0"


def reset() -> None:
    global _started
    _records.clear()
    _started = time.perf_counter()


def set_command(command: str) -> None:
    global _command
    _command = command


@contextmanager
def phase(name: str) -> Iterator[None]:
    """Time one phase; emit a stderr line when verbose or slow."""
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        _records.append((name, elapsed_ms))
        if not _silent() and (_verbose() or elapsed_ms >= SLOW_MS):
            print(f"[PF:time] {name} {elapsed_ms:.0f}ms", file=sys.stderr)


def summary() -> dict[str, float]:
    """Phase name → milliseconds (later duplicates overwrite)."""
    return {name: round(ms, 1) for name, ms in _records}


def total_ms() -> float:
    """Command wall clock — nested phases must not double-count."""
    if not _started:
        return round(sum(ms for _, ms in _records), 1)
    return round((time.perf_counter() - _started) * 1000.0, 1)


def emit_total(command: str | None = None) -> None:
    """One line per command invocation (same verbose/slow policy)."""
    total = total_ms()
    if not _records or _silent():
        return
    name = command or _command or "?"
    if _verbose() or total >= SLOW_MS:
        print(f"[PF:time] command={name} total={total:.0f}ms", file=sys.stderr)
