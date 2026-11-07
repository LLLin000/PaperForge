"""Metrics for reviewing a layout plan against the current OCR output.

Contract
--------
`evaluate_plan(plan, blocks, figure_inventory=None, table_inventory=None) -> dict`

The result is a JSON-serialisable dict. Required keys:

- `pages`, `blocks`
- `coverage`: `{covered, unique, duplicated, missing}` — every block must be
  described exactly once
- `pair_inversions`: adjacent pairs in the plan order that run backwards in
  the current OCR order, with the pair uids
- `holds`: hold count and ratio
- `conflicts`: counts by kind and by severity
- `figure_caption`: `{matched, suspicious}` when an inventory is supplied

`evaluate_plan` is read-only; it must not mutate the plan or the blocks.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .model import REGION_MARGIN, LayoutPlan
from .plan import collect_block_refs


def evaluate_plan(
    plan: LayoutPlan,
    blocks: list[dict],
    figure_inventory: dict | None = None,
    table_inventory: dict | None = None,
) -> dict[str, Any]:
    refs = collect_block_refs(blocks)
    raw_order = {ref.uid: ref.raw_index for ref in refs}
    membership = Counter(uid for page in plan.pages for region in page.regions for uid in region.members)
    expected = {ref.uid for ref in refs}
    covered = sum(membership.values())  # membership entries, so duplicates stay visible
    unique = sum(1 for uid in expected if membership[uid] == 1)
    duplicated = sum(1 for uid in expected if membership[uid] > 1)
    missing = sum(1 for uid in expected if membership[uid] == 0)

    margin_uids = {
        uid
        for page in plan.pages
        for region in page.regions
        if region.kind == REGION_MARGIN
        for uid in region.members
    }
    inversions = []
    for page in plan.pages:
        for before, after in zip(page.order, page.order[1:], strict=False):
            if before in margin_uids or after in margin_uids:
                continue
            if before in raw_order and after in raw_order and raw_order[before] > raw_order[after]:
                inversions.append({"page": page.page, "before": before, "after": after})

    conflict_kinds = Counter(conflict.kind for page in plan.pages for conflict in page.conflicts)
    conflict_severities = Counter(conflict.severity for page in plan.pages for conflict in page.conflicts)
    hold_count = sum(len(page.holds) for page in plan.pages)
    block_count = len(refs)
    result: dict[str, Any] = {
        "pages": len(plan.pages),
        "blocks": block_count,
        "margin_blocks": len(margin_uids),
        "coverage": {
            "covered": covered,
            "unique": unique,
            "duplicated": duplicated,
            "missing": missing,
            "margin": len(margin_uids),
        },
        "pair_inversions": inversions,
        "holds": {"count": hold_count, "ratio": hold_count / block_count if block_count else 0.0},
        "conflicts": {
            "by_kind": dict(sorted(conflict_kinds.items())),
            "by_severity": dict(sorted(conflict_severities.items())),
            "total": sum(conflict_kinds.values()),
        },
    }
    if figure_inventory is not None:
        region_for: dict[str, tuple[str, str | None]] = {}
        page_height = {page.page: page.height for page in plan.pages}
        for page in plan.pages:
            for region in page.regions:
                for uid in region.members:
                    region_for[uid] = (region.region_id, region.parent_id)
        uid_by_block = {(ref.page, ref.block_id): ref.uid for ref in refs}
        matched = 0
        suspicious = []
        for figure in figure_inventory.get("matched_figures", []):
            caption_block = figure.get("legend_block_id", figure.get("block_id", ""))
            caption_uid = uid_by_block.get((int(figure.get("page", 0) or 0), str(caption_block)))
            if caption_uid is None:
                continue
            for asset in figure.get("matched_assets", figure.get("assets", [])):
                asset_page = int(asset.get("page", figure.get("page", 0)) or 0)
                asset_uid = uid_by_block.get((asset_page, str(asset.get("block_id", ""))))
                if asset_uid is None:
                    continue
                matched += 1
                cap_region = region_for.get(caption_uid)
                asset_region = region_for.get(asset_uid)
                if cap_region is None or asset_region is None or cap_region != asset_region:
                    continue
                cap = next((ref for ref in refs if ref.uid == caption_uid), None)
                ast = next((ref for ref in refs if ref.uid == asset_uid), None)
                height = page_height.get(asset_page, 0.0)
                if cap and ast and cap.bbox and ast.bbox and height > 0:
                    cap_y = (cap.bbox[1] + cap.bbox[3]) / 2
                    asset_y = (ast.bbox[1] + ast.bbox[3]) / 2
                    ratio = abs(cap_y - asset_y) / height
                    if ratio > 0.02:
                        suspicious.append(
                            {
                                "page": asset_page,
                                "caption": caption_uid,
                                "asset": asset_uid,
                                "caption_bbox": list(cap.bbox),
                                "asset_bbox": list(ast.bbox),
                                "distance_ratio": round(ratio, 4),
                            }
                        )
        result["figure_caption"] = {"matched": matched, "suspicious": suspicious}
    if table_inventory is not None:
        result["table_inventory"] = {"tables": len(table_inventory.get("tables", []))}
    return result
