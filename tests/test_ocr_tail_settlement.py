from __future__ import annotations


def test_promote_backmatter_heading_candidates_promotes_same_page_followers() -> None:
    from paperforge.worker.ocr_tail_settlement import promote_backmatter_heading_candidates

    blocks = [
        {
            "block_id": "h1",
            "page": 10,
            "role": "backmatter_heading_candidate",
            "seed_role": "backmatter_heading_candidate",
            "text": "Funding",
            "bbox": [100, 100, 260, 130],
        },
        {
            "block_id": "b1",
            "page": 10,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "This work was supported by Grant A.",
            "bbox": [100, 150, 520, 220],
        },
        {
            "block_id": "b2",
            "page": 10,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "The funders had no role in study design.",
            "bbox": [100, 230, 520, 300],
        },
    ]

    promote_backmatter_heading_candidates(blocks)

    assert blocks[0]["role"] == "backmatter_heading"
    assert blocks[1]["role"] == "backmatter_body"
    assert blocks[2]["role"] == "backmatter_body"


def test_settle_tail_and_backmatter_preserves_tail_hold_restore() -> None:
    from paperforge.worker.ocr_tail_settlement import settle_tail_and_backmatter

    blocks = [
        {
            "block_id": "h1",
            "page": 11,
            "role": "section_heading",
            "zone": "tail_nonref_hold_zone",
            "style_family": "heading_like",
            "marker_signature": {"type": "heading_numbered"},
            "text": "5. Conclusions",
        },
        {
            "block_id": "b1",
            "page": 11,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "zone": "tail_nonref_hold_zone",
            "text": "Funding: supported by Grant A.",
        },
        {
            "block_id": "b2",
            "page": 11,
            "role": "backmatter_body",
            "zone": "tail_nonref_hold_zone",
            "style_family": "body_like",
            "marker_signature": {"type": "none"},
            "text": "This section returns to the main conclusions.",
        },
    ]

    report = settle_tail_and_backmatter(structured_blocks=blocks, document_structure=None)

    # The exclude pass converts funding text to backmatter_body, but the
    # numbered heading restore pass then converts ALL backmatter_body blocks
    # back to body_paragraph when active_numbered_body is True.
    # Both end up as body_paragraph.
    assert blocks[1]["role"] == "body_paragraph"
    assert blocks[2]["role"] == "body_paragraph"
    # b1 converted by exclude, both b1 and b2 restored by restore pass
    assert report.promoted_backmatter_heading_ids == []
    assert report.converted_to_backmatter_body_ids == ["b1"]
    assert sorted(report.restored_body_paragraph_ids) == ["b1", "b2"]
    assert report.applied_count == 3


def test_tail_settlement_report_accumulates_operations() -> None:
    from paperforge.worker.ocr_tail_settlement import (
        TailSettlementReport,
        promote_backmatter_heading_candidates,
        exclude_tail_nonref_from_body_flow,
    )

    blocks = [
        {
            "block_id": "h1",
            "page": 10,
            "role": "backmatter_heading_candidate",
            "seed_role": "backmatter_heading_candidate",
            "text": "Funding",
            "bbox": [100, 100, 260, 130],
        },
        {
            "block_id": "b1",
            "page": 10,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "zone": "tail_nonref_hold_zone",
            "text": "Funding: supported by Grant A.",
            "bbox": [100, 150, 520, 220],
        },
    ]

    report = TailSettlementReport()
    promote_backmatter_heading_candidates(blocks, report=report)
    exclude_tail_nonref_from_body_flow(blocks, report=report)

    assert report.promoted_backmatter_heading_ids == ["h1"]
    assert report.converted_to_backmatter_body_ids == ["b1"]
