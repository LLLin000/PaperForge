"""Read-only subprocess probes used by the status surfaces.

The collector registers this narrow seam as a disposable snapshot. Keep this
module limited to environment inspection; business commands do not belong
here.
"""
from __future__ import annotations

import subprocess
from collections.abc import Sequence


def run_readonly_probe(command: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    """Run one bounded environment-inspection command without shell access."""
    return subprocess.run(
        command,
        capture_output=True,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
