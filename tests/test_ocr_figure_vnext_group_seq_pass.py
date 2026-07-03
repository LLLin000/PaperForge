"""Tests for GroupSequentialPass.

Three scenarios:
1. Same-page group match with score >= 0.5
2. Next-page fallback when no same-page group exists
3. Previous-page guard denied (allow returns False)
"""

from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_group_seq_pass import GroupSequentialPass
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_group_sequential_same_page_match():
    """Unmatched legend + distance_cluster on same page, safe_auto_match score >= 0.5 → match."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. A test figure caption.", "bbox": [0, 100, 500, 150]},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [0, 200, 400, 300], "raw_label": "image"},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [0, 310, 400, 410], "raw_label": "image"},
        {"block_id": "filler", "page": 1, "role": "paper_title",
         "text": "Title", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)

    groups = [
        {
            "group_id": "g1",
            "page": 5,
            "group_type": "distance_cluster",
            "asset_block_ids": ["a1", "a2"],
            "cluster_bbox": [0, 200, 400, 410],
            "media_blocks": [{"block_id": "a1"}, {"block_id": "a2"}],
            "safe_auto_match": True,
        }
    ]

    index = FigureCandidateIndex(
        formal_legends=[b for b in blocks if b.get("role") == "figure_caption"],
        held_legends=[],
        rejected_legends=[],
        deduped_legends=[b for b in blocks if b.get("role") == "figure_caption"],
        candidate_groups=groups,
        competing_caption_pages=set(),
        sidecar_candidates={},
        bundle_source_legend_ids=set(),
        locator_candidates=[],
    )

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = GroupSequentialPass().run(state)

    assert len(report.accepted) == 1, f"expected 1 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 1, f"expected 1 match, got {len(state.matches)}"

    match = state.matches[0]
    assert match["settlement_type"] == "group_sequential"
    assert match["figure_number"] == 1
    assert match["legend_block_id"] == "c1"
    assert "group_sequential_match" in match["flags"]
    assert match["confidence"] == 0.45

    matched_bids = {a["block_id"] for a in match.get("matched_assets", [])}
    assert matched_bids == {"a1", "a2"}, f"expected a1,a2, got {matched_bids}"


def test_group_sequential_next_page_fallback():
    """Legend on page 3, group on page 4, no same-page group → match to page 4 group."""
    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. A test figure caption.", "bbox": [0, 100, 500, 150]},
        {"block_id": "a1", "page": 4, "role": "figure_asset",
         "bbox": [0, 200, 400, 300], "raw_label": "image"},
        {"block_id": "a2", "page": 4, "role": "figure_asset",
         "bbox": [0, 310, 400, 410], "raw_label": "image"},
        {"block_id": "filler", "page": 1, "role": "paper_title",
         "text": "Title", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)

    groups = [
        {
            "group_id": "g1",
            "page": 4,
            "group_type": "distance_cluster",
            "asset_block_ids": ["a1", "a2"],
            "cluster_bbox": [0, 200, 400, 410],
            "media_blocks": [{"block_id": "a1"}, {"block_id": "a2"}],
            "safe_auto_match": True,
        }
    ]

    index = FigureCandidateIndex(
        formal_legends=[b for b in blocks if b.get("role") == "figure_caption"],
        held_legends=[],
        rejected_legends=[],
        deduped_legends=[b for b in blocks if b.get("role") == "figure_caption"],
        candidate_groups=groups,
        competing_caption_pages=set(),
        sidecar_candidates={},
        bundle_source_legend_ids=set(),
        locator_candidates=[],
    )

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = GroupSequentialPass().run(state)

    assert len(report.accepted) == 1, f"expected 1 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 1, f"expected 1 match, got {len(state.matches)}"

    match = state.matches[0]
    assert match["settlement_type"] == "group_sequential"
    assert match["legend_block_id"] == "c1"
    assert match["page"] == 4
    assert "group_sequential_match" in match["flags"]

    matched_bids = {a["block_id"] for a in match.get("matched_assets", [])}
    assert matched_bids == {"a1", "a2"}, f"expected a1,a2, got {matched_bids}"


def test_group_sequential_prev_page_guard_denied(monkeypatch):
    """Legend on page 3, group on page 2, allow returns False → no match."""
    monkeypatch.setattr(
        "paperforge.worker.ocr_figures._allow_previous_page_sequential_match",
        lambda cap, asset: False,
    )

    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. A test figure caption.", "bbox": [0, 100, 500, 150]},
        {"block_id": "a1", "page": 2, "role": "figure_asset",
         "bbox": [0, 600, 400, 700], "raw_label": "image"},
        {"block_id": "filler", "page": 1, "role": "paper_title",
         "text": "Title", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)

    groups = [
        {
            "group_id": "g1",
            "page": 2,
            "group_type": "distance_cluster",
            "asset_block_ids": ["a1"],
            "cluster_bbox": [0, 600, 400, 700],
            "media_blocks": [{"block_id": "a1"}],
            "safe_auto_match": True,
        }
    ]

    index = FigureCandidateIndex(
        formal_legends=[b for b in blocks if b.get("role") == "figure_caption"],
        held_legends=[],
        rejected_legends=[],
        deduped_legends=[b for b in blocks if b.get("role") == "figure_caption"],
        candidate_groups=groups,
        competing_caption_pages=set(),
        sidecar_candidates={},
        bundle_source_legend_ids=set(),
        locator_candidates=[],
    )

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = GroupSequentialPass().run(state)

    assert len(report.accepted) == 0, f"expected 0 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 0, f"expected 0 matches, got {len(state.matches)}"
