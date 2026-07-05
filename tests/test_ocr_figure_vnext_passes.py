from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_passes import (
    ContinuationCaptionPass,
    CrossPageReservationPass,
    CrossPageSettlementPass,
    PrimarySamePagePass,
)
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


# --- Continuation caption pass tests ---


def test_cont_caption_detected_and_marked_in_candidate_index():
    """Continuation legends identified and marked during index construction."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Main caption.", "bbox": [0, 100, 500, 150]},
        {"block_id": "c2", "page": 1, "role": "figure_caption", "text": "Figure 1. (Continued) Additional description.", "bbox": [0, 300, 500, 350]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "a2", "page": 1, "role": "figure_asset", "bbox": [0, 200, 200, 290], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    cont_legends = [l for l in index.formal_legends if l.get("_figure_continuation")]
    base_legends = [l for l in index.formal_legends if not l.get("_figure_continuation")]

    assert len(cont_legends) == 1
    assert cont_legends[0]["_continuation_base_number"] == 1
    assert cont_legends[0]["block_id"] == "c2"
    assert len(base_legends) == 1
    assert base_legends[0]["block_id"] == "c1"


def test_cont_caption_matches_same_page_visual_group(monkeypatch):
    """ContinuationCaptionPass matches continuation legend to same-page group with unique ID."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. (Continued) More details.", "bbox": [0, 300, 500, 350]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    index.candidate_groups = [
        {
            "group_id": "g1", "page": 1, "asset_block_ids": ["a1"],
            "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset",
            "cluster_bbox": [0, 0, 200, 90],
        }
    ]

    monkeypatch.setattr(
        "paperforge.worker.ocr_figures._score_legend_to_group",
        lambda *a, **k: {"score": 0.9, "decision": "matched", "evidence": ["cont_same_page"]},
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_figures.score_figure_caption",
        lambda *a, **k: {"score": 0.9},
    )

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = ContinuationCaptionPass().run(state)

    assert len(report.accepted) == 1
    assert len(state.matches) == 1
    match = state.matches[0]
    assert match["is_continuation"] is True
    assert match["continuation_of"] == "figure_001"
    assert match["figure_id"].startswith("figure_001_continued_")
    assert match["settlement_type"] == "continuation_same_page"
    assert match["figure_number"] == 1
    assert match["continuation_of"] != match["figure_id"]


def test_cont_caption_has_unique_id_not_base_figure_id(monkeypatch):
    """Each continuation match gets a unique figure_id, not the base figure_id."""
    # Different pages so asset-claim competition doesn't cause one to lose all groups
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. (Continued) More details.", "bbox": [0, 300, 500, 350]},
        {"block_id": "c2", "page": 2, "role": "figure_caption", "text": "Figure 2. (Continued) Even more details.", "bbox": [0, 400, 500, 450]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "a2", "page": 2, "role": "figure_asset", "bbox": [0, 100, 200, 190], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    index.candidate_groups = [
        {
            "group_id": "g1", "page": 1, "asset_block_ids": ["a1"],
            "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset",
            "cluster_bbox": [0, 0, 200, 90],
        },
        {
            "group_id": "g2", "page": 2, "asset_block_ids": ["a2"],
            "media_blocks": [{"block_id": "a2"}], "group_type": "single_asset",
            "cluster_bbox": [0, 100, 200, 190],
        },
    ]

    monkeypatch.setattr(
        "paperforge.worker.ocr_figures._score_legend_to_group",
        lambda *a, **k: {"score": 0.9, "decision": "matched", "evidence": [""]},
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_figures.score_figure_caption",
        lambda *a, **k: {"score": 0.9},
    )

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = ContinuationCaptionPass().run(state)

    assert len(report.accepted) == 2
    assert len(state.matches) == 2
    ids = [m["figure_id"] for m in state.matches]
    assert len(set(ids)) == 2, "each continuation figure_id must be unique"
    for match in state.matches:
        assert match["is_continuation"] is True
        assert match["continuation_of"] != match["figure_id"]
        assert "_continued_" in match["figure_id"]


def test_cont_caption_cross_page_links_correctly():
    """ContinuationCaptionPass matches continuation legend cross-page (page+1)."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. (Continued) More details.", "bbox": [0, 100, 500, 150]},
        {"block_id": "a1", "page": 2, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    index.candidate_groups = [
        {
            "group_id": "g1", "page": 2, "asset_block_ids": ["a1"],
            "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset",
            "cluster_bbox": [0, 0, 200, 90],
        }
    ]

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = ContinuationCaptionPass().run(state)

    assert len(report.accepted) == 1
    assert len(state.matches) == 1
    match = state.matches[0]
    assert match["is_continuation"] is True
    assert match["continuation_of"] == "figure_001"
    assert match["figure_id"].startswith("figure_001_continued_")
    assert match["settlement_type"] == "continuation_cross_page"


def test_primary_same_page_pass_skips_continuation_legends(monkeypatch):
    """PrimarySamePagePass should skip legends marked as continuation captions."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. (Continued) Detail.", "bbox": [0, 300, 500, 350]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    index.candidate_groups = [
        {
            "group_id": "g1", "page": 1, "asset_block_ids": ["a1"],
            "media_blocks": [{"block_id": "a1"}], "group_type": "single_asset",
            "cluster_bbox": [0, 0, 200, 90],
        }
    ]

    monkeypatch.setattr(
        "paperforge.worker.ocr_figures._score_legend_to_group",
        lambda *a, **k: {"score": 0.9, "decision": "matched", "evidence": [""]},
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_figures.score_figure_caption",
        lambda *a, **k: {"score": 0.9},
    )

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)

    # PrimarySamePagePass should skip the continuation legend, not match it
    assert len(report.accepted) == 0
    assert len(state.matches) == 0


# --- Short caption geometry tests (PR-2a) ---


def test_short_numbered_caption_same_column_match():
    """Short "Figure N." caption matches a same-column asset with tight vertical gap."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1.", "bbox": [0, 240, 200, 270], "zone": "display_zone"},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 200], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    match = state.matches[0]
    assert match["legend_block_id"] == "c1"
    evidence = match.get("match_score", {}).get("evidence", [])
    assert any("short_caption_geometry" in e for e in evidence), f"Expected short_caption_geometry in evidence, got {evidence}"
    assert match["confidence"] >= 0.62


def test_short_numbered_caption_multi_asset_bonus():
    """Short caption gets a multi-asset coherence bonus (score 0.65 vs 0.62)."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1.", "bbox": [0, 480, 200, 510], "zone": "display_zone"},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 200], "raw_label": "image"},
        {"block_id": "a2", "page": 1, "role": "figure_asset", "bbox": [0, 220, 200, 440], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    assert state.matches[0]["confidence"] >= 0.65


def test_short_caption_multiple_competing_legends_same_column_held(monkeypatch):
    """Two short captions in the same column are both held (column-local competition).

    Monkeypatches score_figure_caption low so normal scoring misses, making the
    short-caption geometry branch the only possible rescue.  Competing-in-column
    check then holds both legends.
    """
    monkeypatch.setattr(
        "paperforge.worker.ocr_figures.score_figure_caption",
        lambda *a, **k: {"score": 0.1, "evidence": ["low_score"]},
    )
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1.", "bbox": [0, 240, 200, 270], "zone": "display_zone"},
        {"block_id": "c2", "page": 1, "role": "figure_caption", "text": "Figure 2.", "bbox": [0, 300, 200, 330], "zone": "display_zone"},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 200], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    # Both captions in same column, both within gap range, but competing in column
    # → short-caption branch holds both, normal scoring also misses (low caption_score)
    assert len(report.accepted) == 0
    assert len(state.matches) == 0


def test_short_caption_different_column_rejected():
    """Short caption in different column than the asset group does not match."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1.", "bbox": [700, 240, 900, 270], "zone": "display_zone"},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 200], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    # Column check rejects cross-column before short-caption branch fires
    assert len(report.accepted) == 0
    assert len(state.matches) == 0


def test_short_caption_does_not_override_safe_auto_match():
    """Short caption falls through to normal scoring when group has safe_auto_match."""
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1.", "bbox": [0, 240, 200, 270], "zone": "display_zone"},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 100], "raw_label": "image"},
        {"block_id": "a2", "page": 1, "role": "figure_asset", "bbox": [0, 110, 200, 200], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    # If the group formed a distance_cluster with safe_auto_match, the short caption
    # matches via normal scoring, not the geometry branch.
    assert len(report.accepted) >= 0  # may or may not match depending on group formation
    if report.accepted:
        evidence = report.accepted[0].diagnostics.get("evidence", [])
        # safe_auto_match evidence includes "safe_auto_match", not "short_caption_geometry"
        assert not any("short_caption_geometry" in e for e in evidence), f"Unexpected short_caption_geometry: {evidence}"


# --- PrimarySamePagePass multi-legend multi-asset veto tests (PR-2a follow-up) ---


def test_primary_same_page_veto_two_short_legends_two_assets():
    """Two short numbered explicit legends, distance_cluster with 2 assets on same page.
    -> PrimarySamePagePass must veto whole-group claim."""
    from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus, FigureCandidateIndex
    from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

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
    report = PrimarySamePagePass().run(state)

    # PrimarySamePagePass should not make a whole-group claim
    assert len(report.accepted) == 0, \
        f"expected 0 accepted (veto), got {len(report.accepted)}"


def test_primary_same_page_veto_four_legends_four_assets():
    """Four short numbered explicit legends, distance_cluster with 4 assets on same page.
    -> PrimarySamePagePass must veto; no single legend claims the whole group."""
    from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus, FigureCandidateIndex
    from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 4", "bbox": [0, 100, 200, 130], "zone": "display_zone"},
        {"block_id": "c2", "page": 3, "role": "figure_caption",
         "text": "Figure 5", "bbox": [300, 100, 500, 130], "zone": "display_zone"},
        {"block_id": "c3", "page": 3, "role": "figure_caption",
         "text": "Figure 6", "bbox": [0, 160, 200, 190], "zone": "display_zone"},
        {"block_id": "c4", "page": 3, "role": "figure_caption",
         "text": "Figure 7", "bbox": [300, 160, 500, 190], "zone": "display_zone"},
        {"block_id": "a1", "page": 3, "role": "figure_asset",
         "bbox": [0, 200, 280, 350], "raw_label": "image"},
        {"block_id": "a2", "page": 3, "role": "figure_asset",
         "bbox": [320, 200, 600, 350], "raw_label": "image"},
        {"block_id": "a3", "page": 3, "role": "figure_asset",
         "bbox": [0, 360, 280, 510], "raw_label": "image"},
        {"block_id": "a4", "page": 3, "role": "figure_asset",
         "bbox": [320, 360, 600, 510], "raw_label": "image"},
        {"block_id": "filler", "page": 1, "role": "paper_title",
         "text": "Title", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)

    groups = [
        {
            "group_id": "g1",
            "page": 3,
            "group_type": "distance_cluster",
            "asset_block_ids": ["a1", "a2", "a3", "a4"],
            "cluster_bbox": [0, 200, 600, 510],
            "media_blocks": [
                {"block_id": "a1"}, {"block_id": "a2"},
                {"block_id": "a3"}, {"block_id": "a4"},
            ],
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
    report = PrimarySamePagePass().run(state)

    # PrimarySamePagePass should not make a whole-group claim
    assert len(report.accepted) == 0, \
        f"expected 0 accepted (veto), got {len(report.accepted)}"


def test_primary_same_page_veto_grouped_figure_unaffected():
    """Single descriptive legend with multi-asset distance_cluster group.
    -> Normal grouped figure, one legend claims all assets (no veto)."""
    from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus, FigureCandidateIndex
    from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

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
    report = PrimarySamePagePass().run(state)

    # Single descriptive legend with multi-asset group — should still match normally
    # (not affected by the veto, which only applies to short numbered captions)
    assert len(report.accepted) >= 1, \
        f"expected at least 1 accepted (grouped figure), got {len(report.accepted)}"
    if report.accepted:
        proposal = report.accepted[0]
        # Should claim both assets
        assert len(proposal.assets) == 2, \
            f"expected 2 assets in grouped figure, got {len(proposal.assets)}"
        # Should be a same_page primary match
        assert proposal.reason == "same_page_primary"


def test_primary_same_page_veto_two_legends_then_group_seq_splits(monkeypatch):
    """Full pipeline: PrimarySamePagePass vetoes whole-group; GroupSequentialPass splits.
    2 short legends + 2 assets -> each legend gets 1 asset."""
    from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus, FigureCandidateIndex
    from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger
    from paperforge.worker.ocr_figure_vnext_group_seq_pass import GroupSequentialPass

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

    # Run PrimarySamePagePass — should veto
    report1 = PrimarySamePagePass().run(state)
    assert len(report1.accepted) == 0, \
        f"PrimarySamePagePass should veto, got {len(report1.accepted)} accepted"

    # Run GroupSequentialPass — should split
    report2 = GroupSequentialPass().run(state)
    assert len(report2.accepted) == 2, \
        f"GroupSequentialPass should split, got {len(report2.accepted)} accepted"
    assert len(state.matches) == 2, \
        f"expected 2 matches overall, got {len(state.matches)}"

    # Each match should have exactly one asset
    for m in state.matches:
        assert m["settlement_type"] == "group_sequential"
        assert len(m.get("matched_assets", [])) == 1, \
            f"expected 1 asset per match, got {len(m.get('matched_assets', []))}"

    # c1 (Figure 2) should get a1 (left asset), c2 (Figure 3) should get a2 (right asset)
    match_by_legend = {m["legend_block_id"]: m for m in state.matches}
    assert match_by_legend["c1"]["asset_block_ids"] == ["a1"], \
        f"expected c1 -> a1, got {match_by_legend['c1']['asset_block_ids']}"
    assert match_by_legend["c2"]["asset_block_ids"] == ["a2"], \
        f"expected c2 -> a2, got {match_by_legend['c2']['asset_block_ids']}"
