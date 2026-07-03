from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_passes import CrossPageReservationPass, CrossPageSettlementPass, PrimarySamePagePass
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger
from paperforge.worker.ocr_figure_vnext_types import ResourceRef


def test_primary_same_page_pass_matches_single_safe_group():
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].claim_type == "match"
    assert len(state.matches) == 1


def test_primary_same_page_pass_prefers_higher_score_when_two_legends_compete_for_one_asset(monkeypatch):
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 1, "role": "figure_caption", "text": "Figure 2. Caption", "bbox": [0, 160, 200, 210]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    if not index.candidate_groups:
        index.candidate_groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset", "cluster_bbox": [0, 0, 200, 90]}]

    scores = [{"score": 0.4, "decision": "matched", "evidence": ["low"]}, {"score": 0.9, "decision": "matched", "evidence": ["high"]}]

    def fake_score(*args, **kwargs):
        return scores.pop(0)

    monkeypatch.setattr("paperforge.worker.ocr_figures._score_legend_to_group", fake_score)
    monkeypatch.setattr("paperforge.worker.ocr_figures.score_figure_caption", lambda *a, **k: {"score": 0.9})

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].figure_no == 2


def test_primary_same_page_pass_ignores_previous_page_locator(monkeypatch):
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Fig. 1 (See legend on previous page).", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 1, "role": "figure_caption", "text": "Figure 2. Caption", "bbox": [0, 160, 200, 210]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    if not index.candidate_groups:
        index.candidate_groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset", "cluster_bbox": [0, 0, 200, 90]}]

    monkeypatch.setattr("paperforge.worker.ocr_figures._score_legend_to_group", lambda *a, **k: {"score": 0.9, "decision": "matched", "evidence": [""]})
    monkeypatch.setattr("paperforge.worker.ocr_figures.score_figure_caption", lambda *a, **k: {"score": 0.9})

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)

    # Only the non-locator caption should match
    assert len(report.accepted) == 1
    assert report.accepted[0].figure_no == 2


def test_primary_same_page_pass_unnumbered_formal_caption_does_not_crash(monkeypatch):
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure. Detailed description of the experimental results showing significant differences between groups.", "bbox": [0, 100, 500, 200]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    if not index.candidate_groups:
        index.candidate_groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset", "cluster_bbox": [0, 0, 200, 90]}]

    monkeypatch.setattr("paperforge.worker.ocr_figures._score_legend_to_group", lambda *a, **k: {"score": 0.9, "decision": "matched", "evidence": [""]})
    monkeypatch.setattr("paperforge.worker.ocr_figures.score_figure_caption", lambda *a, **k: {"score": 0.9})

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].figure_no is None
    assert len(state.matches) == 1
    # Must produce figure_unknown_* id, not crash
    assert state.matches[0]["figure_id"].startswith("figure_unknown_")
    assert state.matches[0]["figure_number"] is None


def test_cross_page_reservation_pass_reserves_forward_group_when_same_page_primary_misses():
    """Legend on page 1, group on page 2; same-page pass misses, reservation pass reserves."""
    blocks = [
        {"block_id": "l1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 2, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Same-page pass should NOT match — group is on a different page
    primary_report = PrimarySamePagePass().run(state)
    assert len(primary_report.accepted) == 0

    # Cross-page reservation pass should reserve the forward group
    report = CrossPageReservationPass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].claim_type == "reserve"
    assert len(state.reservations) == 1

    # The reserved group should be marked as reserved in the ledger.
    # Use the auto-generated group_id from the index.
    actual_group_id = index.candidate_groups[0]["group_id"]
    group_ref = ResourceRef(kind="group", page=2, block_id=None, group_id=actual_group_id)
    assert state.ledger.can_claim_group(group_ref) is False


def test_cross_page_reservation_pass_does_not_reserve_group_already_claimed_same_page(monkeypatch):
    """Legend already matched by same-page pass should be skipped by reservation pass."""
    blocks = [
        {"block_id": "l1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    if not index.candidate_groups:
        index.candidate_groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset", "cluster_bbox": [0, 0, 200, 90]}]

    monkeypatch.setattr("paperforge.worker.ocr_figures._score_legend_to_group", lambda *a, **k: {"score": 0.9, "decision": "matched", "evidence": [""]})
    monkeypatch.setattr("paperforge.worker.ocr_figures.score_figure_caption", lambda *a, **k: {"score": 0.9})

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Same-page pass should match
    primary_report = PrimarySamePagePass().run(state)
    assert len(primary_report.accepted) == 1
    assert len(state.matches) == 1

    # Cross-page reservation pass should skip already-matched legend
    report = CrossPageReservationPass().run(state)

    assert len(report.accepted) == 0
    assert len(state.reservations) == 0
def test_cross_page_settlement_pass_claims_reserved_group_into_match_record():
    """Reservation pass reserves, settlement pass claims and adds match record."""
    blocks = [
        {"block_id": "l1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 2, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Run same-page pass (should miss — group is on different page)
    PrimarySamePagePass().run(state)
    assert len(state.matches) == 0

    # Run reservation pass to create a reservation
    reservation_report = CrossPageReservationPass().run(state)
    assert len(state.reservations) == 1
    assert len(reservation_report.accepted) == 1

    # Run settlement pass to claim the reserved group
    report = CrossPageSettlementPass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].claim_type == "match"

    # Check that a match record was added with the right settlement_type
    new_matches = [m for m in state.matches if m.get("settlement_type") == "cross_page_reservation"]
    assert len(new_matches) == 1
    assert str(new_matches[0].get("legend_block_id", "")) == "l1"
    assert new_matches[0].get("page") == 1

    # Verify report contents
    assert "cross_page_settlement" in str(report.pass_name)


def test_cross_page_settlement_pass_keeps_same_page_matches_untouched():
    """Settlement pass with no reservations preserves existing same-page matches."""
    blocks = [
        {"block_id": "l1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    from unittest.mock import patch

    with patch("paperforge.worker.ocr_figures._score_legend_to_group", return_value={"score": 0.9, "decision": "matched", "evidence": [""]}):
        with patch("paperforge.worker.ocr_figures.score_figure_caption", return_value={"score": 0.9}):
            corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
            index = FigureCandidateIndex.from_corpus(corpus)
            if not index.candidate_groups:
                index.candidate_groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset", "cluster_bbox": [0, 0, 200, 90]}]

            state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

            # Same-page pass matches
            primary_report = PrimarySamePagePass().run(state)
            assert len(primary_report.accepted) == 1
            assert len(state.matches) == 1

            # Settlement pass with no reservations should not add matches
            report = CrossPageSettlementPass().run(state)

            assert len(report.accepted) == 0
            # Same-page match preserved
            assert len(state.matches) == 1
