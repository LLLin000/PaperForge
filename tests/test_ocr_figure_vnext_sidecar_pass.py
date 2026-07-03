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
