"""Conflict detection: name every place where the layout is not trustworthy.

Contract
--------
`detect_conflicts(regions, refs_by_uid, order, current_order) -> list[Conflict]`

Conflict kinds are defined in `paperforge.worker.layout.model`
(`CONFLICT_*`). Report what the evidence shows; do not invent a resolution.
An unresolvable ordering problem is `SEVERITY_HOLD`, a suspicious but usable
claim is `SEVERITY_WARN`, and an observation worth reviewing is
`SEVERITY_INFO`.

The function is pure and must be deterministic for the same inputs.
"""

from __future__ import annotations

from collections import defaultdict

from .model import (
    CONFLICT_AMBIGUOUS_COLUMN,
    CONFLICT_CONTAINER_LEAK,
    CONFLICT_CROSS_COLUMN_JUMP,
    CONFLICT_MISSING_GEOMETRY,
    CONFLICT_ORDER_INVERSION,
    CONFLICT_OVERLAPPING_MEMBERSHIP,
    REGION_COLUMN,
    REGION_CONTAINER,
    REGION_FULL_WIDTH,
    SEVERITY_HOLD,
    SEVERITY_INFO,
    SEVERITY_WARN,
    BlockRef,
    Conflict,
    Region,
)


def detect_conflicts(
    regions: list[Region],
    refs_by_uid: dict[str, BlockRef],
    order: list[str],
    current_order: list[str],
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    page_counters: dict[int, int] = defaultdict(int)

    def emit(page: int, kind: str, severity: str, blocks: tuple[str, ...], detail: str) -> None:
        key = (kind, blocks)
        if key in seen:
            return
        seen.add(key)
        conflicts.append(Conflict(f"p{page}:x{page_counters[page]}", page, kind, severity, blocks, detail))
        page_counters[page] += 1
    sorted_refs = sorted(refs_by_uid.values(), key=lambda ref: (ref.page, ref.uid))
    regions_by_page: dict[int, list[Region]] = defaultdict(list)
    for region in sorted(regions, key=lambda item: (item.page, item.y_top, item.x_left, item.kind, item.region_id)):
        regions_by_page[region.page].append(region)

    # A block that a full-width or container region owns has a decided column,
    # so the gutter test would only produce noise for titles and figures.
    non_column: set[str] = {
        uid for region in regions if region.kind != REGION_COLUMN for uid in region.members
    }

    # Missing and ambiguous geometry are per-block observations.
    for ref in sorted_refs:
        if ref.uid in non_column:
            continue
        if ref.bbox is None:
            emit(ref.page, CONFLICT_MISSING_GEOMETRY, SEVERITY_HOLD, (ref.uid,), "bbox missing")
            continue
        if ref.page_width <= 0:
            continue
        gutter_centers: list[float] = []
        columns = sorted(
            (region for region in regions_by_page[ref.page] if region.kind == REGION_COLUMN),
            key=lambda region: (region.x_left, region.x_right, region.region_id),
        )
        for left, right in zip(columns, columns[1:], strict=False):
            if left.x_right <= right.x_left:
                gutter_centers.append((left.x_right + right.x_left) / 2)
        # The page midpoint remains the meaningful gutter when region edges
        # touch or overlap due to OCR geometry.
        if len(columns) >= 2 and not gutter_centers:
            gutter_centers.append(ref.page_width / 2)
        if any(abs(ref.center_x - gutter) <= ref.page_width * 0.02 for gutter in gutter_centers):
            emit(ref.page, CONFLICT_AMBIGUOUS_COLUMN, SEVERITY_HOLD, (ref.uid,), f"center_x={ref.center_x:g}")

    # A block assigned to multiple regions has contradictory ownership.
    memberships: dict[str, list[Region]] = defaultdict(list)
    for region in regions:
        for uid in region.members:
            memberships[uid].append(region)
    for uid in sorted(memberships):
        owners = sorted(memberships[uid], key=lambda region: (region.page, region.kind, region.region_id))
        if len(owners) > 1 and uid in refs_by_uid:
            emit(
                refs_by_uid[uid].page,
                CONFLICT_OVERLAPPING_MEMBERSHIP,
                SEVERITY_WARN,
                (uid,),
                f"regions={len(owners)}",
            )

    # A container can extend slightly beyond its member's measured bbox.
    for region in sorted(regions, key=lambda item: (item.page, item.y_top, item.x_left, item.kind, item.region_id)):
        if region.kind != REGION_CONTAINER:
            continue
        for uid in sorted(region.members):
            ref = refs_by_uid.get(uid)
            if ref is None or ref.bbox is None:
                continue
            tolerance = ref.page_width * 0.02
            left, top, right, bottom = ref.bbox
            outside = (
                left < region.x_left - tolerance
                or right > region.x_right + tolerance
                or top < region.y_top - tolerance
                or bottom > region.y_bottom + tolerance
            )
            center_x = ref.center_x
            center_y = ref.center_y
            # A table or box that spans the gutter legitimately owns blocks on
            # both sides; only a narrow container can leak into another column.
            narrow = (region.x_right - region.x_left) < ref.page_width * 0.6
            other_column = narrow and any(
                column.page == region.page
                and column.kind == REGION_COLUMN
                and column.region_id != region.parent_id
                and column.x_left <= center_x <= column.x_right
                and column.y_top <= center_y <= column.y_bottom
                for column in regions_by_page[region.page]
            )
            if outside or other_column:
                emit(
                    region.page,
                    CONFLICT_CONTAINER_LEAK,
                    SEVERITY_WARN,
                    (uid,),
                    f"outside={int(outside)} other_column={int(other_column)}",
                )

    # Report adjacent canonical-order pairs that OCR emitted in reverse order.
    current_positions = {uid: index for index, uid in enumerate(current_order)}
    for before, after in zip(order, order[1:], strict=False):
        if (
            before not in current_positions
            or after not in current_positions
            or current_positions[before] <= current_positions[after]
        ):
            continue
        first, second = refs_by_uid.get(before), refs_by_uid.get(after)
        confident = first is not None and second is not None and first.bbox is not None and second.bbox is not None
        if confident:
            confident = not any(
                conflict.kind == CONFLICT_AMBIGUOUS_COLUMN and conflict.blocks[0] in (before, after)
                for conflict in conflicts
            )
        emit(first.page if first else (second.page if second else 0), CONFLICT_ORDER_INVERSION,
             SEVERITY_WARN if confident else SEVERITY_INFO, (before, after),
             f"current_positions={current_positions[before]},{current_positions[after]}")

    # Consecutive OCR blocks crossing between columns without an intervening
    # full-width band are direct evidence of a column jump.
    column_for: dict[str, list[Region]] = defaultdict(list)
    for region in regions:
        if region.kind == REGION_COLUMN:
            for uid in region.members:
                column_for[uid].append(region)
    for first_uid, second_uid in zip(current_order, current_order[1:], strict=False):
        first, second = refs_by_uid.get(first_uid), refs_by_uid.get(second_uid)
        if first is None or second is None or first.bbox is None or second.bbox is None or first.page != second.page:
            continue
        y1, y2 = first.center_y, second.center_y
        if max(first.bbox[1], second.bbox[1]) > min(first.bbox[3], second.bbox[3]):
            continue
        different_columns = any(
            a.region_id != b.region_id
            for a in column_for[first_uid]
            for b in column_for[second_uid]
        )
        if not different_columns:
            continue
        separated = any(
            region.page == first.page
            and region.kind == REGION_FULL_WIDTH
            and max(first.bbox[1], region.y_top) <= min(second.bbox[3], region.y_bottom)
            for region in regions_by_page[first.page]
        )
        if not separated:
            emit(
                first.page,
                CONFLICT_CROSS_COLUMN_JUMP,
                SEVERITY_WARN,
                (first_uid, second_uid),
                f"center_y={y1:g},{y2:g}",
            )

    return conflicts
