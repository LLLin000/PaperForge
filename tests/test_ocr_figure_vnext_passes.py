from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_passes import PrimarySamePagePass
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


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
