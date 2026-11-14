"""Derive migration eligibility from the reattribution Census and the human review pack.

Read-only and fail-closed. A paper is READY only when the rebuilt delivery is clean,
the source identity matches, and a human review sheet for that exact snapshot has been
completed. The historical 596-HOLD overlay is never applied here; production migration
stays blocked regardless of the counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CENSUS = ROOT / "docs" / "evidence" / "r3-reattribution" / "reattribution-census.json"
DEFAULT_PACK = ROOT / "docs" / "evidence" / "r3-review-pack" / "index.json"
DEFAULT_OUT = ROOT / "docs" / "evidence" / "r3-reattribution" / "migration-eligibility.json"

DELIVERY_CLEAN = {
    "REBUILT_STRUCTURALLY_RESOLVED", "LEGACY_BACKLOG_RESOLVED", "FALSE_FIGURE_CANDIDATE",
}

PENDING_EVIDENCE_CLASSES = {
    "REBUILD_ERROR_UNASSESSED", "REBUILD_EVIDENCE_INCOMPLETE", "UNASSESSED_IDENTITY_DRIFT",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def derive(census_path: Path, pack_path: Path) -> dict[str, Any]:
    census = _read_json(census_path)
    pack = _read_json(pack_path) if pack_path.is_file() else {"papers": []}
    pack_matches_census = pack.get("source_census_sha256") == _sha256(census_path)
    reviewed = {
        row["key"]: row for row in pack.get("papers", [])
        if row.get("review_status") == "REVIEWED"
    } if pack_matches_census else {}
    papers = census.get("papers", [])
    target_keys = set(census.get("selection", {}).get("target_keys", []))

    status: dict[str, str] = {}
    reasons: dict[str, list[str]] = {}
    for paper in papers:
        key = paper["key"]
        rebuilt = paper.get("rebuilt_state", {})
        state = rebuilt.get("status")
        classification = paper.get("classification")
        if key not in target_keys:
            status[key] = "PENDING_REBUILD"
            reasons[key] = ["not_in_replay_plan"]
            continue
        if state != "REPLAYED":
            status[key] = "HOLD" if state == "SOURCE_MISMATCH" else "PENDING_EVIDENCE"
            reasons[key] = [f"rebuilt_state={state}"]
            continue
        if classification not in DELIVERY_CLEAN:
            status[key] = (
                "PENDING_EVIDENCE" if classification in PENDING_EVIDENCE_CLASSES else "HOLD"
            )
            reasons[key] = [f"classification={classification}"]
            continue
        if not pack_matches_census:
            status[key] = "VISUAL_REVIEW_PENDING"
            reasons[key] = ["review_pack_census_mismatch"]
            continue
        review = reviewed.get(key)
        if review is None:
            status[key] = "VISUAL_REVIEW_PENDING"
            reasons[key] = ["no_matching_human_review"]
            continue
        if (
            review.get("snapshot_fingerprint") != rebuilt.get("snapshot_fingerprint")
            or review.get("source_pdf_sha256") != rebuilt.get("source_pdf_sha256")
        ):
            status[key] = "VISUAL_REVIEW_PENDING"
            reasons[key] = ["review_binding_mismatch"]
            continue
        if review.get("review_outcome") == "FAIL":
            status[key] = "HOLD"
            reasons[key] = ["visual_review_failed"]
            continue
        if review.get("review_outcome") != "PASS":
            status[key] = "VISUAL_REVIEW_PENDING"
            reasons[key] = ["visual_review_incomplete"]
            continue
        status[key] = "READY_CANDIDATE"
        reasons[key] = []

    counts: dict[str, int] = {}
    for state in status.values():
        counts[state] = counts.get(state, 0) + 1

    return {
        "schema": "paperforge.reattribution_migration_eligibility.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "reattribution_census": str(census_path),
            "reattribution_census_sha256": _sha256(census_path),
            "review_pack": str(pack_path) if pack_path.is_file() else None,
            "review_pack_sha256": _sha256(pack_path) if pack_path.is_file() else None,
        },
        "gates": {
            "historical_596_hold_overlay_applied": False,
            "visual_pass_inferred_from_delivery_state": False,
            "review_required_for_ready": True,
            "visual_review_authority": pack.get("review_authority", "none"),
            "human_signoff_present": bool(pack.get("human_review_conducted")),
            "production_migration_authorized": False,
            "production_migration_blocked_reason": (
                "Requires a completed visual review bound to each READY candidate's snapshot, "
                "resolution of source-identity mismatches, and separate user authorization."
            ),
        },
        "status": status,
        "reasons": reasons,
        "counts": counts,
        "ready_count": counts.get("READY_CANDIDATE", 0),
        "production_migration_ready_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", default=str(DEFAULT_CENSUS))
    parser.add_argument("--pack", default=str(DEFAULT_PACK))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    eligibility = derive(Path(args.census), Path(args.pack))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(eligibility, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(eligibility["counts"], ensure_ascii=False))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
