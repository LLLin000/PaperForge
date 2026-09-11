"""Filesystem writability probe.

A report surface needs to answer "can this process write here?" without
becoming a writer itself. Creating the directory to find out is not a probe: it
is a durable mutation of the canonical tree performed by a command whose job is
to report (see the query-side-effect rule in the architecture contract, #221).

The probe therefore:

- returns False when the directory is absent, and creates nothing — the caller
  reports the missing directory rather than silently repairing it;
- when the directory exists, creates one uniquely named file inside it, removes
  it, and returns whether that succeeded. That is a disposable write by
  construction, and the collector attributes it as such through the registered
  wrapper ``fs_probe.probe_writable``
  (``architecture_audit/collectors/common.py``).
"""
from __future__ import annotations

import contextlib
import os
import uuid
from pathlib import Path


def probe_writable(directory: Path) -> bool:
    """True when a file can be created and removed inside an existing directory.

    Never creates the directory: absence is reported as not-writable, so a
    reporting command cannot leave a trace in the vault.
    """
    if not directory.is_dir():
        return False
    candidate = directory / f".pf-write-probe-{uuid.uuid4().hex[:12]}"
    try:
        with open(candidate, "w", encoding="utf-8") as handle:
            _ = handle.write("ok")
        return True
    except OSError:
        return False
    finally:
        with contextlib.suppress(OSError):
            os.unlink(candidate)
