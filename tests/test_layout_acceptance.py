"""Production acceptance gate: the plan may only replace the current order when
every ordering claim on the page is confident and no conflict claims uncertainty.
"""

from __future__ import annotations

import copy

from paperforge.worker.layout import build_layout_plan
from paperforge.worker.layout.acceptance import (
    STATUS_ACCEPT,
    STATUS_HOLD,
    STATUS_REJECT,
    assess_page,
    assess_plan,
)
from paperforge.worker.layout.evaluate import evaluate_plan
from paperforge.worker.layout.model import Conflict


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


def _single_column_page() -> list[dict]:
    return [
        _block("a", (80, 100, 600, 140), "section_heading", "Results"),
        _block("b", (80, 180, 600, 300), text="Body one."),
        _block("c", (80, 340, 600, 460), text="Body two."),
    ]


def _weak_two_column_page() -> list[dict]:
    return [
        _block("l1", (60, 200, 460, 320), text="Left one."),
        _block("l2", (60, 360, 460, 480), text="Left two."),
        _block("r1", (560, 200, 960, 320), text="Right one."),
        _block("r2", (560, 360, 960, 480), text="Right two."),
    ]


def test_confident_single_column_page_is_accepted() -> None:
    blocks = _single_column_page()
    plan = build_layout_plan(blocks)
    result = assess_page(plan, plan.pages[0], blocks)

    assert result.status == STATUS_ACCEPT
    assert result.accepted_order == plan.pages[0].order
    assert result.fallback_reason is None
    assert set(result.source_mapping) == set(result.accepted_order)


def test_low_confidence_two_column_page_is_held() -> None:
    blocks = _weak_two_column_page()
    plan = build_layout_plan(blocks)
    result = assess_page(plan, plan.pages[0], blocks)

    assert result.status == STATUS_HOLD
    assert result.fallback_reason == "low_confidence"
    assert result.accepted_order is None
    assert result.held_blocks  # the pair whose relation is only 0.50


def test_ambiguous_column_conflict_holds_the_page() -> None:
    """A hold-severity conflict must veto the page, whatever the order says."""
    blocks = _single_column_page()
    plan = build_layout_plan(blocks)
    page = plan.pages[0]
    page.conflicts.append(
        Conflict(
            conflict_id="p1:x99",
            page=1,
            kind="ambiguous_column",
            severity="hold",
            blocks=(page.order[0],),
            detail="synthetic gutter block",
        )
    )
    result = assess_page(plan, page, blocks)

    assert result.status == STATUS_HOLD
    assert "ambiguous_column" in result.evidence["blocking_conflicts"]
    assert result.fallback_reason == "hold_conflict"


def test_hold_decision_holds_the_page() -> None:
    blocks = _single_column_page()
    plan = build_layout_plan(blocks)
    page = plan.pages[0]
    page.decisions[0] = page.decisions[0].__class__(
        before=page.decisions[0].before,
        after=page.decisions[0].after,
        relation="hold",
        confidence=0.0,
        reason="synthetic",
    )
    result = assess_page(plan, page, blocks)
    assert result.status == STATUS_HOLD
    assert result.fallback_reason in {"hold_decision", "hold_conflict"}


def test_editing_a_block_after_planning_rejects_the_page() -> None:
    blocks = _single_column_page()
    plan = build_layout_plan(blocks)
    edited = copy.deepcopy(blocks)
    edited[1]["text"] = "Edited after planning."
    result = assess_page(plan, plan.pages[0], edited)
    assert result.status == STATUS_REJECT
    assert result.fallback_reason == "identity_mismatch"


def test_duplicate_block_ids_map_by_position_not_by_id() -> None:
    blocks = [
        _block("dup", (80, 100, 600, 140), text="First with this id."),
        _block("dup", (80, 180, 600, 220), text="Second with this id."),
    ]
    plan = build_layout_plan(blocks)
    result = assess_page(plan, plan.pages[0], blocks)

    assert result.status == STATUS_ACCEPT
    assert len(result.source_mapping) == 2
    assert sorted(result.source_mapping.values()) == [0, 1]


def test_duplicate_membership_is_rejected() -> None:
    blocks = _single_column_page()
    plan = build_layout_plan(blocks)
    page = plan.pages[0]
    region = page.regions[0]
    tampered = region.__class__(**{**region.__dict__, "members": region.members + (page.order[0],)})
    page.regions.append(tampered)

    result = assess_page(plan, page, blocks)
    assert result.status == STATUS_REJECT
    assert result.fallback_reason == "duplicate_membership"


def test_container_members_are_mapped_once_and_never_lost() -> None:
    blocks = [
        _block("caption", (80, 120, 600, 150), "table_caption", "Table 1. Values."),
        _block("table", (80, 180, 900, 460), "table_html", "<table></table>"),
        _block("after", (80, 520, 600, 600), text="Following paragraph."),
    ]
    plan = build_layout_plan(blocks)
    page = plan.pages[0]
    result = assess_page(plan, page, blocks)

    assert result.status == STATUS_ACCEPT
    mapped = [uid for uid in result.accepted_order if uid in result.source_mapping]
    assert sorted(mapped) == sorted(result.source_mapping)
    container_uids = [uid for region in page.regions if region.kind == "container" for uid in region.members]
    assert container_uids, "the table should be modelled as a container"
    for uid in container_uids:
        assert result.accepted_order.count(uid) == 1


def test_failed_acceptance_leaves_plan_and_blocks_untouched() -> None:
    blocks = _weak_two_column_page()
    plan = build_layout_plan(blocks)
    plan_before = copy.deepcopy(plan.to_dict())
    blocks_before = copy.deepcopy(blocks)

    result = assess_page(plan, plan.pages[0], blocks)

    assert result.status == STATUS_HOLD
    assert plan.to_dict() == plan_before
    assert blocks == blocks_before


def test_reordering_the_input_keeps_the_accepted_order() -> None:
    blocks = _single_column_page()
    plan = build_layout_plan(blocks)
    shuffled = [blocks[2], blocks[0], blocks[1]]

    forward = assess_page(plan, plan.pages[0], blocks)
    backward = assess_page(plan, plan.pages[0], shuffled)

    assert forward.status == backward.status == STATUS_ACCEPT
    assert forward.accepted_order == backward.accepted_order
    assert forward.source_mapping != backward.source_mapping  # indices moved...


def test_assess_plan_returns_one_entry_per_page() -> None:
    blocks = _single_column_page() + [
        _block("d", (80, 100, 600, 140), text="Page two.", page=2),
    ]
    plan = build_layout_plan(blocks)
    results = assess_plan(plan, blocks)
    assert [result.page for result in results] == [1, 2]


def test_figure_caption_identity_is_undetermined_when_block_ids_repeat() -> None:
    blocks = [
        _block("dup", (80, 100, 600, 140), "figure_caption", "Caption one."),
        _block("dup", (80, 700, 600, 740), "figure_asset", ""),
    ]
    plan = build_layout_plan(blocks)
    inventory = {
        "matched_figures": [
            {"page": 1, "legend_block_id": "dup", "matched_assets": [{"block_id": "dup", "page": 1}]}
        ]
    }
    metrics = evaluate_plan(plan, blocks, inventory)
    caption = metrics["figure_caption"]
    assert caption["matched"] == 0
    assert caption["undetermined"] >= 1
