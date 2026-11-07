"""Plan assembly: blocks in, read-only layout plan out.

This is the only public entry point of the layout package. It composes the
three concerns — region tree, reading graph, conflict detection — and never
mutates the input blocks or writes anything to disk.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .conflicts import detect_conflicts
from .model import BlockRef, LayoutPlan, PagePlan, block_fingerprint
from .reading import build_reading_order
from .regions import build_region_tree

_TINY_TEXT = 0


def _bbox_tuple(block: dict) -> tuple[float, float, float, float] | None:
    bbox = block.get("bbox") or block.get("block_bbox") or []
    if len(bbox) < 4:
        return None
    try:
        left, top, right, bottom = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except (TypeError, ValueError):
        return None
    if right < left or bottom < top:
        return None
    return (left, top, right, bottom)


def _page_size(blocks: Iterable[dict]) -> tuple[float, float]:
    width = 0.0
    height = 0.0
    for block in blocks:
        width = max(width, float(block.get("page_width") or 0.0))
        height = max(height, float(block.get("page_height") or 0.0))
    return width, height


def collect_block_refs(blocks: list[dict]) -> list[BlockRef]:
    """Turn OCR blocks into stable, geometry-keyed references.

    The input order is recorded as `raw_index` evidence only. Identity (`uid`)
    comes from a geometric sort, so shuffling `blocks` cannot change it.
    """
    by_page: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for raw_index, block in enumerate(blocks):
        try:
            page = int(block.get("page", 0) or 0)
        except (TypeError, ValueError):
            page = 0
        by_page[page].append((raw_index, block))

    refs: list[BlockRef] = []
    for page in sorted(by_page):
        entries = by_page[page]
        width, height = _page_size(block for _, block in entries)

        def sort_key(entry: tuple[int, dict]) -> tuple[float, float, str, str]:
            _, block = entry
            bbox = _bbox_tuple(block)
            y_top = bbox[1] if bbox else float("inf")
            x_left = bbox[0] if bbox else float("inf")
            text = str(block.get("text") or "")
            digest = hashlib.sha1(f"{block.get('role')}|{text}".encode()).hexdigest()[:12]
            return (y_top, x_left, str(block.get("block_id") or ""), digest)

        ordered = sorted(entries, key=sort_key)
        for position, (raw_index, block) in enumerate(ordered):
            text = str(block.get("text") or "")
            bbox = _bbox_tuple(block)
            block_id = str(block.get("block_id") or "")
            refs.append(
                BlockRef(
                    uid=f"p{page}:{position:04d}",
                    page=page,
                    block_id=block_id,
                    bbox=bbox,
                    raw_index=raw_index,
                    role=block.get("role"),
                    text_len=len(text.strip()),
                    page_width=width,
                    page_height=height,
                    fingerprint=block_fingerprint(
                        page,
                        block_id,
                        bbox,
                        block.get("role"),
                        text,
                        render_default=block.get("render_default"),
                        index_default=block.get("index_default"),
                        owner_id=block.get("_object_owner_id"),
                    ),
                )
            )
    return refs


def build_layout_plan(blocks: list[dict]) -> LayoutPlan:
    """Build a read-only layout plan for every page present in `blocks`."""
    refs = collect_block_refs(blocks)
    refs_by_uid = {ref.uid: ref for ref in refs}
    pages: list[BlockRef] = sorted(refs, key=lambda ref: ref.page)
    page_numbers = sorted({ref.page for ref in pages})

    plan = LayoutPlan()
    stats: dict[str, Any] = {
        "blocks": len(refs),
        "pages": len(page_numbers),
        "regions": 0,
        "containers": 0,
        "holds": 0,
        "conflicts": 0,
        "tiny_text_blocks": sum(1 for ref in refs if ref.text_len <= _TINY_TEXT),
    }

    for page in page_numbers:
        page_refs = [ref for ref in pages if ref.page == page]
        width = max((ref.page_width for ref in page_refs), default=0.0)
        height = max((ref.page_height for ref in page_refs), default=0.0)
        # Evidence: the order the OCR layer produced, kept for comparison only.
        current_order = [ref.uid for ref in sorted(page_refs, key=lambda ref: ref.raw_index)]

        regions = build_region_tree(page_refs, page)
        order, decisions, holds = build_reading_order(regions, refs_by_uid, current_order)
        conflicts = detect_conflicts(regions, refs_by_uid, order, current_order)

        plan.pages.append(
            PagePlan(
                page=page,
                width=width,
                height=height,
                regions=regions,
                order=order,
                holds=holds,
                decisions=decisions,
                conflicts=conflicts,
            )
        )
        stats["regions"] += len(regions)
        stats["containers"] += sum(1 for region in regions if region.kind == "container")
        stats["holds"] += len(holds)
        stats["conflicts"] += len(conflicts)

    plan.stats = stats
    plan.identities = {ref.uid: ref.fingerprint for ref in refs}
    return plan
