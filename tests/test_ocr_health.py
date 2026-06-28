from __future__ import annotations


def test_health_counts_all_heading_tiers_and_requires_stronger_reference_evidence() -> None:
    from paperforge.worker.ocr_health import build_ocr_health
    structured_blocks = [
        {"role": "section_heading", "text": "Intro"},
        {"role": "subsection_heading", "text": "Methods"},
        {"role": "sub_subsection_heading", "text": "2.1 Setup"},
        {"role": "body_paragraph", "raw_label": "reference_content", "text": "[1] weak raw label"},
    ]
    health = build_ocr_health(
        page_count=1, raw_blocks_count=4,
        structured_blocks=structured_blocks,
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": [], "figure_legend_completeness": {}},
        table_inventory={"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": []},
        reader_payload=None, rendered_markdown=None,
    )
    assert health["section_heading_count"] == 3
    assert health["references_found"] is False


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

    health = build_ocr_health(
        page_count=2, raw_blocks_count=4, structured_blocks=blocks, figure_inventory={}, table_inventory={}
    )

    assert "span_coverage_quality" in health
    assert "body_spine_quality" in health
    assert "layout_audit_status" in health


def test_ocr_health_includes_decision_counts() -> None:
    from paperforge.worker.ocr_decisions import record_decision
    from paperforge.worker.ocr_health import build_ocr_health

    blocks = [{"block_id": "a", "page": 1, "role": "body_paragraph", "bbox": [0, 0, 1, 1]}]
    record_decision(blocks[0], stage="rescue", old_role="noise", new_role="body_paragraph", reason="body family")
    report = build_ocr_health(
        page_count=1, raw_blocks_count=1, structured_blocks=blocks, figure_inventory={}, table_inventory={}
    )
    assert report["role_mutation_count"] == 1
    assert report["role_rescue_count"] == 1


def test_ocr_health_reports_anchor_first_authority_summaries() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_health import build_ocr_health

    doc = DocumentStructure(
        body_family_anchor={"status": "ACCEPT"},
        reference_family_anchor={"status": "ACCEPT"},
        region_bus={
            "body_zone": {"status": "ACCEPT", "block_ids": ["p2_b1"]},
            "reference_zone": {"status": "ACCEPT", "block_ids": ["p5_b2"]},
        },
    )
    blocks = [
        {"block_id": "p2_b1", "role": "body_paragraph", "text": "Body", "page": 2, "bbox": [0, 0, 10, 10]},
        {"block_id": "p5_b2", "role": "reference_item", "text": "[1] Ref", "page": 5, "bbox": [0, 0, 10, 10]},
    ]

    report = build_ocr_health(
        page_count=5,
        raw_blocks_count=2,
        structured_blocks=blocks,
        figure_inventory={},
        table_inventory={},
        doc_structure=doc,
    )

    assert report["anchor_summary"]["body_family_anchor"] == "ACCEPT"
    assert report["anchor_summary"]["reference_family_anchor"] == "ACCEPT"
    assert report["zone_summary"]["reference_zone"] == "ACCEPT"


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


def test_ocr_health_reports_layout_confidence_distribution() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, PageLayoutProfile
    from paperforge.worker.ocr_health import build_ocr_health

    doc = DocumentStructure(
        page_layouts={
            1: PageLayoutProfile(confidence=0.8),
            2: PageLayoutProfile(confidence=0.5),
            3: PageLayoutProfile(confidence=0.2),
        }
    )

    report = build_ocr_health(
        page_count=3,
        raw_blocks_count=3,
        structured_blocks=[
            {"role": "abstract_body"},
            {"role": "reference_item"},
            {"role": "section_heading"},
            {"role": "section_heading"},
        ],
        figure_inventory={},
        table_inventory={},
        doc_structure=doc,
    )

    assert report["layout_confidence_distribution"] == {"high": 1, "medium": 1, "low": 1}


def test_ocr_health_counts_low_confidence_insert_candidates() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=2,
        structured_blocks=[
            {
                "role": "structured_insert_candidate",
                "insert_score": {"score": 0.45, "decision": "structured_insert_candidate"},
            },
            {"role": "structured_insert", "insert_score": {"score": 0.35, "decision": "body"}},
            {"role": "abstract_body"},
            {"role": "reference_item"},
            {"role": "section_heading"},
            {"role": "section_heading"},
        ],
        figure_inventory={},
        table_inventory={},
    )

    assert report["low_confidence_insert_candidate_count"] == 1
    assert report["candidate_forced_count"] == 1


def test_ocr_health_counts_ambiguous_and_low_confidence_tables() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[
            {"role": "abstract_body"},
            {"role": "reference_item"},
            {"role": "section_heading"},
            {"role": "section_heading"},
        ],
        figure_inventory={},
        table_inventory={
            "tables": [
                {
                    "has_asset": False,
                    "is_continuation": False,
                    "match_status": "ambiguous",
                    "match_score": {"score": 0.5},
                },
                {
                    "has_asset": True,
                    "is_continuation": False,
                    "match_status": "matched_low_confidence",
                    "match_score": {"score": 0.45},
                },
            ]
        },
    )

    assert report["ambiguous_table_match_count"] == 1
    assert report["low_confidence_table_match_count"] == 1


def test_ocr_health_reports_hard_rule_and_uncertainty_summary() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, PageLayoutProfile
    from paperforge.worker.ocr_health import build_ocr_health

    doc = DocumentStructure(page_layouts={1: PageLayoutProfile(confidence=0.25)})
    doc.tail_boundary_score = {"score": 0.35}

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=6,
        structured_blocks=[
            {"role": "structured_insert", "insert_score": {"score": 0.35}},
            {"role": "abstract_body"},
            {"role": "reference_item"},
            {"role": "section_heading"},
            {"role": "section_heading"},
        ],
        figure_inventory={
            "matched_figures": [{"caption_score": {"score": 0.3}}],
            "ambiguous_figures": [{"legend_block_id": "cap1"}],
            "unresolved_clusters": [{"cluster_id": "unresolved_cluster_001"}],
        },
        table_inventory={
            "tables": [
                {
                    "match_status": "ambiguous",
                    "match_score": {"score": 0.5},
                    "has_asset": False,
                    "is_continuation": False,
                }
            ]
        },
        doc_structure=doc,
    )

    assert report["low_score_but_matched_count"] >= 1
    assert report["ambiguous_match_count"] >= 2
    assert report["unresolved_cluster_count"] == 1
    assert report["candidate_forced_count"] >= 1
    assert report["low_tail_boundary_confidence"] is True


def test_ocr_health_has_hard_rule_decision_count_key() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[
            {"role": "abstract_body"},
            {"role": "reference_item"},
            {"role": "section_heading"},
            {"role": "section_heading"},
        ],
        figure_inventory={},
        table_inventory={},
    )

    assert "hard_rule_decision_count" in report
    assert isinstance(report["hard_rule_decision_count"], int)


def test_ocr_health_hard_rule_decision_count_uses_real_signals() -> None:
    from paperforge.worker.ocr_decisions import record_decision
    from paperforge.worker.ocr_health import build_ocr_health

    blocks = [
        {"block_id": "a", "page": 1, "role": "structured_insert", "insert_score": {"score": 0.35}},
        {"block_id": "b", "page": 1, "role": "abstract_body"},
        {"block_id": "c", "page": 1, "role": "reference_item"},
        {"block_id": "d", "page": 1, "role": "section_heading"},
        {"block_id": "e", "page": 1, "role": "section_heading"},
    ]
    record_decision(
        blocks[0],
        stage="structured_insert_promotion",
        old_role="body_paragraph",
        new_role="structured_insert",
        reason="forced fallback",
    )
    record_decision(
        blocks[0],
        stage="tail_candidate_resolution",
        old_role="tail_candidate_body",
        new_role="reference_item",
        reason="tail ownership",
    )

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=len(blocks),
        structured_blocks=blocks,
        figure_inventory={},
        table_inventory={},
    )

    assert report["hard_rule_decision_count"] >= 2


def test_health_reports_anchor_zone_and_hold_statuses() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=2,
        raw_blocks_count=3,
        structured_blocks=[],
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": []},
        table_inventory={"tables": [], "held_tables": [], "unmatched_assets": [], "unmatched_captions": []},
        doc_structure={
            "anchor_summary": {"reference_family_anchor": "ACCEPT", "body_family_anchor": "ACCEPT"},
            "zone_summary": {"reference_zone": "ACCEPT", "body_zone": "ACCEPT"},
            "held_counts": {"families": 1, "matches": 0},
        },
    )

    assert "anchor_summary" in report
    assert "zone_summary" in report
    assert "held_counts" in report


def test_health_counts_held_figures_and_tables() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[
            {"role": "abstract_body"},
            {"role": "reference_item"},
            {"role": "section_heading"},
            {"role": "section_heading"},
        ],
        figure_inventory={
            "matched_figures": [],
            "held_figures": [{"figure_id": "held_figure_001"}],
            "unmatched_legends": [],
            "unmatched_assets": [],
        },
        table_inventory={
            "tables": [],
            "held_tables": [{"table_id": "held_table_001"}],
            "unmatched_assets": [],
            "unmatched_captions": [],
        },
    )

    assert report["held_figure_count"] == 1
    assert report["held_table_count"] == 1
    assert report["held_match_count"] == 2


def test_role_gate_health_corrections_are_not_errors() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_health import build_ocr_health

    role_gate_summary = {
        "status": "healthy",
        "corrected_structural_seed_count": 3,
        "held_structural_seed_count": 0,
        "final_unverified_structural_role_count": 0,
        "seed_role_passthrough_count": 0,
        "abstract_body_outside_span_count": 0,
        "reference_item_outside_reference_zone_count": 0,
    }
    doc = DocumentStructure()
    doc.role_gate_summary = role_gate_summary

    structured_blocks = [
        {"role": "section_heading", "text": "Introduction"},
        {"role": "section_heading", "text": "Methods"},
        {"role": "abstract_body", "text": "Abstract."},
        {"role": "reference_item", "text": "Ref."},
    ]
    health = build_ocr_health(
        page_count=1,
        raw_blocks_count=len(structured_blocks),
        structured_blocks=structured_blocks,
        figure_inventory={"matched_figures": [], "unmatched_legends": [], "unmatched_assets": []},
        table_inventory={"tables": [], "unmatched_captions": [], "unmatched_assets": []},
        doc_structure=doc,
    )

    assert "role_gate_summary" in health
    assert health["role_gate_summary"]["corrected_structural_seed_count"] == 3
    assert health["overall"] != "red"


def test_role_gate_health_degrades_on_passthrough() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    role_gate_summary = {
        "status": "degraded",
        "corrected_structural_seed_count": 0,
        "held_structural_seed_count": 2,
        "final_unverified_structural_role_count": 2,
        "seed_role_passthrough_count": 2,
        "abstract_body_outside_span_count": 1,
        "reference_item_outside_reference_zone_count": 1,
    }
    health = build_ocr_health(
        page_count=1,
        raw_blocks_count=0,
        structured_blocks=[],
        figure_inventory={},
        table_inventory={},
        doc_structure={"role_gate_summary": role_gate_summary},
    )

    assert "role_gate_summary" in health
    assert health["role_gate_summary"]["status"] == "degraded"


def test_ocr_health_role_gate_degraded_forces_overall_red() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    role_gate_summary = {
        "status": "degraded",
        "corrected_structural_seed_count": 0,
        "held_structural_seed_count": 1,
        "final_unverified_structural_role_count": 1,
        "seed_role_passthrough_count": 1,
        "abstract_body_outside_span_count": 0,
        "reference_item_outside_reference_zone_count": 0,
    }
    health = build_ocr_health(
        page_count=1,
        raw_blocks_count=0,
        structured_blocks=[],
        figure_inventory={},
        table_inventory={},
        doc_structure={"role_gate_summary": role_gate_summary},
    )

    assert health["overall"] == "red"


def test_ocr_health_exposes_completeness_signals_for_runtime_blocks() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=2,
        structured_blocks=[
            {
                "role": "body_paragraph",
                "text": "short text",
                "page": 1,
                "pdf_text": "short text plus a much longer native PDF segment that should dominate coverage",
                "pdf_region_text": "short text plus a much longer native PDF segment that should dominate coverage",
            },
            {"role": "section_heading", "text": "Intro"},
            {"role": "section_heading", "text": "Methods"},
            {"role": "reference_item", "text": "[1] Ref"},
            {"role": "abstract_body", "text": "Abstract."},
        ],
        figure_inventory={},
        table_inventory={},
    )

    assert report["page_text_coverage"][1]["page_text_coverage_status"] == "low"
    assert report["text_completeness_summary"]["short_vs_pdf"] == 1


def test_ocr_health_marks_missing_pdf_baseline_without_perfect_ratio() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[
            {"role": "body_paragraph", "text": "Body text", "page": 1, "pdf_text": ""},
            {"role": "section_heading", "text": "Intro"},
            {"role": "section_heading", "text": "Methods"},
            {"role": "reference_item", "text": "[1] Ref"},
            {"role": "abstract_body", "text": "Abstract."},
        ],
        figure_inventory={},
        table_inventory={},
    )

    coverage = report["page_text_coverage"][1]
    assert coverage["page_text_coverage_status"] == "missing_pdf_text"
    assert coverage["page_text_coverage_ratio_chars"] is None


def test_rendered_text_coverage_normalizes_whitespace_and_case() -> None:
    from paperforge.worker.ocr_health import audit_rendered_text_coverage

    result = audit_rendered_text_coverage(
        rendered_markdown="In  Vivo methods are summarized here.",
        pdf_segments=["in vivo methods are summarized here."],
    )

    assert result["rendered_text_gap_count"] == 0


def test_ocr_health_reports_rendered_gap_count_when_markdown_is_provided() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[
            {"role": "body_paragraph", "text": "Short OCR body.", "page": 1, "pdf_region_text": "A long methods segment that is missing from render."},
            {"role": "section_heading", "text": "Intro"},
            {"role": "section_heading", "text": "Methods"},
            {"role": "reference_item", "text": "[1] Ref"},
            {"role": "abstract_body", "text": "Abstract."},
        ],
        figure_inventory={},
        table_inventory={},
        rendered_markdown="Only the introduction survived.",
    )

    assert report["rendered_text_gap_count"] == 1


def test_health_emits_additive_v2_fields_without_replacing_overall() -> None:
    from paperforge.worker.ocr_health import build_ocr_health
    health = build_ocr_health(
        page_count=1, raw_blocks_count=0,
        structured_blocks=[{"role": "section_heading", "text": "Intro"}],
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": [], "figure_legend_completeness": {}},
        table_inventory={"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": []},
        reader_payload=None, rendered_markdown=None,
    )
    assert "overall" in health
    assert "heading_total_v2" in health
    assert "matched_figure_count_v2" in health
    assert "issue_breakdown_v2" in health
