from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_classic_seq_pass import (
    ClassicSequentialPass,
    UnresolvedClusterConsolidation,
)
from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_classic_sequential_match_unmatched_caption_to_forward_asset():
    """Unmatched numbered caption on page 3, ungrouped asset on page 4 →
    ClassicSequentialPass creates a sequential match in reading order.
    """
    blocks = [
        {"block_id": "l1", "page": 3, "role": "figure_caption",
         "text": "Figure 99. Caption text here.", "bbox": [0, 100, 800, 150]},
        {"block_id": "a1", "page": 4, "role": "figure_asset",
         "bbox": [0, 0, 400, 300]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    # Ensure asset is ungrouped — no candidate groups
    index.candidate_groups = []
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = ClassicSequentialPass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].claim_type == "match"
    assert report.accepted[0].figure_no == 99
    assert report.accepted[0].confidence == 0.35
    assert report.accepted[0].evidence_rank == 6
    assert report.accepted[0].reason == "sequential_match"
    assert len(state.matches) == 1
    m = state.matches[0]
    assert m["settlement_type"] == "sequential"
    assert m["confidence"] == 0.35
    assert "sequential_match" in m["flags"]
    assert m["figure_number"] == 99
    assert m["legend_block_id"] == "l1"
    assert m["page"] == 4  # asset page


def test_classic_sequential_previous_page_guard_prevents_match():
    """Numbered caption on page 3, asset on page 2, but
    _allow_previous_page_sequential_match returns False (zone is not
    post_reference) → no match created.
    """
    blocks = [
        {"block_id": "l1", "page": 3, "role": "figure_caption",
         "text": "Figure 99. Caption text here.", "bbox": [0, 100, 800, 150]},
        {"block_id": "a1", "page": 2, "role": "figure_asset",
         "bbox": [100, 1000, 500, 1100]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    index.candidate_groups = []
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = ClassicSequentialPass().run(state)

    # The previous-page guard should reject the match because the caption zone
    # is not 'post_reference_backmatter_zone' or 'display_zone'.
    assert len(report.accepted) == 0
    assert len(state.matches) == 0


def test_unresolved_cluster_consolidation_builds_cluster_on_rejected_page():
    """Two unmatched figure_asset blocks on a page with rejected legends →
    UnresolvedClusterConsolidation creates one cluster in state.unresolved.
    """
    blocks = [
        {"block_id": "a1", "page": 2, "role": "figure_asset",
         "bbox": [0, 0, 200, 100]},
        # a2 placed close enough to a1 (15px gap) for _media_clusters to merge
        {"block_id": "a2", "page": 2, "role": "figure_asset",
         "bbox": [0, 115, 200, 215]},
        # A short caption that will be rejected (not a formal legend)
        {"block_id": "r1", "page": 2, "role": "figure_caption",
         "text": "blah blah", "bbox": [0, 0, 100, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Confirm r1 is in rejected_legends
    assert any(b.get("block_id") == "r1" for b in index.rejected_legends)

    report = UnresolvedClusterConsolidation().run(state)

    assert len(state.unresolved) == 1
    cluster = state.unresolved[0]
    assert len(cluster["media_block_ids"]) == 2
    assert "a1" in cluster["media_block_ids"]
    assert "a2" in cluster["media_block_ids"]
    assert cluster["page"] == 2
    assert cluster["cluster_id"].startswith("unresolved_cluster_")
    # cluster_bbox should span both assets
    assert cluster["cluster_bbox"][1] == 0     # y1 = min(0, 115) = 0
    assert cluster["cluster_bbox"][3] == 215   # y2 = max(100, 215) = 215
    assert len(report.accepted) == 1
    assert report.accepted[0].claim_type == "unresolved_cluster"
