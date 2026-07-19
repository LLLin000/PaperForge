from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_passes import PrimarySamePagePass
from paperforge.worker.ocr_figure_vnext_sidecar_pass import SidecarPass
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger
from paperforge.worker.ocr_figure_vnext_types import ResourceRef


def test_sidecar_pass_matches_narrow_captions_to_asset_bands(monkeypatch):
    """Three narrow captions on page 5 with three assets at different y-bands.

    PrimarySamePagePass misses (monkeypatched scoring), SidecarPass rescues
    each narrow caption into a sidecar match.
    """
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. First caption", "bbox": [100, 100, 300, 130]},
        {"block_id": "c2", "page": 5, "role": "figure_caption",
         "text": "Figure 2. Second caption", "bbox": [100, 300, 310, 330]},
        {"block_id": "c3", "page": 5, "role": "figure_caption",
         "text": "Figure 3. Third caption", "bbox": [100, 500, 300, 530]},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [50, 0, 250, 90]},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [50, 180, 260, 270]},
        {"block_id": "a3", "page": 5, "role": "figure_asset",
         "bbox": [60, 400, 270, 480]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    assert 5 in index.sidecar_candidates
    assert len(index.sidecar_candidates[5]) == 3

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Ensure PrimarySamePagePass misses — narrow captions score poorly for same-page
    monkeypatch.setattr(
        "paperforge.worker.ocr_figures._score_legend_to_group",
        lambda *a, **k: {"score": 0.0, "decision": "missed", "evidence": []},
    )
    PrimarySamePagePass().run(state)

    report = SidecarPass().run(state)

    assert len(report.accepted) >= 1
    sidecar_matches = [m for m in state.matches if m.get("settlement_type") == "sidecar"]
    assert len(sidecar_matches) >= 1

    matched_ids = {m.get("legend_block_id") for m in sidecar_matches}
    assert matched_ids == {"c1", "c2", "c3"}

    for match in sidecar_matches:
        assert len(match.get("matched_assets", [])) >= 1
        assert "sidecar_match" in match.get("flags", [])


def test_sidecar_pass_skips_pages_with_fewer_than_two_narrow_captions():
    """Single narrow caption on a page — no sidecar_candidates entry."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. Only caption", "bbox": [100, 100, 300, 130]},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [50, 0, 250, 90]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    assert 5 not in index.sidecar_candidates

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = SidecarPass().run(state)

    assert len(report.accepted) == 0



def test_single_narrow_sidecar_rescue_fires_for_left_caption_right_image():
    """Single narrow left caption with same-row right image → sidecar rescued."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. Narrow caption with image to the right",
         "bbox": [100, 100, 300, 200]},   # narrow, left column
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [320, 100, 600, 250]},   # right of caption, same-row
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    # The single narrow caption must now appear in sidecar_candidates
    assert 5 in index.sidecar_candidates
    assert len(index.sidecar_candidates[5]) == 1
    assert index.sidecar_candidates[5][0]["block_id"] == "c1"

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = SidecarPass().run(state)

    assert len(report.accepted) >= 1
    sidecar_matches = [m for m in state.matches if m.get("settlement_type") == "sidecar"]
    assert len(sidecar_matches) == 1
    assert sidecar_matches[0].get("legend_block_id") == "c1"
    assert len(sidecar_matches[0].get("matched_assets", [])) >= 1
    assert "sidecar_match" in sidecar_matches[0].get("flags", [])


def test_single_narrow_sidecar_no_rescue_when_no_row_coupled_asset():
    """Single narrow caption whose asset is not row-coupled → not rescued."""
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. Narrow caption",
         "bbox": [100, 300, 300, 340]},   # narrow, below asset
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [50, 0, 250, 90]},       # above, no y-overlap
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    assert 5 not in index.sidecar_candidates

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = SidecarPass().run(state)
    assert len(report.accepted) == 0


def test_single_narrow_sidecar_does_not_break_grouped_baseline():
    """Three narrow captions plus single narrow caption — grouped baseline intact."""
    blocks = [
        # Three grouped narrow captions on page 5 (existing multi-caption path)
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. First", "bbox": [100, 100, 300, 130]},
        {"block_id": "c2", "page": 5, "role": "figure_caption",
         "text": "Figure 2. Second", "bbox": [100, 300, 310, 330]},
        {"block_id": "c3", "page": 5, "role": "figure_caption",
         "text": "Figure 3. Third", "bbox": [100, 500, 300, 530]},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [50, 0, 250, 90]},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [50, 180, 260, 270]},
        {"block_id": "a3", "page": 5, "role": "figure_asset",
         "bbox": [60, 400, 270, 480]},
        # Single narrow caption on page 6 with row-coupled asset (37-like)
        {"block_id": "c4", "page": 6, "role": "figure_caption",
         "text": "Figure 4. Side rescued", "bbox": [100, 200, 280, 350]},
        {"block_id": "a4", "page": 6, "role": "figure_asset",
         "bbox": [300, 200, 600, 380]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    # Page 5: the three grouped captions still form a sidecar candidate
    assert 5 in index.sidecar_candidates
    assert len(index.sidecar_candidates[5]) == 3
    assert {b["block_id"] for b in index.sidecar_candidates[5]} == {"c1", "c2", "c3"}

    # Page 6: single caption rescued via the 37-like path
    assert 6 in index.sidecar_candidates
    assert len(index.sidecar_candidates[6]) == 1
    assert index.sidecar_candidates[6][0]["block_id"] == "c4"

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = SidecarPass().run(state)

    sidecar_matches = [m for m in state.matches if m.get("settlement_type") == "sidecar"]
    assert len(sidecar_matches) == 4  # all four rescued

    page5_matches = [m for m in sidecar_matches if m.get("page") == 5]
    page6_matches = [m for m in sidecar_matches if m.get("page") == 6]
    assert len(page5_matches) == 3
    assert len(page6_matches) == 1
    assert page6_matches[0].get("legend_block_id") == "c4"

def test_sidecar_pass_does_not_steal_assets_from_protected_same_page_matches():
    """Two narrow captions on page 5; c1 already has a protected same-page match.

    SidecarPass should skip c1 and match only c2.
    """
    blocks = [
        {"block_id": "c1", "page": 5, "role": "figure_caption",
         "text": "Figure 1. Protected", "bbox": [100, 100, 300, 130]},
        {"block_id": "c2", "page": 5, "role": "figure_caption",
         "text": "Figure 2. Available", "bbox": [100, 300, 310, 330]},
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [50, 0, 250, 90]},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [50, 180, 260, 270]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    assert 5 in index.sidecar_candidates
    assert len(index.sidecar_candidates[5]) == 2

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Pre-populate a protected same-page match for c1
    c1_ref = ResourceRef(kind="legend", page=5, block_id="c1", figure_no=1)
    a1_ref = ResourceRef(kind="asset", page=5, block_id="a1")
    state.ledger.try_claim_assets([a1_ref], owner=c1_ref, reason="same_page_primary")
    state.matches.append({
        "legend_block_id": "c1",
        "settlement_type": "same_page",
        "matched_assets": [{"block_id": "a1"}],
        "flags": [],
        "figure_number": 1,
    })

    report = SidecarPass().run(state)

    # c1 should be skipped (protected), c2 should get a sidecar match
    sidecar_matches = [m for m in state.matches if m.get("settlement_type") == "sidecar"]
    assert len(sidecar_matches) == 1
    assert sidecar_matches[0]["legend_block_id"] == "c2"
    assert len(sidecar_matches[0].get("matched_assets", [])) >= 1
