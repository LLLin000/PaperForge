#!/usr/bin/env python3
"""Differential audit: compare existing block_review.jsonl truth against current pipeline output.

Identifies blocks where pipeline role/zone now matches or still differs from human truth.
Marks resolved entries and flags blocks needing re-audit. Updates block_review.jsonl in-place.

Usage:
    python diff_audit.py <KEY> --source-root D:/path/to/ocr [--audit-root D:/path/to/audit]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from paperforge.worker.ocr_artifacts import artifact_paths_for_root

# Canonical role map: alias → pipeline output role name.
_CANONICAL_ROLE = {
    "media_asset": "figure_asset",
    "structural_noise": "noise",
    "author_list": "authors",
    "running_header": "noise",
    "page_marker": "noise",
    "frontmatter_metadata": "frontmatter_noise",
    "separator": "noise",
}


def _canonical(role: str) -> str:
    return _CANONICAL_ROLE.get(role, role)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Diff audit: compare truth roles with current pipeline")
    ap.add_argument("key")
    ap.add_argument("--source-root", dest="source_root", required=True)
    ap.add_argument("--audit-root", dest="audit_root", default=None)
    args = ap.parse_args()

    source_root = Path(args.source_root)
    audit_root = Path(args.audit_root) if args.audit_root else Path("audit")
    paper_audit = audit_root / args.key
    review_path = paper_audit / "block_review.jsonl"
    changed_path = paper_audit / "changed_blocks_after_fallback.json"

    reviews = _load_jsonl(review_path)
    if not reviews:
        print(f"No block_review.jsonl at {review_path} — nothing to diff.")
        return

    artifacts = artifact_paths_for_root(source_root, args.key)
    if not artifacts.blocks_structured.exists():
        print(f"ERROR: No structured blocks at {artifacts.blocks_structured}")
        sys.exit(1)

    structured = _load_jsonl(artifacts.blocks_structured)

    # Index structured by key
    struct_by_key: dict[str, dict] = {}
    for block in structured:
        page = block.get("page", 0)
        bid = block.get("block_id")
        if page is None or bid is None:
            continue
        key = f"p{page}:{bid}"
        struct_by_key[key] = block

    matches_truth = 0
    needs_reaudit = 0
    changed_items: list[dict] = []

    for review in reviews:
        bid = review.get("block_id", "")
        truth_role = review.get("truth_role", "")
        truth_zone = review.get("truth_zone", "")
        current = struct_by_key.get(bid)
        if not current:
            continue

        pipe_role = current.get("role", "")
        pipe_zone = current.get("zone", "")
        pipe_text_len = len(str(current.get("text", "")).strip())

        role_match = _canonical(pipe_role) == _canonical(truth_role)
        zone_match = not truth_zone or pipe_zone == truth_zone

        if role_match:
            review["_pipeline_verified"] = True
            review["_current_role"] = pipe_role
            matches_truth += 1
        else:
            review["_needs_reaudit"] = True
            review["_current_role"] = pipe_role
            review["_current_zone"] = pipe_zone
            needs_reaudit += 1

        changed_items.append({
            "block_id": bid,
            "truth_role": truth_role,
            "pipe_role": pipe_role,
            "pipe_zone": pipe_zone,
            "pipe_text_len": pipe_text_len,
            "role_match": role_match,
            "zone_match": zone_match,
        })

    # Write summary
    summary = {
        "paper": args.key,
        "total_reviewed": len(reviews),
        "pipeline_verified": matches_truth,
        "need_reaudit": needs_reaudit,
        "changed_blocks": changed_items,
    }
    changed_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Normalize truth_role to canonical form in place, so future diffs
    # match even without the alias map.
    for review in reviews:
        raw = str(review.get("truth_role") or "")
        canonical = _canonical(raw)
        if canonical != raw:
            review["truth_role"] = canonical

    # Write back updated block_review.jsonl
    _write_jsonl(review_path, reviews)

    print(f"Paper: {args.key}")
    print(f"  Total reviewed: {len(reviews)}")
    print(f"  Pipeline verified (role matches truth): {matches_truth}")
    print(f"  Need re-audit (role still wrong): {needs_reaudit}")
    print(f"Written: {changed_path}")
    print(f"Updated: {review_path}")


if __name__ == "__main__":
    main()
