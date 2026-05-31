from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LayoutZone:
    zone_id: str
    page_index: int
    y_range: tuple[int, int]
    node_ids: list[str] = field(default_factory=list)
    regime_type: str = "uncertain"
    regime_confidence: float = 0.0
    column_count: int | None = None
    column_bounds: list[tuple[int, int]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


def _attr(obj, name, default=None):
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def _bbox_xc(bbox):
    if bbox[2] <= bbox[0]:
        return None
    return (bbox[0] + bbox[2]) / 2


def detect_layout_zones(
    spine_nodes: list,
    page_width: int = 0,
    page_height: int = 0,
) -> list[LayoutZone]:
    if not spine_nodes:
        return []

    mid = page_width / 2 if page_width else 600
    left_nodes = []
    right_nodes = []

    for node in spine_nodes:
        bbox = tuple(_attr(node, "bbox", (0, 0, 0, 0)))
        xc = _bbox_xc(bbox)
        if xc is None:
            continue
        if xc < mid:
            left_nodes.append(node)
        else:
            right_nodes.append(node)

    zone = LayoutZone(
        zone_id="page-default",
        page_index=0,
        y_range=(0, page_height or 1684),
        node_ids=[_attr(n, "node_id", "") for n in spine_nodes],
        regime_type="two_col" if left_nodes and right_nodes else "single_col",
        regime_confidence=0.6 if left_nodes and right_nodes else 0.8,
        column_count=2 if left_nodes and right_nodes else 1,
        column_bounds=(
            [(0, int(mid)), (int(mid), page_width)] if left_nodes and right_nodes else [(0, page_width)]
        ),
        evidence=(
            [f"two-column body layout: {len(left_nodes)}L/{len(right_nodes)}R nodes"]
            if left_nodes and right_nodes
            else ["single-column body layout"]
        ),
    )

    return [zone]


def order_body_spine(
    spine_nodes: list,
    zones: list[LayoutZone],
    mode: str = "prior_preserving",
) -> list:
    if not zones:
        return list(spine_nodes)

    zone = zones[0]

    if zone.regime_type == "two_col" and mode == "column_major":
        mid = zone.column_bounds[0][1] if zone.column_bounds else 600
        left = []
        right = []
        for node in spine_nodes:
            bbox = tuple(_attr(node, "bbox", (0, 0, 0, 0)))
            xc = _bbox_xc(bbox)
            if xc is None:
                left.append(node)
                continue
            if xc < mid:
                left.append(node)
            else:
                right.append(node)

        left.sort(key=lambda n: _attr(n, "bbox", (0, 0, 0, 0))[1])
        right.sort(key=lambda n: _attr(n, "bbox", (0, 0, 0, 0))[1])
        return left + right

    return list(spine_nodes)
