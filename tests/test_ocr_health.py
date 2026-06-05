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


def test_health_report_distinguishes_formal_tables_from_segments() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    table_inventory = {
        "tables": [
            {"table_id": "tbl_001", "has_asset": True},
            {"table_id": "tbl_002", "has_asset": True},
        ],
        "unmatched_captions": [],
        "unmatched_assets": [
            {"asset_id": "seg_001"},
            {"asset_id": "seg_002"},
            {"asset_id": "seg_003"},
        ],
    }

    report = build_ocr_health(
        page_count=5,
        raw_blocks_count=50,
        structured_blocks=[],
        figure_inventory={},
        table_inventory=table_inventory,
    )

    assert report.get("formal_table_count", 0) == 2
    assert report.get("table_segment_count", 0) == 5
