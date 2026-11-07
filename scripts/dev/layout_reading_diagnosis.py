"""Explain why accepted layout orders do or do not change emitted reading order."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SCOPE_BLOCKED_ROLES = frozenset({
    "reference_heading", "reference_item", "backmatter_heading", "backmatter_body",
    "backmatter_heading_candidate", "table_html", "structured_insert", "non_body_insert",
})
CATEGORIES = ("already_correct", "gate_blocked", "scope_blocked", "non_emitting_only", "real_change_candidate")


def _identity(block: dict) -> tuple[Any, ...]:
    return (int(block.get("page", 0) or 0), str(block.get("block_id")), tuple(block.get("bbox") or ()))


def _event_ids(events: list[dict], blocks_by_page: dict[int, list[dict]]) -> dict[int, list[tuple[Any, ...]]] | None:
    """Map events to block identities; ambiguous block_id matches are undetermined."""
    result: dict[int, list[tuple[Any, ...]]] = {}
    for event in events:
        page = int(event.get("page", 0) or 0)
        matches = [b for b in blocks_by_page.get(page, []) if str(b.get("block_id")) == str(event.get("block_id"))]
        if len(matches) != 1:
            return None
        result.setdefault(page, []).append(_identity(matches[0]))
    return result


def classify_pages(blocks: list[dict], plan, acceptance: list, emitted_events: list[dict]) -> list[dict]:
    """Pure page attribution. Plan UIDs are bridged to input indices via refs.

    Acceptance only supplies `source_mapping` for accepted pages; a rejected
    page still has a plan order, and the point of `gate_blocked` is to compare
    that order with the renderer's input order.
    """
    from paperforge.worker.layout.plan import collect_block_refs

    uid_to_index = {ref.uid: ref.raw_index for ref in collect_block_refs(blocks)}
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)
    events_by_page = _event_ids(emitted_events, by_page)
    accepted = {item.page: item for item in acceptance}
    plan_pages = {item.page: item for item in plan.pages}
    output = []
    for page_num in sorted(set(by_page) | set(plan_pages)):
        page_blocks = by_page.get(page_num, [])
        gate = accepted.get(page_num)
        page_plan = plan_pages.get(page_num)
        fallback_mapping = gate.source_mapping if gate is not None else {}

        def _index_of(uid: str, mapping: dict = fallback_mapping) -> int | None:
            if uid in uid_to_index:
                return uid_to_index[uid]
            # Synthetic plans in tests carry their own uid mapping.
            return mapping.get(uid)

        mapped = []
        if page_plan:
            mapped = [index for uid in page_plan.order if (index := _index_of(uid)) is not None]
        input_indices = [i for i, block in enumerate(blocks) if int(block.get("page", 0) or 0) == page_num]
        plan_differs = bool(mapped) and mapped != input_indices
        scope_reason = ""
        if page_plan and any(region.kind == "container" for region in page_plan.regions):
            scope_reason = "container_region"
        else:
            for block in page_blocks:
                if (block.get("role") or "") in _SCOPE_BLOCKED_ROLES:
                    scope_reason = f"role:{block.get('role')}"
                    break
                if block.get("_object_owner_id"):
                    scope_reason = "object_owner"
                    break
                if block.get("_container_text"):
                    scope_reason = "box_container"
                    break
        fallback = getattr(gate, "fallback_reason", None) if gate else None
        if not plan_differs:
            # No order change to make: the gate's verdict is irrelevant here.
            category = "already_correct"
        elif not gate or not gate.accepted:
            category = "gate_blocked"
        elif scope_reason:
            category = "scope_blocked"
        elif events_by_page is None:
            category = "UNDETERMINED"
        else:
            input_ids = [_identity(blocks[i]) for i in input_indices]
            plan_ids = [_identity(blocks[i]) for i in mapped]
            emitted = events_by_page.get(page_num, [])
            emitted_set = set(emitted)
            plan_emitted = [identity for identity in plan_ids if identity in emitted_set]
            input_emitted = [identity for identity in input_ids if identity in emitted_set]
            category = "non_emitting_only" if plan_emitted == input_emitted else "real_change_candidate"
        changed_pairs = sum(1 for a, b in zip(mapped, input_indices, strict=False) if a != b) if plan_differs else 0
        rows = page_blocks
        output.append({
            "page": page_num, "category": category, "fallback_reason": fallback,
            "changed_pair_count": changed_pairs,
            "held_blocks": list(getattr(gate, "held_blocks", []) or []) if gate else [],
            "evidence": getattr(gate, "evidence", {}) if gate else {},
            "scope_reason": scope_reason or None,
            "blocks": [{"block_id": b.get("block_id"), "bbox": b.get("bbox"),
                        "text_snippet": str(b.get("text", ""))[:200]} for b in rows],
        })
    return output


def diagnose(paper_dir: Path, thresholds: tuple[float, ...] = ()) -> dict[str, Any] | None:
    from layout_shadow_render import _render, load_final_blocks

    from paperforge.worker.layout.acceptance import assess_plan
    from paperforge.worker.layout.plan import build_layout_plan

    if not (paper_dir / "canonical" / "blocks.raw.jsonl").is_file():
        return None
    blocks, metadata, document, figures, tables, reader = load_final_blocks(paper_dir)
    plan = build_layout_plan(blocks)
    baseline = _render(copy.deepcopy(blocks), metadata, document, figures, tables, reader, None)
    reports = []
    for threshold in (0.80, *thresholds):
        acceptance = assess_plan(plan, blocks, min_confidence=threshold)
        pages = classify_pages(blocks, plan, acceptance, baseline.emitted_block_events)
        counts = dict(sorted(Counter(p["category"] for p in pages).items()))
        report = {"threshold": threshold, "pages": pages, "counts": counts}
        if threshold != 0.80:
            report["diagnostic"] = True
        reports.append(report)
    return {"key": paper_dir.name, "pages": reports[0]["pages"], "counts": reports[0]["counts"],
            "diagnostics": reports[1:]}

def _markdown(papers: list[dict], categories: dict[str, int]) -> str:
    lines = ["| key | " + " | ".join(CATEGORIES) + " |", "|---|" + "---:|" * len(CATEGORIES)]
    for paper in papers:
        counts = " | ".join(str(paper["counts"].get(category, 0)) for category in CATEGORIES)
        lines.append(f"| {paper['key']} | {counts} |")
    lines.extend(["", "Real-change candidates:"])
    for paper in papers:
        for page in paper["pages"]:
            if page["category"] == "real_change_candidate":
                details = "; ".join(
                    f"{block['block_id']}: {block['text_snippet']}" for block in page["blocks"]
                )
                lines.append(f"- {paper['key']} page {page['page']}: {details}")
    lines.append("\nTotals: " + json.dumps(categories, sort_keys=True))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--keys-file", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--diagnostic", action="append", type=float, default=[])
    args = parser.parse_args(argv)
    keys = list(args.keys or [])
    if args.keys_file is not None:
        keys.extend(args.keys_file.read_text(encoding="utf-8").split())
    if not keys:
        parser.error("provide --keys and/or --keys-file")
    if args.limit is not None:
        keys = keys[:max(0, args.limit)]
    papers = [value for key in keys if (value := diagnose(args.vault / key, tuple(args.diagnostic))) is not None]
    totals = dict(sorted(Counter(page["category"] for paper in papers for page in paper["pages"]).items()))
    payload = {"papers": papers, "totals": totals, "categories": list(CATEGORIES)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(papers, totals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
