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


def test_figure_match_score_prefers_same_page_overlap() -> None:
    from paperforge.worker.ocr_scores import score_figure_match

    legend = {"block_id": "cap1", "page": 2, "bbox": [100, 500, 700, 540]}
    asset = {"block_id": "fig1", "page": 2, "bbox": [120, 120, 680, 480]}

    result = score_figure_match(legend, asset, caption_score={"score": 0.8})

    assert result["decision"] == "matched"
    assert result["matched_asset_id"] == "fig1"
    assert result["score"] >= 0.6
    assert "same_page" in result["evidence"]
    assert "x_overlap" in result["evidence"]


def test_figure_match_score_rejects_low_caption_score() -> None:
    from paperforge.worker.ocr_scores import score_figure_match

    legend = {"block_id": "cap1", "page": 2, "bbox": [100, 500, 700, 540]}
    asset = {"block_id": "fig1", "page": 2, "bbox": [120, 120, 680, 480]}

    result = score_figure_match(legend, asset, caption_score={"score": 0.2})

    assert result["decision"] == "rejected"
    assert result["score"] < 0.4
    assert "low_caption_score" in result["evidence"]


def test_structured_insert_score_uses_multiple_evidence_terms() -> None:
    from paperforge.worker.ocr_scores import score_structured_insert

    block = {"text": "Box 1. Key points", "role": "body_paragraph", "_in_visual_container": True, "bbox": [50, 100, 400, 180], "page_width": 1200}

    result = score_structured_insert(block, body_spine_match=False, cluster_coherent=True)

    assert result["decision"] == "structured_insert"
    assert result["score"] >= 0.7
    assert "visual_container" in result["evidence"]
    assert "box_or_summary_keyword" in result["evidence"]


def test_structured_insert_score_keeps_visual_container_alone_as_candidate() -> None:
    from paperforge.worker.ocr_scores import score_structured_insert

    block = {"text": "Ordinary paragraph text", "role": "body_paragraph", "_in_visual_container": True, "bbox": [100, 100, 900, 180], "page_width": 1200}

    result = score_structured_insert(block, body_spine_match=True, cluster_coherent=False)

    assert result["decision"] != "structured_insert"
    assert result["score"] < 0.7
