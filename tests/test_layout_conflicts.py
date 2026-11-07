from __future__ import annotations

from copy import deepcopy

from paperforge.worker.layout.conflicts import detect_conflicts
from paperforge.worker.layout.model import (
    CONFLICT_AMBIGUOUS_COLUMN,
    CONFLICT_CONTAINER_LEAK,
    CONFLICT_CROSS_COLUMN_JUMP,
    CONFLICT_MISSING_GEOMETRY,
    CONFLICT_ORDER_INVERSION,
    REGION_COLUMN,
    REGION_CONTAINER,
    SEVERITY_HOLD,
    SEVERITY_INFO,
    SEVERITY_WARN,
    BlockRef,
    Region,
)


def ref(uid: str, bbox: tuple[float, float, float, float] | None, *, page: int = 1, width: float = 1000) -> BlockRef:
    return BlockRef(uid, page, uid, bbox, 0, "text", 1, width, 1400)


def region(
    region_id: str, kind: str, members: tuple[str, ...], *,
    x: tuple[float, float] = (0, 1000), y: tuple[float, float] = (0, 1400),
    parent: str | None = None,
) -> Region:
    return Region(region_id, 1, kind, *x, *y, members, parent, 1.0)


def kinds(conflicts):
    return [conflict.kind for conflict in conflicts]


def test_missing_geometry_is_hold():
    conflicts = detect_conflicts([], {"a": ref("a", None)}, [], [])
    assert len(conflicts) == 1
    assert conflicts[0].kind == CONFLICT_MISSING_GEOMETRY
    assert conflicts[0].severity == SEVERITY_HOLD


def test_ambiguous_column_near_gutter_is_hold():
    refs = {"a": ref("a", (480, 100, 520, 140))}
    regions = [region("left", REGION_COLUMN, ("a",), x=(0, 480)), region("right", REGION_COLUMN, (), x=(520, 1000))]
    conflicts = detect_conflicts(regions, refs, ["a"], ["a"])
    assert kinds(conflicts) == [CONFLICT_AMBIGUOUS_COLUMN]
    assert conflicts[0].severity == SEVERITY_HOLD


def test_overlapping_membership_is_reported_once():
    refs = {"a": ref("a", (100, 100, 200, 140))}
    regions = [region("one", REGION_COLUMN, ("a",)), region("two", REGION_COLUMN, ("a",))]
    conflicts = detect_conflicts(regions, refs, [], [])
    assert kinds(conflicts) == ["overlapping_membership"]
    assert conflicts[0].severity == SEVERITY_WARN


def test_container_member_outside_expanded_bounds_leaks():
    refs = {"a": ref("a", (300, 300, 400, 350))}
    regions = [region("container", REGION_CONTAINER, ("a",), x=(100, 250), y=(100, 250))]
    conflicts = detect_conflicts(regions, refs, [], [])
    assert kinds(conflicts) == [CONFLICT_CONTAINER_LEAK]

def test_container_member_in_another_column_leaks():
    refs = {"a": ref("a", (650, 300, 700, 350))}
    regions = [
        region("left", REGION_COLUMN, (), x=(0, 480)),
        region("right", REGION_COLUMN, (), x=(520, 1000)),
        region("container", REGION_CONTAINER, ("a",), x=(600, 800), y=(250, 400), parent="left"),
    ]
    conflicts = detect_conflicts(regions, refs, [], [])
    leak = next(conflict for conflict in conflicts if conflict.kind == CONFLICT_CONTAINER_LEAK)
    assert leak.detail == "outside=0 other_column=1"



def test_order_inversion_severity_uses_geometry_confidence():
    refs = {"a": ref("a", (100, 100, 150, 140)), "b": ref("b", (200, 100, 250, 140))}
    conflicts = detect_conflicts([], refs, ["a", "b"], ["b", "a"])
    inversion = next(conflict for conflict in conflicts if conflict.kind == CONFLICT_ORDER_INVERSION)
    assert inversion.severity == SEVERITY_WARN
    refs["a"] = ref("a", None)
    uncertain = detect_conflicts([], refs, ["a", "b"], ["b", "a"])
    inversion = next(conflict for conflict in uncertain if conflict.kind == CONFLICT_ORDER_INVERSION)
    assert inversion.severity == SEVERITY_INFO


def test_cross_column_jump_without_full_width_separator():
    refs = {
        "a": ref("a", (100, 100, 200, 140)),
        "b": ref("b", (700, 110, 800, 150)),
    }
    regions = [region("left", REGION_COLUMN, ("a",), x=(0, 480)), region("right", REGION_COLUMN, ("b",), x=(520, 1000))]
    conflicts = detect_conflicts(regions, refs, ["a", "b"], ["a", "b"])
    assert kinds(conflicts) == [CONFLICT_CROSS_COLUMN_JUMP]


def test_clean_two_column_page_has_no_conflicts():
    refs = {
        "a": ref("a", (100, 100, 300, 140)),
        "b": ref("b", (600, 100, 800, 140)),
        "c": ref("c", (100, 200, 300, 240)),
        "d": ref("d", (600, 200, 800, 240)),
    }
    regions = [
        region("left", REGION_COLUMN, ("a", "c"), x=(0, 480)),
        region("right", REGION_COLUMN, ("b", "d"), x=(520, 1000)),
    ]
    assert detect_conflicts(regions, refs, ["a", "c", "b", "d"], ["a", "c", "b", "d"]) == []


def test_deterministic_and_pure():
    refs = {"a": ref("a", (100, 100, 200, 140)), "b": ref("b", (700, 100, 800, 140))}
    regions = [region("left", REGION_COLUMN, ("a",)), region("right", REGION_COLUMN, ("b",))]
    order, current = ["a", "b"], ["b", "a"]
    before = deepcopy((regions, refs, order, current))
    first = detect_conflicts(regions, refs, order, current)
    second = detect_conflicts(regions, refs, order, current)
    assert first == second
    assert (regions, refs, order, current) == before
    assert [conflict.conflict_id for conflict in first] == [f"p1:x{index}" for index in range(len(first))]
