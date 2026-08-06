#!/usr/bin/env python3
"""Architecture audit report renderer (thin wrapper, #134).

Delegates to the canonical projection module
`paperforge.architecture_audit.report.render_html`. This file exists so the
live report directory keeps one obvious regenerate command; the HTML itself is
a disposable ArchitectureReportView, never architecture truth.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    sys.path.insert(0, str(HERE.parent.parent))
    from paperforge.architecture_audit.report.render_html import main as canonical_main

    return canonical_main(["--dir", str(HERE), "--out", str(HERE / "index.html")])


if __name__ == "__main__":
    raise SystemExit(main())
