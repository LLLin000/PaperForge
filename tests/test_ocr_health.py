from __future__ import annotations


def test_health_report_is_independent_from_ocr_status() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    structured_blocks = [
        {"role": "section_heading", "text": "1 Introduction"},
        {"role": "body_paragraph", "text": "Body"},
        {"role": "figure_caption", "text": "Figure 1. Example"},
    ]
    figure_inventory = {
        "matched_figures": [],
        "unmatched_legends": [{"text": "Figure 1. Example"}],
        "unmatched_assets": [],
    }
    table_inventory = {
        "tables": [],
        "unmatched_captions": [],
        "unmatched_assets": [],
    }

    report = build_ocr_health(
        page_count=3,
        raw_blocks_count=20,
        structured_blocks=structured_blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert report["page_count"] == 3
    assert report["figure_caption_count"] == 1
    assert report["overall"] in {"yellow", "red"}
