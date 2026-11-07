from __future__ import annotations

from paperforge.worker.layout.model import (
    REGION_COLUMN,
    REGION_CONTAINER,
    REGION_FULL_WIDTH,
    BlockRef,
)
from paperforge.worker.layout.regions import build_region_tree


def block(uid: str, bbox: tuple[float, float, float, float] | None, role: str | None = None) -> BlockRef:
    return BlockRef(uid, 1, uid, bbox, 0, role, 10, 1000, 1200)


def test_single_column():
    regions = build_region_tree([block("a", (100, 100, 300, 150)), block("b", (110, 200, 320, 250))], 1)
    assert len(regions) == 1
    assert regions[0].kind == REGION_COLUMN
    assert regions[0].members == ("a", "b")
    assert regions[0].confidence == 0.9


def test_two_columns():
    refs = [block(f"l{i}", (100, 100 + i * 100, 350, 150 + i * 100)) for i in range(3)]
    refs += [block(f"r{i}", (650, 100 + i * 100, 900, 150 + i * 100)) for i in range(3)]
    regions = build_region_tree(refs, 1)
    columns = [region for region in regions if region.kind == REGION_COLUMN]
    assert len(columns) == 2
    assert columns[0].members == ("l0", "l1", "l2")
    assert columns[1].members == ("r0", "r1", "r2")
    assert all(region.confidence == 0.75 for region in columns)


def test_full_width_splits_bands():
    refs = [block("top", (100, 100, 400, 150)), block("wide", (0, 300, 1000, 360)), block("bottom", (100, 500, 400, 550))]
    regions = build_region_tree(refs, 1)
    wide = next(region for region in regions if region.kind == REGION_FULL_WIDTH)
    columns = [region for region in regions if region.kind == REGION_COLUMN]
    assert wide.members == ("wide",)
    assert len(columns) == 2
    assert columns[0].members == ("top",)
    assert columns[1].members == ("bottom",)


def test_container_owns_contained_members():
    refs = [
        block("text", (100, 100, 350, 150)),
        block("insert", (100, 200, 500, 450), "structured_insert"),
        block("caption", (110, 210, 400, 240)),
        block("body", (120, 270, 450, 320)),
    ]
    regions = build_region_tree(refs, 1)
    container = next(region for region in regions if region.kind == REGION_CONTAINER)
    columns = [region for region in regions if region.kind == REGION_COLUMN]
    assert container.members == ("insert", "caption", "body")
    for column in columns:
        assert "insert" not in column.members
        assert "caption" not in column.members
        assert "body" not in column.members
    parent = next(region for region in columns if region.region_id == container.parent_id)
    # The container's parent is the column piece it sits in, not the page.
    assert parent.y_top <= container.y_top and container.y_bottom <= parent.y_bottom


def test_missing_bbox_fallback():
    regions = build_region_tree([block("a", None)], 1)
    assert len(regions) == 1
    assert regions[0].kind == REGION_COLUMN
    assert regions[0].members == ("a",)
    assert regions[0].confidence == 0.1
    assert "missing bbox" in regions[0].evidence


def test_determinism_and_shuffle_invariance():
    refs = [block(f"l{i}", (100, 100 + i * 100, 350, 150 + i * 100)) for i in range(3)]
    refs += [block(f"r{i}", (650, 100 + i * 100, 900, 150 + i * 100)) for i in range(3)]
    result = build_region_tree(refs, 1)
    assert result == build_region_tree(refs, 1)
    shuffled = build_region_tree(list(reversed(refs)), 1)
    assert [(r.kind, r.x_left, r.x_right, r.y_top, r.y_bottom, r.members) for r in result] == [
        (r.kind, r.x_left, r.x_right, r.y_top, r.y_bottom, r.members) for r in shuffled
    ]


def test_margin_bands_hold_running_heads_and_folios() -> None:
    from paperforge.worker.layout.model import REGION_MARGIN

    refs = [
        BlockRef("h", 1, "h", (60, 20, 500, 40), 0, "body_paragraph", 20, 1000, 1400),
        BlockRef("b", 1, "b", (60, 200, 900, 400), 1, "body_paragraph", 200, 1000, 1400),
        BlockRef("f", 1, "f", (450, 1360, 500, 1380), 2, "body_paragraph", 3, 1000, 1400),
    ]
    regions = build_region_tree(refs, 1)
    margin = [region for region in regions if region.kind == REGION_MARGIN]
    assert len(margin) == 1
    assert set(margin[0].members) == {"h", "f"}
    content = [uid for region in regions if region.kind != REGION_MARGIN for uid in region.members]
    assert content == ["b"]
