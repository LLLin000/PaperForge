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


def test_multi_legend_veto_two_legends_two_assets():
    """Two short numbered explicit legends, distance_cluster with 2 assets on same page.
    -> whole-group vetoed, each legend claims one asset by position."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 2", "bbox": [0, 100, 200, 130], "zone": "display_zone"},
        {"block_id": "c2", "page": 5, "role": "figure_caption",
         "text": "Figure 3", "bbox": [300, 100, 500, 130], "zone": "display_zone"},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [0, 200, 250, 400], "raw_label": "image"},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [300, 200, 550, 400], "raw_label": "image"},
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
            "cluster_bbox": [0, 200, 550, 400],
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

    # Both legends should have been matched (one each, no whole-group claim)
    assert len(report.accepted) == 2, f"expected 2 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 2, f"expected 2 matches, got {len(state.matches)}"

    # Each match should have exactly one asset
    for m in state.matches:
        assert m["settlement_type"] == "group_sequential"
        assert "group_sequential_match" in m["flags"]
        assert len(m.get("matched_assets", [])) == 1, \
            f"expected 1 asset per match, got {len(m.get('matched_assets', []))}"

    # c1 (Figure 2) should get a1 (left asset), c2 (Figure 3) should get a2 (right asset)
    match_by_legend = {m["legend_block_id"]: m for m in state.matches}
    assert match_by_legend["c1"]["asset_block_ids"] == ["a1"], \
        f"expected c1 -> a1, got {match_by_legend['c1']['asset_block_ids']}"
    assert match_by_legend["c2"]["asset_block_ids"] == ["a2"], \
        f"expected c2 -> a2, got {match_by_legend['c2']['asset_block_ids']}"


def test_multi_legend_veto_grouped_figure_no_veto():
    """Single descriptive legend + multi-asset distance_cluster.
    -> normal grouped figure, one legend claims all assets (no veto)."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 2. Overview of system architecture. (A) Input (B) Processing.",
         "bbox": [0, 100, 500, 150]},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [0, 200, 250, 400], "raw_label": "image"},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [300, 200, 550, 400], "raw_label": "image"},
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
            "cluster_bbox": [0, 200, 550, 400],
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

    # Single descriptive legend → normal grouped figure, both assets claimed
    assert len(report.accepted) == 1, f"expected 1 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 1, f"expected 1 match, got {len(state.matches)}"

    match = state.matches[0]
    assert match["settlement_type"] == "group_sequential"
    assert "group_sequential_match" in match["flags"]
    assert match["legend_block_id"] == "c1"

    matched_bids = {a["block_id"] for a in match.get("matched_assets", [])}
    assert matched_bids == {"a1", "a2"}, f"expected a1,a2, got {matched_bids}"


def test_multi_legend_veto_ambiguous_no_veto():
    """Two short legends but group has 3 assets (n_legends < n_assets).
    -> no veto; first legend claims the whole group."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 2", "bbox": [0, 100, 200, 130], "zone": "display_zone"},
        {"block_id": "c2", "page": 5, "role": "figure_caption",
         "text": "Figure 3", "bbox": [300, 100, 500, 130], "zone": "display_zone"},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [0, 200, 180, 300], "raw_label": "image"},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [200, 200, 380, 300], "raw_label": "image"},
        {"block_id": "a3", "page": 5, "role": "figure_asset",
         "bbox": [400, 200, 580, 300], "raw_label": "image"},
        {"block_id": "filler", "page": 1, "role": "paper_title",
         "text": "Title", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)

    groups = [
        {
            "group_id": "g1",
            "page": 5,
            "group_type": "distance_cluster",
            "asset_block_ids": ["a1", "a2", "a3"],
            "cluster_bbox": [0, 200, 580, 300],
            "media_blocks": [{"block_id": "a1"}, {"block_id": "a2"}, {"block_id": "a3"}],
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

    # 2 legends < 3 assets → no veto, first legend takes all
    assert len(report.accepted) == 1, f"expected 1 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 1, f"expected 1 match, got {len(state.matches)}"

    match = state.matches[0]
    assert match["settlement_type"] == "group_sequential"
    assert match["legend_block_id"] == "c1"

    matched_bids = {a["block_id"] for a in match.get("matched_assets", [])}
    assert matched_bids == {"a1", "a2", "a3"}, f"expected a1,a2,a3, got {matched_bids}"
