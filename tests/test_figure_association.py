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
def test_stacked_same_column_assets_match_caption_as_one_figure():
    blocks = [
        {"block_id": "top", "page": 1, "role": "figure_asset", "bbox": [120, 70, 598, 350], "raw_label": "chart"},
        {"block_id": "bottom", "page": 1, "role": "figure_asset", "bbox": [121, 390, 595, 689], "raw_label": "chart"},
        {"block_id": "polar", "page": 1, "role": "figure_asset", "bbox": [622, 68, 1104, 331], "raw_label": "chart"},
        {"block_id": "left_caption", "page": 1, "role": "figure_caption", "text": "Fig. 5 Panels (a) and (b) show the measured response.", "bbox": [115, 710, 606, 933]},
        {"block_id": "right_caption", "page": 1, "role": "figure_caption", "text": "Fig. 6 The polar plots show the measured displacement.", "bbox": [616, 346, 1106, 479]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    ids = {frozenset(group["asset_block_ids"]) for group in index.candidate_groups}
    assert frozenset({"top", "bottom"}) in ids
    assert frozenset({"polar"}) in ids

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    PrimarySamePagePass().run(state)
    owners = {match["legend_block_id"]: set(match["asset_block_ids"]) for match in state.matches}
    assert owners["left_caption"] == {"top", "bottom"}
    assert owners["right_caption"] == {"polar"}


def test_body_text_between_stacked_assets_keeps_groups_separate():
    blocks = [
        {"block_id": "top", "page": 1, "role": "figure_asset", "bbox": [120, 70, 598, 350], "raw_label": "chart"},
        {"block_id": "body", "page": 1, "role": "body_paragraph", "text": "An unrelated paragraph between the two visual assets.", "bbox": [150, 355, 570, 385]},
        {"block_id": "bottom", "page": 1, "role": "figure_asset", "bbox": [121, 390, 595, 689], "raw_label": "chart"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert {frozenset(group["asset_block_ids"]) for group in index.candidate_groups} == {
        frozenset({"top"}),
        frozenset({"bottom"}),
    }


def test_figure_grouping_does_not_change_table_claims():
    from paperforge.worker.ocr_tables import build_table_inventory

    blocks = [
        {"block_id": "cap", "page": 3, "role": "table_caption", "raw_label": "figure_title", "text": "Table 1 Dose response results", "bbox": [618, 67, 1106, 108]},
        {"block_id": "table", "page": 3, "role": "table_html", "raw_label": "table", "text": "<table><tr><td>x</td></tr></table>", "bbox": [621, 111, 1105, 275]},
        {"block_id": "chart_top", "page": 4, "role": "figure_asset", "raw_label": "chart", "bbox": [120, 70, 598, 350]},
        {"block_id": "chart_bottom", "page": 4, "role": "figure_asset", "raw_label": "chart", "bbox": [121, 390, 595, 689]},
    ]
    before = build_table_inventory(blocks)
    FigureCandidateIndex.from_corpus(FigureCorpus.from_blocks(blocks, page_width=1200))
    after = build_table_inventory(blocks)
    assert before == after
    assert [(row["caption_block_id"], row["asset_block_id"]) for row in after["tables"]] == [("cap", "table")]
