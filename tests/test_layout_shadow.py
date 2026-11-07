"""Shadow render seam: reordering must be opt-in, scoped and lossless."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from paperforge.worker.layout.plan import build_layout_plan
from paperforge.worker.ocr_render import _apply_layout_order, render_fulltext_markdown

REPO = Path(__file__).resolve().parents[1]


def _shadow_module():
    spec = importlib.util.spec_from_file_location(
        "layout_shadow_render", REPO / "scripts/dev/layout_shadow_render.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _block(bid: str, bbox, role="body_paragraph", text="text", page=1) -> dict:
    return {
        "page": page,
        "block_id": bid,
        "bbox": list(bbox),
        "page_width": 1000,
        "page_height": 1400,
        "role": role,
        "text": text,
    }


def test_reorder_applies_only_to_listed_pages_and_keeps_every_block() -> None:
    blocks = [
        {"page": 1, "block_id": "a", "_layout_source_index": 0},
        {"page": 1, "block_id": "b", "_layout_source_index": 1},
        {"page": 1, "block_id": "c", "_layout_source_index": 2},
        {"page": 2, "block_id": "d", "_layout_source_index": 3},
        {"page": 2, "block_id": "e", "_layout_source_index": 4},
    ]
    ordered = _apply_layout_order(blocks, {1: [2, 0, 1]})
    assert [block["block_id"] for block in ordered] == ["c", "a", "b", "d", "e"]


def test_blocks_without_a_listed_source_index_keep_relative_order_at_the_end() -> None:
    blocks = [
        {"page": 1, "block_id": "a", "_layout_source_index": 0},
        {"page": 1, "block_id": "b", "_layout_source_index": 1},
        {"page": 1, "block_id": "stray"},
    ]
    ordered = _apply_layout_order(blocks, {1: [1, 0]})
    assert [block["block_id"] for block in ordered] == ["b", "a", "stray"]


def test_empty_override_is_a_noop_for_rendering() -> None:
    blocks = [_block("a", (80, 100, 600, 140), "section_heading", "Results")]
    blocks.append(_block("b", (80, 180, 600, 260), text="Body text."))
    document = None
    kwargs = dict(
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=1,
        document_structure=document,
        reader_payload={},
        return_events=True,
    )
    baseline = render_fulltext_markdown(structured_blocks=[dict(block) for block in blocks], **kwargs)
    override = render_fulltext_markdown(structured_blocks=[dict(block) for block in blocks], layout_order={}, **kwargs)
    assert baseline.markdown == override.markdown
    assert baseline.heading_events == override.heading_events
    assert [event.get("block_id") for event in baseline.emitted_block_events] == [
        event.get("block_id") for event in override.emitted_block_events
    ]


def test_shadow_scope_excludes_tail_references_and_object_pages() -> None:
    module = _shadow_module()
    blocks = [
        _block("body", (80, 200, 600, 400), "body_paragraph", "Body."),
        _block("ref", (80, 600, 600, 640), "reference_item", "[1] Reference."),
    ]
    by_page = {1: blocks}
    plan = build_layout_plan(blocks)
    ok, reason = module.page_in_scope(plan.pages[0], by_page)
    assert not ok and reason.startswith("role:reference_item")

    container_blocks = [
        _block("body", (80, 200, 600, 400), "body_paragraph", "Body."),
        _block("table", (80, 500, 900, 800), "table_html", "<table></table>"),
    ]
    container_plan = build_layout_plan(container_blocks)
    ok, reason = module.page_in_scope(container_plan.pages[0], {1: container_blocks})
    assert not ok and reason == "container_region"

    plain = [_block("a", (80, 200, 600, 400), "body_paragraph", "Body.")]
    plain_plan = build_layout_plan(plain)
    ok, _ = module.page_in_scope(plain_plan.pages[0], {1: plain})
    assert ok
