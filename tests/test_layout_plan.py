"""Plan-level invariants: identity, coverage, determinism, purity.

These do not test the segmentation quality — that lives in the per-module
tests. They pin the contract every consumer may rely on.
"""

from __future__ import annotations

import copy

from paperforge.worker.layout import build_layout_plan, collect_block_refs


def _blocks() -> list[dict]:
    return [
        {"page": 1, "block_id": "1", "bbox": [60, 80, 540, 110], "page_width": 1200, "page_height": 1600, "role": "section_heading", "text": "Results"},
        {"page": 1, "block_id": "2", "bbox": [60, 130, 540, 260], "page_width": 1200, "page_height": 1600, "role": "body_paragraph", "text": "Left column text."},
        {"page": 1, "block_id": "3", "bbox": [640, 130, 1140, 300], "page_width": 1200, "page_height": 1600, "role": "body_paragraph", "text": "Right column text."},
        {"page": 1, "block_id": "4", "bbox": [60, 400, 1140, 600], "page_width": 1200, "page_height": 1600, "role": "figure_asset", "text": ""},
        {"page": 2, "block_id": "1", "bbox": [60, 80, 1140, 120], "page_width": 1200, "page_height": 1600, "role": "body_paragraph", "text": "Second page."},
        {"page": 2, "block_id": "2", "bbox": [], "page_width": 1200, "page_height": 1600, "role": "footnote", "text": "No bbox."},
    ]


def test_collect_block_refs_assigns_geometry_keyed_uids() -> None:
    refs = collect_block_refs(_blocks())
    assert [ref.uid for ref in refs] == [f"p1:{i:04d}" for i in range(4)] + ["p2:0000", "p2:0001"]
    assert refs[0].block_id == "1" and refs[0].role == "section_heading"


def test_collect_block_refs_is_input_order_independent() -> None:
    forward = {ref.uid: (ref.page, ref.block_id, ref.bbox) for ref in collect_block_refs(_blocks())}
    backward = {
        ref.uid: (ref.page, ref.block_id, ref.bbox)
        for ref in collect_block_refs(list(reversed(_blocks())))
    }
    assert forward == backward


def test_plan_structure_is_shuffle_invariant() -> None:
    """Regions and conflicts are geometry-only; held pairs defer to OCR order."""
    original = build_layout_plan(_blocks()).to_dict()
    shuffled = build_layout_plan(list(reversed(_blocks()))).to_dict()

    # `order_inversion` and `cross_column_jump` measure the plan against the
    # OCR order, so they intentionally move when that evidence is shuffled.
    geometry_kinds = {"missing_geometry", "ambiguous_column", "overlapping_membership", "container_leak"}

    for forward, backward in zip(original["pages"], shuffled["pages"]):
        assert forward["regions"] == backward["regions"]
        def geometry(page: dict) -> list[dict]:
            return [c for c in page["conflicts"] if c["kind"] in geometry_kinds]

        assert geometry(forward) == geometry(backward)
        held = set(forward["holds"]) | set(backward["holds"])
        assert [uid for uid in forward["order"] if uid not in held] == [
            uid for uid in backward["order"] if uid not in held
        ]


def test_plan_does_not_mutate_input_blocks() -> None:
    blocks = _blocks()
    snapshot = copy.deepcopy(blocks)
    build_layout_plan(blocks)
    assert blocks == snapshot


def test_every_block_is_described_exactly_once() -> None:
    plan = build_layout_plan(_blocks())
    seen: list[str] = []
    for page in plan.pages:
        for region in page.regions:
            seen.extend(region.members)
    assert len(seen) == len(set(seen))
    assert set(seen) == {ref.uid for ref in collect_block_refs(_blocks())}


def test_region_ids_are_stable_and_page_scoped() -> None:
    plan = build_layout_plan(_blocks())
    ids = [region.region_id for page in plan.pages for region in page.regions]
    assert len(ids) == len(set(ids))
    assert all(region_id.startswith(f"p{region_id[1]}:") for region_id in ids)
    assert plan.to_dict()["version"] == plan.version
