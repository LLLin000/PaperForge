"""Reading graph: which block comes next, with evidence and holds.

Contract
--------
`build_reading_order(regions, refs_by_uid, current_order) -> (order, decisions, holds)`

The function is pure: no mutation of regions, refs or current_order.
"""

from __future__ import annotations

from .model import (
    REGION_COLUMN,
    REGION_CONTAINER,
    REGION_MARGIN,
    RELATION_BEFORE,
    RELATION_HOLD,
    BlockRef,
    OrderDecision,
    Region,
)


def _key(uid: str, refs: dict[str, BlockRef]) -> tuple[float, float, str]:
    """Reading order inside one region.

    Y is quantised into 1%-of-page-height rows before X is compared: labels
    that sit on the same visual row differ by a few pixels in `bbox` (baseline
    jitter), and ordering them by raw Y flips them left-to-right.
    """
    ref = refs[uid]
    bbox = ref.bbox
    if bbox is None:
        return (float("inf"), float("inf"), uid)
    row = round(bbox[1] / max(ref.page_height * 0.01, 1.0))
    return (row, bbox[0], uid)


def _heading(ref: BlockRef) -> bool:
    role = (ref.role or "").lower().replace("-", "_")
    return any(word in role for word in ("heading", "title", "header"))


def build_reading_order(
    regions: list[Region],
    refs_by_uid: dict[str, BlockRef],
    current_order: list[str],
) -> tuple[list[str], list[OrderDecision], list[str]]:
    current_rank = {uid: index for index, uid in enumerate(current_order)}
    # Margin artifacts (running heads, folios) sit at the end of the page path:
    # they are page furniture, not content the reader follows.
    ordered_regions = sorted(
        regions,
        key=lambda region: (region.kind == REGION_MARGIN, region.y_top, region.x_left, region.region_id),
    )

    ambiguous: set[tuple[str, str]] = set()
    columns = [region for region in ordered_regions if region.kind == REGION_COLUMN]
    for left in columns:
        for right in columns:
            if (
                left.x_left >= right.x_left
                or left.y_bottom <= right.y_top
                or right.y_bottom <= left.y_top
            ):
                continue
            band_top = min(left.y_top, right.y_top)
            band_bottom = max(left.y_bottom, right.y_bottom)
            height = band_bottom - band_top
            # Only a column pair that is not top-aligned, or whose left column
            # stops well above the band bottom, leaves the hand-off unclear.
            # Aligned columns with a short left column are still read left first.
            if height > 0 and (
                left.y_top != band_top
                or right.y_top != band_top
            ):
                ambiguous.add((left.region_id, right.region_id))

    order: list[str] = []
    owner: dict[str, Region] = {}
    for region in ordered_regions:
        members = sorted((uid for uid in region.members if uid in refs_by_uid), key=lambda uid: _key(uid, refs_by_uid))
        if region.kind == REGION_CONTAINER and members:
            heading = next((uid for uid in members if _heading(refs_by_uid[uid])), None)
            if heading is not None:
                members.remove(heading)
                members.insert(0, heading)
        for uid in members:
            owner.setdefault(uid, region)
            if uid not in order:
                order.append(uid)

    for left_id, right_id in ambiguous:
        pair_uids = [uid for uid in order if owner[uid].region_id in (left_id, right_id)]
        ranks = {uid: index for index, uid in enumerate(order)}
        pair_uids.sort(key=lambda uid: (current_rank.get(uid, len(current_rank) + ranks[uid]), ranks[uid]))
        pair_set = set(pair_uids)
        for index, uid in zip((i for i, item in enumerate(order) if item in pair_set), pair_uids, strict=True):
            order[index] = uid

    for uid in current_order:
        if uid not in order:
            order.append(uid)

    decisions: list[OrderDecision] = []
    holds: list[str] = []
    for before, after in zip(order, order[1:], strict=False):
        first_region, second_region = owner.get(before), owner.get(after)
        relation, confidence, reason = RELATION_BEFORE, 0.9, "same region with vertical separation"
        if first_region is None or second_region is None:
            confidence, reason = 0.0, "missing region geometry"
            relation = RELATION_HOLD
        elif first_region.region_id == second_region.region_id:
            first_box, second_box = refs_by_uid[before].bbox, refs_by_uid[after].bbox
            if first_box is None or second_box is None:
                relation, confidence, reason = RELATION_HOLD, 0.0, "missing bbox inside the region"
            elif second_box[1] < first_box[1]:
                # Inside one region the order is top-down; a pair that runs
                # upwards means the region itself is mis-shaped.
                relation, confidence, reason = RELATION_HOLD, 0.0, "upward move inside one region"
            else:
                confidence, reason = 0.85, "same region, top-down order"
        elif (
            (first_region.region_id, second_region.region_id) in ambiguous
            or (second_region.region_id, first_region.region_id) in ambiguous
        ):
            relation, confidence, reason = RELATION_HOLD, 0.0, "column continuation is ambiguous"
        elif REGION_MARGIN in (first_region.kind, second_region.kind):
            confidence, reason = 0.6, "page furniture after body content"
        elif first_region.kind == REGION_COLUMN and second_region.kind == REGION_COLUMN:
            confidence, reason = 0.7, "column hand-off supported by band geometry"
        else:
            confidence, reason = 0.8, "cross-region band boundary"
        if relation == RELATION_BEFORE:
            region_confidence = min(first_region.confidence, second_region.confidence)
            if region_confidence < confidence:
                confidence = region_confidence
                reason += f" (region confidence {region_confidence:.2f})"
        decisions.append(OrderDecision(before, after, relation, confidence, reason))
        if relation == RELATION_HOLD:
            for uid in (before, after):
                if uid not in holds:
                    holds.append(uid)
    return order, decisions, holds
