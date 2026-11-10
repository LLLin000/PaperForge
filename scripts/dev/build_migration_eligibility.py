#!/usr/bin/env python
"""Build the migration eligibility overlay from R1 statuses + R2e holds."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r1", default=str(REPO / "docs/evidence/r1/papers.json"))
    ap.add_argument("--r2e", default=str(REPO / "docs/evidence/r2-audit/content-r2e.json"))
    ap.add_argument("--out", default=str(REPO / "docs/evidence/r2-audit/migration-eligibility.json"))
    ap.add_argument("--resolved", default=str(REPO / "docs/evidence/r2-audit/r2f-resolution.json"))
    args = ap.parse_args()

    r1 = json.loads(Path(args.r1).read_text(encoding="utf-8"))
    base = r1.get("status", r1)
    content = json.loads(Path(args.r2e).read_text(encoding="utf-8"))
    resolved = set()
    resolved_path = Path(args.resolved)
    if resolved_path.is_file():
        resolved = set(json.loads(resolved_path.read_text(encoding="utf-8")).get("resolved", []))
    holds = sorted(
        r["key"] for r in content["results"]
        if r["verdict"] == "HOLD" and r["key"] not in resolved
    )
    status = dict(base)
    for key in holds:
        status[key] = "TEXT_FIDELITY_HOLD"
    out = {
        "schema": "paperforge.migration_eligibility.v1",
        "base": "docs/evidence/r1/papers.json",
        "overlay": "docs/evidence/r2-audit/content-r2e.json",
        "status": dict(sorted(status.items())),
        "status_counts": dict(sorted(Counter(status.values()).items())),
        "text_fidelity_hold": holds,
        "note": "TEXT_FIDELITY_HOLD overrides READY; do not migrate these papers until R2f clears them.",
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"papers": len(status), "holds": len(holds), "counts": out["status_counts"]}))


if __name__ == "__main__":
    main()
