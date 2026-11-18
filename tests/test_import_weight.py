"""P0 import-weight guard: ``paperforge.worker.ocr`` must stay lazily loaded.

The OCR worker keeps 20+ imports function-level so Windows multiprocessing
spawn does not pay for (or break on) heavy distributions. This test imports
the module in a clean subprocess and asserts the lazily-held distributions
were not pulled in eagerly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Distributions that must NOT be in sys.modules after importing the worker.
LAZY_HEAVIES = ("torch", "chromadb", "pdfplumber", "fitz", "pymupdf", "PIL")


def test_worker_ocr_import_stays_light() -> None:
    names = ", ".join(repr(name) for name in LAZY_HEAVIES)
    code = (
        "import sys, paperforge.worker.ocr; "
        f"heavy = [m for m in ({names},) if m in sys.modules]; "
        "assert not heavy, f'eager heavy imports pulled by paperforge.worker.ocr: {heavy}'"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
