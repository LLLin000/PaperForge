from __future__ import annotations


def test_figure_caption_score_returns_evidence() -> None:
    from paperforge.worker.ocr_scores import score_figure_caption

    block = {"role": "figure_caption_candidate", "text": "Figure 1. Cell migration assay", "page": 1, "bbox": [100, 500, 800, 540]}
    result = score_figure_caption(block, nearby_media=True, caption_style_match=True)
    assert result["decision"] == "figure_caption"
    assert result["score"] >= 0.7
    assert "figure_number" in result["evidence"]


def test_table_match_score_prefers_same_page_overlap() -> None:
    from paperforge.worker.ocr_scores import score_table_match

    caption = {"text": "Table 1. Baseline characteristics", "page": 2, "bbox": [100, 100, 700, 140]}
    asset = {"block_id": "t1", "page": 2, "bbox": [100, 160, 700, 500]}
    result = score_table_match(caption, asset)
    assert result["decision"] == "matched"
    assert result["matched_asset_id"] == "t1"
    assert result["score"] >= 0.7


def test_tail_boundary_score_returns_reason_list() -> None:
    from paperforge.worker.ocr_scores import score_tail_boundary

    result = score_tail_boundary(forward_body_end=8, backward_backmatter_start=9, references_start={"page": 10})
    assert result["score"] >= 0.7
    assert result["body_end_page"] == 8
    assert result["reason"]
