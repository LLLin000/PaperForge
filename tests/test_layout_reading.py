from __future__ import annotations

from copy import deepcopy

from paperforge.worker.layout.model import (
    REGION_COLUMN,
    REGION_CONTAINER,
    REGION_FULL_WIDTH,
    RELATION_HOLD,
    BlockRef,
    Region,
)
from paperforge.worker.layout.reading import build_reading_order


def ref(uid: str, box: tuple[float, float, float, float], role: str | None = None) -> BlockRef:
    return BlockRef(uid, 1, uid, box, 0, role, 10, 600, 800)


def region(
    name: str,
    kind: str,
    bounds: tuple[int, int, int, int],
    members: tuple[str, ...],
    confidence: float = 1.0,
) -> Region:
    x, y, right, bottom = bounds
    return Region(name, 1, kind, x, right, y, bottom, members, None, confidence)


def test_single_column_order_and_adjacent_decisions() -> None:
    refs = {"a": ref("a", (10, 40, 100, 60)), "b": ref("b", (10, 10, 100, 30))}
    regions = [region("c", REGION_COLUMN, (0, 0, 250, 100), ("a", "b"))]
    order, decisions, holds = build_reading_order(regions, refs, ["a", "b"])
    assert order == ["b", "a"]
    assert [(d.before, d.after) for d in decisions] == [("b", "a")]
    assert decisions[0].confidence == 0.85
    assert holds == []


def test_two_columns_read_left_then_right() -> None:
    refs = {uid: ref(uid, box) for uid, box in {
        "l1": (10, 10, 100, 30), "l2": (10, 70, 100, 90),
        "r1": (310, 10, 400, 30), "r2": (310, 50, 400, 70),
    }.items()}
    regions = [
        region("right", REGION_COLUMN, (300, 10, 500, 90), ("r2", "r1")),
        region("left", REGION_COLUMN, (0, 10, 200, 90), ("l2", "l1")),
    ]
    order, decisions, _ = build_reading_order(regions, refs, list(refs))
    assert order == ["l1", "l2", "r1", "r2"]
    assert decisions[1].confidence == 0.7



def test_weak_split_caps_cross_column_confidence() -> None:
    refs = {"l": ref("l", (10, 10, 100, 30)), "r": ref("r", (310, 10, 400, 30))}
    regions = [
        region("left", REGION_COLUMN, (0, 10, 200, 50), ("l",), 0.5),
        region("right", REGION_COLUMN, (300, 10, 500, 50), ("r",), 0.5),
    ]
    _, decisions, holds = build_reading_order(regions, refs, ["l", "r"])
    decision = decisions[0]
    assert decision.relation == "before"
    assert decision.confidence == 0.5
    assert decision.reason == "column hand-off supported by band geometry (region confidence 0.50)"
    assert holds == []


def test_strong_split_preserves_lower_geometry_confidence() -> None:
    refs = {"l": ref("l", (10, 10, 100, 30)), "r": ref("r", (310, 10, 400, 30))}
    regions = [
        region("left", REGION_COLUMN, (0, 10, 200, 50), ("l",), 0.75),
        region("right", REGION_COLUMN, (300, 10, 500, 50), ("r",), 0.75),
    ]
    _, decisions, holds = build_reading_order(regions, refs, ["l", "r"])
    assert decisions[0].confidence == 0.7
    assert decisions[0].reason == "column hand-off supported by band geometry"
    assert holds == []


def test_single_column_confidence_0_9_does_not_cap_same_region_decision() -> None:
    refs = {"a": ref("a", (10, 10, 100, 20)), "b": ref("b", (10, 30, 100, 40))}
    regions = [region("c", REGION_COLUMN, (0, 0, 200, 100), ("a", "b"), 0.9)]
    _, decisions, holds = build_reading_order(regions, refs, ["a", "b"])
    assert decisions[0].confidence == 0.85
    assert decisions[0].reason == "same region, top-down order"
    assert holds == []

def test_top_aligned_short_left_column_is_still_read_first() -> None:
    """A left column ending early is normal two-column flow, not ambiguity."""
    refs = {"l": ref("l", (10, 10, 100, 40)), "r": ref("r", (310, 10, 400, 40))}
    regions = [
        region("left", REGION_COLUMN, (0, 10, 200, 50), ("l",)),
        region("right", REGION_COLUMN, (300, 10, 500, 100), ("r",)),
    ]
    order, decisions, holds = build_reading_order(regions, refs, ["r", "l"])
    assert order == ["l", "r"]
    assert decisions[0].relation == "before"
    assert holds == []


def test_staggered_columns_hold_and_preserve_ocr_relative_order() -> None:
    """When one column starts above the other, the hand-off is not decidable."""
    refs = {"l": ref("l", (10, 90, 100, 120)), "r": ref("r", (310, 10, 400, 40))}
    regions = [
        region("left", REGION_COLUMN, (0, 90, 200, 120), ("l",)),
        region("right", REGION_COLUMN, (300, 10, 500, 120), ("r",)),
    ]
    order, decisions, holds = build_reading_order(regions, refs, ["r", "l"])
    assert order == ["r", "l"]
    assert decisions[0].relation == RELATION_HOLD
    assert decisions[0].confidence == 0.0
    assert decisions[0].reason == "column continuation is ambiguous"
    assert holds == ["r", "l"]


def test_container_is_contiguous_heading_first_and_coverage_unique() -> None:
    refs = {
        "before": ref("before", (10, 10, 100, 20)),
        "body": ref("body", (20, 80, 100, 100)),
        "head": ref("head", (20, 40, 100, 50), "section_heading"),
        "after": ref("after", (10, 140, 100, 150)),
        "outside": ref("outside", (10, 200, 100, 210)),
    }
    regions = [
        region("later", REGION_FULL_WIDTH, (0, 140, 500, 160), ("after",)),
        region("container", REGION_CONTAINER, (0, 30, 200, 110), ("body", "head")),
        region("earlier", REGION_FULL_WIDTH, (0, 0, 500, 30), ("before",)),
    ]
    order, decisions, holds = build_reading_order(regions, refs, ["before", "head", "body", "after", "outside"])
    assert order == ["before", "head", "body", "after", "outside"]
    assert len(order) == len(set(order)) == len(refs)
    assert len(decisions) == len(order) - 1
    assert holds == ["after", "outside"]


def test_deterministic_and_pure() -> None:
    refs = {"a": ref("a", (10, 10, 100, 20)), "b": ref("b", (10, 30, 100, 40))}
    regions = [region("c", REGION_COLUMN, (0, 0, 200, 100), ("b", "a"))]
    current = ["b", "a"]
    before = deepcopy((regions, refs, current))
    first = build_reading_order(regions, refs, current)
    assert first == build_reading_order(regions, refs, current)
    assert (regions, refs, current) == before


def test_margin_region_is_emitted_after_body_content() -> None:
    from paperforge.worker.layout.model import REGION_MARGIN

    refs = {"head": ref("head", (10, 5, 400, 20)), "body": ref("body", (10, 300, 400, 400))}
    regions = [
        region("margin", REGION_MARGIN, (0, 0, 500, 30), ("head",)),
        region("body", REGION_COLUMN, (0, 300, 500, 400), ("body",)),
    ]
    order, decisions, _ = build_reading_order(regions, refs, ["head", "body"])
    assert order == ["body", "head"]
    assert decisions[0].reason == "page furniture after body content"


def test_same_row_labels_are_ordered_left_to_right() -> None:
    """A few pixels of baseline jitter must not flip two labels on one row."""
    refs = {
        "right": ref("right", (400, 102, 460, 126)),
        "left": ref("left", (200, 100, 260, 124)),
    }
    regions = [region("c", REGION_COLUMN, (0, 0, 600, 800), ("right", "left"))]
    order, _, _ = build_reading_order(regions, refs, ["right", "left"])
    assert order == ["left", "right"]
