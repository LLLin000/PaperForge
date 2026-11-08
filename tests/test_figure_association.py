from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus


from paperforge.worker.ocr_figure_vnext_passes import (
    CrossPageReservationPass,
    CrossPageSettlementPass,
    PrimarySamePagePass,
)


from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_side_by_side_same_row_matches():
    blocks = [
        {"block_id": "cap", "page": 1, "role": "figure_caption", "text": "Fig. 4 Caption", "bbox": [96, 114, 327, 256]},
        {"block_id": "asset", "page": 1, "role": "figure_asset", "bbox": [373, 119, 1092, 762], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)
    assert len(report.accepted) == 1
    assert state.matches[0]["legend_block_id"] == "cap"
    assert state.matches[0]["asset_block_ids"] == ["asset"]
    assert "side_adjacent" in state.matches[0]["match_score"]["evidence"]


def test_side_by_side_negative_far_above():
    blocks = [
        {"block_id": "cap", "page": 1, "role": "figure_caption", "text": "Fig. 4 Caption", "bbox": [96, 10, 327, 60]},
        {"block_id": "asset", "page": 1, "role": "figure_asset", "bbox": [373, 119, 1092, 762], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)
    assert len(report.accepted) == 0


def test_side_by_side_negative_closer_caption():
    blocks = [
        {"block_id": "cap_far", "page": 1, "role": "figure_caption", "text": "Fig. 4 Caption", "bbox": [96, 114, 327, 256]},
        {"block_id": "cap_close", "page": 1, "role": "figure_caption", "text": "Fig. 5 Caption", "bbox": [360, 119, 500, 200]},
        {"block_id": "asset", "page": 1, "role": "figure_asset", "bbox": [373, 119, 1092, 762], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)
    # asset should not be claimed by the farther caption
    matched = [m for m in state.matches if "asset" in (m.get("asset_block_ids") or [])]
    assert all(m["legend_block_id"] != "cap_far" for m in matched)


def test_page_qualified_duplicate_block_ids():
    blocks = [
        {"block_id": "dup", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "dup", "page": 2, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "cap", "page": 2, "role": "figure_caption", "text": "Fig. 5 Caption", "bbox": [80, 113, 583, 357]},
        {"block_id": "body", "page": 2, "role": "body_paragraph", "bbox": [0, 1000, 100, 1020], "text": "x"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    # page-qualified: two distinct assets despite same block_id
    ids = [(g.get("page"), g.get("asset_block_ids")) for g in index.candidate_groups]
    assert len(index.candidate_groups) == 2
    assert (1, ["dup"]) in [(g.get("page"), g.get("asset_block_ids")) for g in index.candidate_groups]
    assert (2, ["dup"]) in [(g.get("page"), g.get("asset_block_ids")) for g in index.candidate_groups]
