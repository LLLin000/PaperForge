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


def test_build_spine_health() -> None:
    from paperforge.worker.ocr_health import build_spine_health

    body_spine = {
        "_meta": {
            "quality": "strong",
            "anchor_pages": [3, 4, 5],
            "sample_count": 12,
            "font_coherence": 0.92,
            "width_dispersion": 0.15,
        },
    }
    result = build_spine_health(body_spine)
    assert result["body_spine_quality"] == "strong"
    assert result["body_anchor_pages"] == [3, 4, 5]
    assert result["body_spine_sample_count"] == 12

    # Missing _meta defaults
    empty = build_spine_health({})
    assert empty["body_spine_quality"] == "weak"
    assert empty["body_anchor_pages"] == []
    assert empty["body_spine_sample_count"] == 0


def test_build_span_coverage_health() -> None:
    from paperforge.worker.ocr_health import build_span_coverage_health

    blocks = [
        {"span_metadata": {"size": 10}},
        {"span_metadata": {"size": 10}},
        {"span_metadata": None},
    ]
    result = build_span_coverage_health(blocks)
    assert result["coverage_ratio"] == 2 / 3
    assert result["coverage_quality"] == "moderate"
    assert result["blocks_with_span"] == 2
    assert result["blocks_without_span"] == 1
    assert result["degraded_mode_active"] is False

    # Empty blocks
    empty = build_span_coverage_health([])
    assert empty["degraded_mode_active"] is True
    assert empty["coverage_quality"] == "weak"


def test_layout_audit_health_surface() -> None:
    from paperforge.worker.ocr_health import build_layout_audit_health

    audit = {
        "status": "warn",
        "page_warnings": {"3": ["heading owns body in different column above it"]},
        "anomaly_count": 1,
        "anomaly_pages": [3],
    }
    result = build_layout_audit_health(audit)
    assert result["layout_audit_status"] == "warn"
    assert result["layout_anomaly_pages"] == [3]
    assert result["layout_anomaly_count"] == 1

    empty = build_layout_audit_health({})
    assert empty["layout_audit_status"] == "unknown"
    assert empty["layout_anomaly_pages"] == []
    assert empty["layout_anomaly_count"] == 0


def test_ocr_health_includes_span_spine_and_layout_signals() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    blocks = [
        {"role": "section_heading", "span_metadata": [{"font": "Body"}]},
        {"role": "section_heading", "span_metadata": [{"font": "Body"}]},
        {"role": "abstract_body", "span_metadata": [{"font": "Body"}]},
        {"role": "reference_item", "span_metadata": [{"font": "Body"}]},
    ]

    health = build_ocr_health(page_count=2, raw_blocks_count=4, structured_blocks=blocks, figure_inventory={}, table_inventory={})

    assert "span_coverage_quality" in health
    assert "body_spine_quality" in health
    assert "layout_audit_status" in health


def test_ocr_health_includes_decision_counts() -> None:
    from paperforge.worker.ocr_decisions import record_decision
    from paperforge.worker.ocr_health import build_ocr_health

    blocks = [{"block_id": "a", "page": 1, "role": "body_paragraph", "bbox": [0, 0, 1, 1]}]
    record_decision(blocks[0], stage="rescue", old_role="noise", new_role="body_paragraph", reason="body family")
    report = build_ocr_health(page_count=1, raw_blocks_count=1, structured_blocks=blocks, figure_inventory={}, table_inventory={})
    assert report["role_mutation_count"] == 1
    assert report["role_rescue_count"] == 1


def test_ocr_health_includes_tail_boundary_confidence() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    structured_blocks = [
        {"role": "section_heading", "text": "1 Introduction"},
        {"role": "body_paragraph", "text": "Body"},
        {"role": "reference_heading", "text": "References"},
        {"role": "reference_item", "text": "1. Author."},
    ]
    figure_inventory = {
        "matched_figures": [],
        "unmatched_legends": [],
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
    assert "tail_boundary_confidence" in report
    assert isinstance(report["tail_boundary_confidence"], (int, float))


def test_ocr_health_includes_confidence_distributions() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    structured_blocks = [
        {"role": "section_heading", "text": "1 Introduction"},
        {"role": "body_paragraph", "text": "Body"},
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "caption_score": {"score": 0.9, "decision": "figure_caption", "evidence": ["figure_number"]},
            },
            {
                "figure_id": "figure_002",
                "caption_score": {"score": 0.5, "decision": "figure_caption_candidate", "evidence": []},
            },
            {
                "figure_id": "figure_003",
                "caption_score": {"score": 0.3, "decision": "rejected", "evidence": []},
            },
        ],
        "unmatched_legends": [],
        "unmatched_assets": [],
    }
    table_inventory = {
        "tables": [
            {"match_score": {"score": 0.85, "decision": "matched", "evidence": ["same_page"]}},
            {"match_score": {"score": 0.40, "decision": "ambiguous", "evidence": []}},
            {"match_score": {"score": 0.20, "decision": "ambiguous", "evidence": []}},
        ],
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
    assert "figure_match_confidence_distribution" in report
    assert "table_match_confidence_distribution" in report
    assert "tail_boundary_confidence" in report

    fig_dist = report["figure_match_confidence_distribution"]
    assert fig_dist["high"] == 1
    assert fig_dist["medium"] == 1
    assert fig_dist["low"] == 1

    tbl_dist = report["table_match_confidence_distribution"]
    assert tbl_dist["high"] == 1
    assert tbl_dist["medium"] == 1
    assert tbl_dist["low"] == 1


def test_health_report_includes_degraded_reasons() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=0,
        structured_blocks=[],
        figure_inventory={},
        table_inventory={},
    )

    assert "degraded_reasons" in report
    assert len(report["degraded_reasons"]) > 0
