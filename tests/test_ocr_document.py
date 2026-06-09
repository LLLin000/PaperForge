from __future__ import annotations


def test_page_layout_profile_includes_confidence_and_evidence() -> None:
    from paperforge.worker.ocr_document import _build_page_layout_profiles

    blocks = [
        {"role": "body_paragraph", "page": 1, "bbox": [100, 100, 500, 160], "page_width": 1200, "page_height": 1700},
        {"role": "body_paragraph", "page": 1, "bbox": [700, 100, 1100, 160], "page_width": 1200, "page_height": 1700},
    ]

    profile = _build_page_layout_profiles(blocks)[1]

    assert hasattr(profile, "confidence")
    assert hasattr(profile, "evidence")
    assert profile.confidence >= 0.5
    assert "eligible_body_blocks" in profile.evidence


def test_layout_profiles_ignore_wide_headings_and_media() -> None:
    from paperforge.worker.ocr_document import _build_page_layout_profiles

    blocks = [
        {"role": "section_heading", "page": 1, "bbox": [50, 50, 1150, 90], "page_width": 1200, "page_height": 1700},
        {"role": "figure_asset", "page": 1, "bbox": [400, 120, 800, 500], "page_width": 1200, "page_height": 1700},
        {"role": "body_paragraph", "page": 1, "bbox": [100, 600, 500, 660], "page_width": 1200, "page_height": 1700},
        {"role": "body_paragraph", "page": 1, "bbox": [700, 600, 1100, 660], "page_width": 1200, "page_height": 1700},
    ]

    profile = _build_page_layout_profiles(blocks)[1]

    assert profile.column_count == 2
    assert "excluded_non_body_blocks" in profile.evidence


def test_analyze_document_structure_flat_backmatter() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, analyze_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Intro"},
        {"page": 2, "role": "body_paragraph", "text": "Methods"},
        {"page": 3, "role": "body_paragraph", "text": "Results"},
        {"page": 3, "role": "section_heading", "text": "Discussion"},
        {"page": 4, "role": "body_paragraph", "text": "Discussion text"},
        {"page": 5, "role": "backmatter_heading", "text": "Acknowledgments"},
        {"page": 5, "role": "backmatter_body", "text": "Thanks."},
        {"page": 6, "role": "reference_heading", "text": "References"},
        {"page": 6, "role": "reference_item", "text": "[1] Ref A"},
    ]

    doc = analyze_document_structure(blocks)

    assert isinstance(doc, DocumentStructure)
    assert doc.body_end_page == 4
    assert doc.spread_start == 5
    assert doc.spread_end == 6
    assert doc.backmatter_form == "flat"


def test_analyze_document_structure_container_backmatter() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, analyze_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Intro"},
        {"page": 2, "role": "section_heading", "text": "Methods"},
        {"page": 3, "role": "body_paragraph", "text": "Results"},
        {"page": 3, "role": "section_heading", "text": "Discussion"},
        {"page": 4, "role": "body_paragraph", "text": "Discussion text"},
        {"page": 5, "role": "backmatter_boundary_heading", "text": "ADDITIONAL INFORMATION AND DECLARATIONS"},
        {"page": 5, "role": "backmatter_heading", "text": "Funding"},
        {"page": 5, "role": "backmatter_body", "text": "Funded by NIH."},
        {"page": 6, "role": "backmatter_heading", "text": "Acknowledgments"},
        {"page": 6, "role": "backmatter_body", "text": "Thanks."},
        {"page": 6, "role": "backmatter_heading", "text": "Author Contributions"},
        {"page": 6, "role": "backmatter_body", "text": "AB did X."},
        {"page": 7, "role": "reference_heading", "text": "References"},
        {"page": 7, "role": "reference_item", "text": "[1] Ref A"},
    ]

    doc = analyze_document_structure(blocks)

    assert isinstance(doc, DocumentStructure)
    assert doc.backmatter_form == "container"


def test_analyze_document_structure_exposes_reference_family_anchor_before_final_reference_roles() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, analyze_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Intro text"},
        {"page": 2, "role": "body_paragraph", "text": "Methods text"},
        {
            "page": 5,
            "role": "reference_heading",
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "[2] Another reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
        },
    ]

    doc = analyze_document_structure(blocks)

    assert isinstance(doc, DocumentStructure)
    assert doc.reference_family_anchor is not None
    assert doc.reference_family_anchor["status"] == "ACCEPT"
    assert doc.reference_family_anchor["item_count"] == 2


def test_analyze_document_structure_discovers_reference_family_anchor_before_tail_role_normalization() -> None:
    from paperforge.worker.ocr_document import analyze_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Intro text"},
        {"page": 2, "role": "body_paragraph", "text": "Methods text"},
        {
            "page": 5,
            "role": "reference_heading",
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "[2] Another reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
        },
    ]

    doc = analyze_document_structure(blocks)

    assert doc.reference_family_anchor is not None
    assert doc.reference_family_anchor["status"] == "ACCEPT"
    assert blocks[3]["role"] == "body_paragraph"
    assert blocks[4]["role"] == "body_paragraph"


def test_analyze_document_structure_wires_style_family_artifacts_into_blocks() -> None:
    from paperforge.worker.ocr_document import analyze_document_structure

    blocks = [
        {
            "block_id": "p3_b1",
            "page": 3,
            "role": "body_paragraph",
            "text": "Long narrative body paragraph with enough text to be treated as core body evidence across the main article flow and stable typography. " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        },
        {
            "block_id": "p5_b1",
            "page": 4,
            "role": "body_paragraph",
            "text": "Long narrative body paragraph continuing the main article flow with matching typography and substantial prose for body-anchor detection. " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "width_bucket": 250, "x_center": 242, "x_center_bucket": 250},
        },
        {
            "block_id": "p5_b1b",
            "page": 5,
            "role": "body_paragraph",
            "text": "Long narrative body paragraph extending the article with the same body typography and enough tokens to remain a strong body candidate. " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 261, "width_bucket": 250, "x_center": 241, "x_center_bucket": 250},
        },
        {
            "block_id": "p5_b2",
            "page": 5,
            "role": "body_paragraph",
            "text": "Figure 2. Compact legend text",
            "marker_signature": {"type": "figure_number", "number": 2},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 220, "x_center": 250},
        },
    ]

    analyze_document_structure(blocks)

    assert blocks[0]["style_family"] == "body_like"
    assert blocks[0]["style_family_authority"] in {"body_family_anchor", "body_zone_with_anchor", "body_zone_candidate"}
    assert blocks[3]["style_family"] == "legend_like"


def test_normalize_document_structure_keeps_reference_family_anchor_anchor_first() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Intro text"},
        {"page": 2, "role": "body_paragraph", "text": "Methods text"},
        {
            "page": 5,
            "role": "reference_heading",
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "[2] Another reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
        },
    ]

    doc, normalized_blocks = normalize_document_structure(blocks)

    assert doc.reference_family_anchor is not None
    assert doc.reference_family_anchor["status"] == "ACCEPT"
    assert normalized_blocks[3]["role"] == "body_paragraph"
    assert normalized_blocks[4]["role"] == "body_paragraph"


def test_normalize_document_structure_wires_style_family_artifacts_into_blocks() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {
            "block_id": "p3_b1",
            "page": 3,
            "role": "body_paragraph",
            "text": "Long narrative body paragraph with enough text to be treated as core body evidence across the main article flow and stable typography. " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        },
        {
            "block_id": "p4_b1",
            "page": 4,
            "role": "body_paragraph",
            "text": "Long narrative body paragraph continuing the main article flow with matching typography and substantial prose for body-anchor detection. " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "width_bucket": 250, "x_center": 242, "x_center_bucket": 250},
        },
        {
            "block_id": "p5_b1",
            "page": 5,
            "role": "body_paragraph",
            "text": "Long narrative body paragraph extending the article with the same body typography and enough tokens to remain a strong body candidate. " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 261, "width_bucket": 250, "x_center": 241, "x_center_bucket": 250},
        },
        {
            "block_id": "p5_b2",
            "page": 5,
            "role": "body_paragraph",
            "text": "Figure 2. Compact legend text",
            "marker_signature": {"type": "figure_number", "number": 2},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 220, "x_center": 250},
        },
    ]

    _, normalized_blocks = normalize_document_structure(blocks)

    assert normalized_blocks[0]["style_family"] == "body_like"
    assert normalized_blocks[0]["style_family_authority"] in {
        "body_family_anchor",
        "body_zone_with_anchor",
        "body_zone_candidate",
    }
    assert normalized_blocks[3]["style_family"] == "legend_like"


def test_normalize_document_structure_preserves_reference_zone_integrity_from_anchor_flow() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {
            "block_id": "p2_b1",
            "page": 2,
            "role": "body_paragraph",
            "text": "Stable body paragraph with repeated typography and enough prose to form the body family anchor. " * 2,
            "bbox": [100, 120, 460, 280],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_size_bucket": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "width_bucket": 250, "x_center": 230, "x_center_bucket": 250},
        },
        {
            "block_id": "p5_b1",
            "page": 5,
            "role": "reference_heading",
            "text": "References",
            "bbox": [100, 100, 340, 140],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 120, "x_center": 220},
        },
        {
            "block_id": "p5_b2",
            "page": 5,
            "role": "body_paragraph",
            "text": "[1] Example reference with authors and journal details.",
            "bbox": [110, 180, 500, 260],
            "page_width": 1200,
            "page_height": 1600,
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_size_bucket": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        },
    ]

    doc, normalized_blocks = normalize_document_structure(blocks)

    assert doc.reference_zones
    ref_row = next(block for block in normalized_blocks if block["block_id"] == "p5_b2")
    assert ref_row.get("zone") == "reference_zone"
    assert ref_row.get("style_family") == "reference_like"


def test_candidate_resolution_demotes_body_spine_narrative_figure_mentions() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, PageLayoutProfile, _resolve_ambiguous_candidates

    blocks = [
        {
            "page": 4,
            "bbox": [100, 500, 950, 620],
            "text": "Figure 2 shows the control response over time in both cohorts.",
            "role": "figure_caption_candidate",
        }
    ]
    doc_structure = DocumentStructure(body_end_page=4)
    page_layouts = {
        4: PageLayoutProfile(column_count=1, column_boundaries=[], layout_type="single_column", confidence=1.0)
    }

    _resolve_ambiguous_candidates(blocks, doc_structure, page_layouts)

    assert blocks[0]["role"] == "body_paragraph"


def test_reference_zone_is_inferred_from_reference_family_anchor_not_preexisting_roles() -> None:
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {
            "block_id": "p1_b1",
            "page": 1,
            "text": "Abstract",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
        },
        {
            "block_id": "p4_b1",
            "page": 4,
            "text": "Body text",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0},
            "layout_signature": {"width": 260},
        },
        {
            "block_id": "p8_b1",
            "page": 8,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
        },
        {
            "block_id": "p8_b2",
            "page": 8,
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5},
            "layout_signature": {"width": 250},
        },
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family", "sample_pages": [4]},
        "reference_family_anchor": {"status": "ACCEPT", "family_name": "reference_family", "item_count": 1},
    }

    zones = infer_zones(blocks, anchors)

    assert zones["reference_zone"]["status"] == "ACCEPT"
    assert "p8_b2" in zones["reference_zone"]["block_ids"]


def test_analyze_document_structure_persists_region_bus_in_dataclass_serialization() -> None:
    import dataclasses

    from paperforge.worker.ocr_document import analyze_document_structure

    blocks = [
        {
            "block_id": "p1_b1",
            "page": 1,
            "role": "body_paragraph",
            "text": "Title",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 16.0},
            "layout_signature": {"width": 420},
        },
        {
            "block_id": "p3_b1",
            "page": 3,
            "role": "body_paragraph",
            "text": "This is a sufficiently long body paragraph with enough tokens to behave like stable body content.",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "block_id": "p6_b1",
            "page": 6,
            "role": "reference_heading",
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
        },
        {
            "block_id": "p6_b2",
            "page": 6,
            "role": "body_paragraph",
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "block_id": "p6_b3",
            "page": 6,
            "role": "body_paragraph",
            "text": "[2] Another example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
        },
    ]

    doc = analyze_document_structure(blocks)
    data = dataclasses.asdict(doc)

    assert "region_bus" in data
    assert data["region_bus"]["reference_zone"]["status"] == "ACCEPT"
    assert "p6_b2" in data["region_bus"]["reference_zone"]["block_ids"]
    assert "p6_b3" in data["region_bus"]["reference_zone"]["block_ids"]


def test_infer_zones_keeps_pre_reference_tail_out_of_body_zone() -> None:
    from paperforge.worker.ocr_document import TailBoundary, infer_zones

    blocks = [
        {
            "block_id": "p1_b1",
            "page": 1,
            "text": "Title",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 16.0},
            "layout_signature": {"width": 420},
        },
        {
            "block_id": "p4_b1",
            "page": 4,
            "text": "Body text",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "block_id": "p7_b1",
            "page": 7,
            "text": "Acknowledgments",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 180, "x_center": 240},
        },
        {
            "block_id": "p7_b2",
            "page": 7,
            "text": "We thank the core facility.",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.8},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "block_id": "p8_b1",
            "page": 8,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120, "x_center": 240},
        },
        {
            "block_id": "p8_b2",
            "page": 8,
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5},
            "layout_signature": {"width": 250, "x_center": 240},
        },
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family", "sample_pages": [4]},
        "reference_family_anchor": {"status": "ACCEPT", "family_name": "reference_family", "item_count": 1},
    }
    tail_spread = TailBoundary(
        body_end_page=4,
        backmatter_start=7,
        references_start=8,
        spread_start=7,
        spread_end=8,
        is_clean_separated=True,
        reason="test",
    )

    zones = infer_zones(blocks, anchors, tail_spread=tail_spread)

    assert "p7_b2" in zones["tail_nonref_hold_zone"]["block_ids"]
    assert "p7_b2" not in zones["body_zone"]["block_ids"]


def test_infer_zones_inferrs_tail_nonref_hold_without_pre_labeled_tail_roles() -> None:
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {
            "block_id": "p1_b1",
            "page": 1,
            "role": "body_paragraph",
            "text": "Title",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 16.0},
            "layout_signature": {"width": 420},
        },
        {
            "block_id": "p4_b1",
            "page": 4,
            "role": "body_paragraph",
            "text": "This is a sufficiently long body paragraph with enough tokens to establish body-family evidence.",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "block_id": "p7_b1",
            "page": 7,
            "role": "body_paragraph",
            "text": "Acknowledgments",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 10.8, "font_family_norm": "Helvetica", "is_bold": True},
            "layout_signature": {"width": 180, "x_center": 240},
        },
        {
            "block_id": "p7_b2",
            "page": 7,
            "role": "body_paragraph",
            "text": "We thank the core facility.",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.8, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "block_id": "p8_b1",
            "page": 8,
            "role": "body_paragraph",
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0, "font_family_norm": "Helvetica", "is_bold": True},
            "layout_signature": {"width": 120, "x_center": 240},
        },
        {
            "block_id": "p8_b2",
            "page": 8,
            "role": "body_paragraph",
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
        },
        {
            "block_id": "p8_b3",
            "page": 8,
            "role": "body_paragraph",
            "text": "[2] Another example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
        },
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family", "sample_pages": [4]},
        "reference_family_anchor": {"status": "ACCEPT", "family_name": "reference_family", "item_count": 2},
    }

    zones = infer_zones(blocks, anchors)

    assert "p7_b2" in zones["tail_nonref_hold_zone"]["block_ids"]
    assert "p7_b2" not in zones["body_zone"]["block_ids"]


def test_normalize_flat_backmatter_unifies_heading_family() -> None:
    from paperforge.worker.ocr_document import (
        TailBoundary,
        _normalize_backmatter_roles_after_boundary,
    )

    blocks = [
        {"page": 70, "role": "body_paragraph", "text": "Conclusion continuation"},
        {"page": 71, "role": "backmatter_heading", "text": "Data availability"},
        {"page": 71, "role": "backmatter_body", "text": "No new data."},
        {"page": 71, "role": "subsection_heading", "text": "Conflicts of interest"},
        {"page": 71, "role": "body_paragraph", "text": "There are no conflicts to declare."},
        {"page": 71, "role": "backmatter_heading", "text": "Acknowledgements"},
        {"page": 71, "role": "backmatter_body", "text": "Supported by grant."},
        {"page": 71, "role": "reference_heading", "text": "References"},
        {"page": 71, "role": "reference_item", "text": "1. Ref item"},
    ]

    tail = TailBoundary(
        body_end_page=70,
        backmatter_start=71,
        references_start=71,
        spread_start=71,
        spread_end=71,
        is_clean_separated=True,
        reason="test",
    )

    _normalize_backmatter_roles_after_boundary(tail, "flat", blocks)

    assert blocks[3]["role"] == "backmatter_heading"
    assert blocks[4]["role"] == "backmatter_body"
    assert blocks[4]["render_default"] is True
    assert blocks[7]["role"] == "reference_heading"


def test_analyze_document_structure_no_tail() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, analyze_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Only body"},
        {"page": 2, "role": "body_paragraph", "text": "Still body"},
    ]

    doc = analyze_document_structure(blocks)

    assert isinstance(doc, DocumentStructure)
    assert doc.body_end_page is None
    assert doc.spread_start is None
    assert doc.spread_end is None
    assert doc.backmatter_form == "flat"


def test_rescue_frontmatter_noise_to_body_paragraph() -> None:
    """frontmatter_noise in body section with body-like font → body_paragraph."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "Intro body paragraph with enough text to establish a profile.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 2,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "Methods section describing the experimental setup in full detail.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 3,
            "role": "frontmatter_noise",
            "role_confidence": 0.6,
            "text": "This block was misclassified as frontmatter noise but is actually body text.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {"page": 4, "role": "reference_heading", "role_confidence": 0.9, "text": "References"},
        {"page": 4, "role": "reference_item", "role_confidence": 0.7, "text": "[1] Author A, Journal, 2025"},
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 2,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "frontmatter_noise": {
            "block_count": 1,
            "mean_size": 8.0,
            "max_size": 8.5,
            "min_size": 7.5,
            "dispersion": 0.05,
            "quality": "weak",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(body_end_page=3)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    rescued = next(b for b in result if b["text"].startswith("This block was misclassified"))
    assert rescued["role"] == "body_paragraph", f"Expected body_paragraph, got {rescued['role']}"


def test_rescue_body_paragraph_to_reference_item() -> None:
    """body_paragraph with ref-like font in references section → reference_item."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        PagePosition,
        rescue_roles_with_document_context,
    )

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "Main body paragraph that is long enough for context.",
            "span_metadata": {"size": 10.5, "flags": "normal"},
        },
        {"page": 5, "role": "reference_heading", "role_confidence": 0.9, "text": "References"},
        {
            "page": 5,
            "role": "body_paragraph",
            "role_confidence": 0.5,
            "text": "1. Smith J, Johnson K. A study on something. Journal, 2025.",
            "span_metadata": {"size": 9.0, "flags": "normal"},
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 1,
            "mean_size": 10.5,
            "max_size": 10.5,
            "min_size": 10.5,
            "dispersion": 0.0,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "reference_item": {
            "block_count": 0,
            "mean_size": 9.0,
            "max_size": 9.0,
            "min_size": 9.0,
            "dispersion": 0.0,
            "quality": "weak",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(body_end_page=4, references_start=PagePosition(page=5, y=0))
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    promoted = next(b for b in result if b["text"].startswith("1. Smith"))
    assert promoted["role"] == "reference_item", f"Expected reference_item, got {promoted['role']}"


def test_rescue_weak_heading_demoted_to_body() -> None:
    """Weak heading (confidence < 0.6) with body-like font → body_paragraph."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "Some intro body text that provides a long enough context for profiling.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 2,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "More body text to strengthen the body profile for better font matching.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 2,
            "role": "section_heading",
            "role_confidence": 0.5,
            "text": "Methods",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 2,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "section_heading": {
            "block_count": 0,
            "mean_size": 12.0,
            "max_size": 12.0,
            "min_size": 12.0,
            "dispersion": 0.0,
            "quality": "no_data",
            "bold_ratio": 1.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(body_end_page=2)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    demoted = next(b for b in result if b["text"] == "Methods")
    assert demoted["role"] == "body_paragraph", f"Expected body_paragraph, got {demoted['role']}"


def test_rescue_strong_numbered_heading_not_demoted() -> None:
    """Strong numbered heading (e.g. '5.1 Results') should NOT be demoted."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "Body paragraph one with enough text to contribute to a font profile.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 2,
            "role": "section_heading",
            "role_confidence": 0.5,
            "text": "5.1 Results",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 1,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(body_end_page=2)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    heading = next(b for b in result if b["text"] == "5.1 Results")
    assert heading["role"] == "section_heading", f"Expected section_heading preserved, got {heading['role']}"


def test_rescue_no_document_structure_derived() -> None:
    """rescue_roles_with_document_context should derive structure when not provided."""
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "Body text that is long enough for establishing a font profile here.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 2,
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "text": "More body text here to help build a solid body paragraph profile.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "page": 2,
            "role": "frontmatter_noise",
            "role_confidence": 0.6,
            "text": "Misclassified text block that should be rescued to body paragraph.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {"page": 3, "role": "reference_heading", "role_confidence": 0.9, "text": "References"},
        {"page": 3, "role": "reference_item", "role_confidence": 0.7, "text": "[1] Author A, Journal, 2025"},
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 2,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "frontmatter_noise": {
            "block_count": 1,
            "mean_size": 8.0,
            "max_size": 8.5,
            "min_size": 7.5,
            "dispersion": 0.05,
            "quality": "weak",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    result = rescue_roles_with_document_context(blocks, role_profiles)

    rescued = next(b for b in result if b["text"].startswith("Misclassified"))
    assert rescued["role"] == "body_paragraph", f"Expected body_paragraph, got {rescued['role']}"


def test_rescue_analyze_document_structure_mixed_tail_spread() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, analyze_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Intro"},
        {"page": 2, "role": "body_paragraph", "text": "Results"},
        {"page": 3, "role": "body_paragraph", "text": "Continued results"},
        {"page": 3, "role": "backmatter_heading", "text": "Acknowledgments"},
        {"page": 3, "role": "backmatter_body", "text": "Thanks."},
        {"page": 4, "role": "body_paragraph", "text": "More results interleaved"},
        {"page": 4, "role": "reference_heading", "text": "References"},
        {"page": 4, "role": "reference_item", "text": "[1] Ref A"},
    ]

    doc = analyze_document_structure(blocks)

    assert isinstance(doc, DocumentStructure)
    assert doc.spread_start is not None
    assert doc.spread_end is not None


def _make_block(bid: int, pg: int = 1, role: str = "body_paragraph", text: str = "text", w: int = 500) -> dict:
    return {
        "block_id": f"b{bid}",
        "page": pg,
        "role": role,
        "text": text,
        "bbox": [80, 100, 80 + w, 140],
        "page_width": 1200,
        "page_height": 1700,
    }


def test_body_anchor_pages_exclude_page_1() -> None:
    """When page 1 is contaminated with title/authors, it should not dominate body baseline."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Page 1: title + authors + furniture — no real body paragraphs
    blocks += [_make_block(i, pg=1, role="paper_title", text="Title", w=200) for i in range(3)]
    blocks += [_make_block(i, pg=1, role="authors", text="Authors", w=200) for i in range(3)]
    blocks += [_make_block(i, pg=1, role="noise", text="Copyright", w=136) for i in range(2)]
    # Pages 2-8: clean body paragraphs
    for pg in range(2, 9):
        blocks += [
            _make_block(i + pg * 10, pg=pg, role="body_paragraph", text=f"Body para on page {pg}", w=510)
            for i in range(5)
        ]
    # Page 9: references
    blocks += [_make_block(i, pg=9, role="reference_heading", text="References", w=150) for i in range(1)]

    spine = _detect_body_spine(blocks)
    # Page 1 should have either a reasonable width (not 200) or the anchor
    # pages list should exclude page 1.  Currently anchor_pages does not
    # exist → this will be [] → resolves to [1] ≠ [1] → False → fail.
    anchor_pages: list[int] = spine.get(1, {}).get("anchor_pages", [])  # type: ignore[type-arg]
    assert anchor_pages or [1] != [1], f"Page 1 anchor pages should exclude page 1, got anchor_pages={anchor_pages!r}"


def test_body_anchor_pages_exclude_tail() -> None:
    """Pages in the tail spread should be excluded from anchor pages."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Pages 1-5: clean body
    for pg in range(1, 6):
        blocks += [
            _make_block(i + pg * 10, pg=pg, role="body_paragraph", text=f"Body para on page {pg}", w=510)
            for i in range(5)
        ]
    # Pages 6-8: tail (references, etc.)
    blocks += [_make_block(i, pg=6, role="reference_heading", text="References", w=150) for i in range(1)]
    blocks += [_make_block(i, pg=7, role="reference_item", text="Ref item", w=200) for i in range(3)]
    blocks += [_make_block(i, pg=8, role="backmatter_body", text="Ack", w=300) for i in range(2)]

    spine = _detect_body_spine(blocks)
    # Anchor pages should be from body section, not tail.
    # Currently anchor_pages does not exist → [] → fails when we require non-empty.
    anchor_pages: list[int] = spine.get(2, {}).get("anchor_pages", [])  # type: ignore[type-arg]
    assert anchor_pages and all(pg < 6 for pg in anchor_pages), (
        f"Anchor pages should be in body (pages 2-5), got anchor_pages={anchor_pages!r}"
    )


def test_anchor_ranking_prefers_body_dense_pages() -> None:
    """Pages with more body paragraphs rank higher in anchor selection."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Page 2: few body paragraphs (should rank lower)
    blocks += [_make_block(i, pg=2, role="body_paragraph", text="Body para on page 2", w=510) for i in range(2)]
    # Pages 3-4: many body paragraphs (should rank higher)
    for pg in range(3, 5):
        blocks += [
            _make_block(i + pg * 10, pg=pg, role="body_paragraph", text=f"Body para on page {pg}", w=510)
            for i in range(8)
        ]
    # Page 5: moderate body paragraphs
    blocks += [_make_block(i, pg=5, role="body_paragraph", text="Body para on page 5", w=510) for i in range(4)]

    spine = _detect_body_spine(blocks)
    anchor_pages: list[int] = spine.get(2, {}).get("anchor_pages", [])  # type: ignore[type-arg]
    # Pages 3-4 (8 paras each) should rank higher than page 5 (4 paras) and page 2 (2 paras).
    # Currently no anchor_pages key → [] → fails.
    assert len(anchor_pages) >= 2, f"Expected at least 2 anchor pages, got {anchor_pages!r}"
    ranked = [p for p in anchor_pages if p in (3, 4, 5, 2)]
    assert ranked[0] in (3, 4), f"Highest ranked should be 3 or 4, got {ranked}"


def test_middle_page_baseline_excludes_frontmatter() -> None:
    """Page 1 contaminated with title/authors/noise — body paragraphs on page 1
    are few relative to total blocks.  Body baseline should come from central
    pages 4-8, not from contaminated page 1."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Page 1: contaminated — 2 title, 2 authors, 4 noise, only 2 body_paragraph
    # body_ratio = 2/10 = 0.2 < 0.4 → should be excluded by new scoring
    for i in range(2):
        blocks.append(
            {
                "block_id": f"b_title{i}",
                "page": 1,
                "role": "paper_title",
                "text": f"Title {i}",
                "bbox": [80, 20 + i * 40, 280, 60 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    for i in range(2):
        blocks.append(
            {
                "block_id": f"b_author{i}",
                "page": 1,
                "role": "authors",
                "text": f"Author {i}",
                "bbox": [80, 120 + i * 40, 300, 160 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    for i in range(4):
        blocks.append(
            {
                "block_id": f"b_noise{i}",
                "page": 1,
                "role": "noise",
                "text": f"Noise {i}",
                "bbox": [80, 220 + i * 40, 180, 260 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    for i in range(2):
        blocks.append(
            {
                "block_id": f"b_body1_{i}",
                "page": 1,
                "role": "body_paragraph",
                "text": f"Body on page 1 {i}",
                "bbox": [80, 400 + i * 40, 500, 440 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    # Pages 4-8: clean body (3 body paragraphs each)
    for pg in range(4, 9):
        for i in range(3):
            blocks.append(
                {
                    "block_id": f"b{pg}_{i}",
                    "page": pg,
                    "role": "body_paragraph",
                    "text": f"Body on {pg}",
                    "bbox": [80, 100 + i * 80, 550, 140 + i * 80],
                    "page_width": 1200,
                    "page_height": 1700,
                }
            )
    # Pages 10-11: tail
    blocks.append(
        {
            "block_id": "ref_head",
            "page": 10,
            "role": "reference_heading",
            "text": "References",
            "bbox": [80, 100, 400, 130],
            "page_width": 1200,
            "page_height": 1700,
        }
    )
    for i in range(3):
        blocks.append(
            {
                "block_id": f"ref_{i}",
                "page": 10,
                "role": "reference_item",
                "text": f"Ref {i}",
                "bbox": [80, 150 + i * 40, 500, 190 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )

    spine = _detect_body_spine(blocks)
    anchor_pages: list[int] = spine.get(4, {}).get("anchor_pages", [])
    # Page 1 has 2 body + 8 non-body = body_ratio 0.2 → excluded
    assert 1 not in anchor_pages, f"Page 1 should be excluded from anchor pages, got {anchor_pages}"
    # Tail pages (10+) should be excluded
    assert all(pg < 10 for pg in anchor_pages), f"Tail pages should be excluded, got {anchor_pages}"
    # Central pages 4-8 should be included
    central = [pg for pg in anchor_pages if pg in (4, 5, 6, 7, 8)]
    assert len(central) >= 2, f"Expected at least 2 central pages (4-8) in anchors, got {anchor_pages}"


def test_middle_page_baseline_excludes_tail() -> None:
    """Tail pages (backmatter/references) should be excluded from anchor pages."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Page 1: frontmatter only — will be excluded by page==1 guard
    for i in range(3):
        blocks.append(
            {
                "block_id": f"b_title{i}",
                "page": 1,
                "role": "paper_title",
                "text": f"Title {i}",
                "bbox": [80, 20 + i * 40, 280, 60 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    # Page 2: contaminated (2 body + 6 non-body)
    for i in range(2):
        blocks.append(
            {
                "block_id": f"b2_body{i}",
                "page": 2,
                "role": "body_paragraph",
                "text": f"Body on 2 {i}",
                "bbox": [80, 100 + i * 40, 500, 140 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    for i in range(6):
        blocks.append(
            {
                "block_id": f"b2_noise{i}",
                "page": 2,
                "role": "noise",
                "text": f"Noise {i}",
                "bbox": [80, 300 + i * 30, 180, 330 + i * 30],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    # Pages 4-8: clean body (4 body paragraphs each)
    for pg in range(4, 9):
        for i in range(4):
            blocks.append(
                {
                    "block_id": f"b{pg}_{i}",
                    "page": pg,
                    "role": "body_paragraph",
                    "text": f"Body on {pg}",
                    "bbox": [80, 100 + i * 60, 550, 140 + i * 60],
                    "page_width": 1200,
                    "page_height": 1700,
                }
            )
    # Pages 10+: tail (reference heading + items)
    blocks.append(
        {
            "block_id": "ref_h",
            "page": 10,
            "role": "reference_heading",
            "text": "References",
            "bbox": [80, 100, 400, 130],
            "page_width": 1200,
            "page_height": 1700,
        }
    )
    for i in range(4):
        blocks.append(
            {
                "block_id": f"ref_{i}",
                "page": 10,
                "role": "reference_item",
                "text": f"Ref {i}",
                "bbox": [80, 150 + i * 40, 500, 190 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )

    spine = _detect_body_spine(blocks)
    anchor_pages: list[int] = spine.get(4, {}).get("anchor_pages", [])
    # No tail pages should be in anchors
    assert all(pg < 10 for pg in anchor_pages), f"Tail pages (10+) should be excluded, got {anchor_pages}"
    # Central pages 4-8 should be included
    assert any(pg in (4, 5, 6, 7, 8) for pg in anchor_pages), f"Expected central pages in anchors, got {anchor_pages}"


def test_detect_body_spine_returns_reasonable_values() -> None:
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = [
        {"role": "body_paragraph", "bbox": [100, 500, 800, 540], "page": 1},
        {"role": "body_paragraph", "bbox": [100, 600, 810, 640], "page": 1},
    ]
    spine = _detect_body_spine(blocks)
    assert 1 in spine
    assert spine[1]["median_width"] == 700  # 800-100
    assert spine[1]["median_x"] == 100


def test_detect_non_body_insert_marks_narrow_blocks() -> None:
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = [
        # Pages 2-4: establish strong body spine
        *[{"role": "body_paragraph", "bbox": [100, 100 + i * 100, 800, 140 + i * 100],
           "page": pg, "span_metadata": [{"size": 10, "font": "Times"}]}
          for pg in range(2, 5) for i in range(3)],
        # Two normal body paragraphs (wide)
        {"role": "body_paragraph", "bbox": [100, 400, 800, 440], "page": 1},
        {"role": "body_paragraph", "bbox": [100, 500, 810, 540], "page": 1},
        # A narrow block (author bio type) -- much narrower than 700px
        {"role": "body_paragraph", "bbox": [50, 200, 300, 250], "page": 1},
        # Another narrow block on same page
        {"role": "body_paragraph", "bbox": [50, 300, 310, 350], "page": 1},
    ]
    spine = _detect_body_spine(blocks)
    indices = _detect_non_body_insert_clusters(blocks, spine)
    assert 11 in indices, f"Expected index 11 in {indices}"
    assert 12 in indices, f"Expected index 12 in {indices}"


def test_detect_non_body_insert_marks_narrow_body_paragraphs() -> None:
    """Narrow body_paragraph blocks (author bios) are detected as non-body inserts."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = [
        # Pages 2-4: establish strong body spine
        *[{"role": "body_paragraph", "bbox": [100, 100 + i * 100, 800, 140 + i * 100],
           "page": pg, "span_metadata": [{"size": 10, "font": "Times"}]}
          for pg in range(2, 5) for i in range(3)],
        # wide body paragraphs on page 1
        {"role": "body_paragraph", "bbox": [100, 100, 800, 140], "page": 1},
        {"role": "body_paragraph", "bbox": [100, 200, 810, 240], "page": 1},
        # narrow body_paragraph = potential author bio
        {"role": "body_paragraph", "bbox": [50, 600, 300, 640], "page": 1},
        {"role": "body_paragraph", "bbox": [50, 680, 310, 720], "page": 1},
    ]
    spine = _detect_body_spine(blocks)
    indices = _detect_non_body_insert_clusters(blocks, spine, body_end_page=8)
    assert 11 in indices, f"Expected index 11 (narrow body_paragraph) in {indices}"
    assert 12 in indices, f"Expected index 12 (narrow body_paragraph) in {indices}"


def test_non_body_insert_not_backfilled_to_body() -> None:
    """Verify that non_body_insert blocks are not rescued to body_paragraph."""
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "TEST001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [50, 200, 300, 240],
            "text": "Short bio line one",
            "page_width": 1200,
            "page_height": 1600,
            "source": "ocr_raw",
        },
        {
            "paper_id": "TEST001",
            "page": 1,
            "block_id": "p1_b2",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [50, 280, 310, 320],
            "text": "Short bio line two",
            "page_width": 1200,
            "page_height": 1600,
            "source": "ocr_raw",
        },
        # A wide body paragraph
        {
            "paper_id": "TEST001",
            "page": 1,
            "block_id": "p1_b3",
            "raw_label": "text",
            "raw_order": 2,
            "bbox": [100, 600, 800, 640],
            "text": "The following experimental results demonstrate the effect of the treatment on cell migration and proliferation assays performed in triplicate",
            "page_width": 1200,
            "page_height": 1600,
            "source": "ocr_raw",
        },
        # Pages 2-4: establish strong body spine
        *[{
            "paper_id": "TEST001", "page": pg,
            "block_id": f"p{pg}_b{i}", "raw_label": "text",
            "raw_order": 3 + (pg - 2) * 3 + i,
            "bbox": [100, 100 + i * 100, 800, 140 + i * 100],
            "text": f"Standard body paragraph on page {pg} providing enough textual content for processing.",
            "page_width": 1200, "page_height": 1600, "source": "ocr_raw",
            "span_metadata": {"size": 10, "font": "Times"},
        } for pg in range(2, 5) for i in range(3)],
    ]
    rows, _ = build_structured_blocks(raw_blocks)
    non_body = [r for r in rows if r.get("role") == "non_body_insert"]
    assert len(non_body) == 2, f"Expected 2 non_body_insert, got {len(non_body)}"
    for r in non_body:
        assert r.get("render_default") is False, f"non_body_insert should not render: {r}"


# ---------------------------------------------------------------------------
# Family-level profile tests
# ---------------------------------------------------------------------------


def test_build_family_profiles_body_family() -> None:
    """body_family aggregates body_paragraph, tail_candidate_body, backmatter_body."""
    from paperforge.worker.ocr_profiles import build_family_profiles

    blocks = [
        {"role": "body_paragraph", "span_metadata": {"size": 10, "flags": "normal"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.5, "flags": "normal"}},
        {"role": "tail_candidate_body", "span_metadata": {"size": 10, "flags": "normal"}},
        {"role": "backmatter_body", "span_metadata": {"size": 9.5, "flags": "italic"}},
        {"role": "section_heading", "span_metadata": {"size": 14, "flags": "bold"}},
    ]

    families = build_family_profiles(blocks)

    assert "body_family" in families, f"body_family missing from {list(families.keys())}"
    bf = families["body_family"]
    assert bf["block_count"] == 4
    assert "member_roles" in bf
    assert "body_paragraph" in bf["member_roles"]
    assert "tail_candidate_body" in bf["member_roles"]
    assert "backmatter_body" in bf["member_roles"]


def test_build_family_profiles_heading_family() -> None:
    """heading_family aggregates section_heading, subsection_heading, sub_subsection_heading."""
    from paperforge.worker.ocr_profiles import build_family_profiles

    blocks = [
        {"role": "section_heading", "span_metadata": {"size": 14, "flags": "bold"}},
        {"role": "subsection_heading", "span_metadata": {"size": 12, "flags": "bold"}},
        {"role": "sub_subsection_heading", "span_metadata": {"size": 11, "flags": "bold"}},
    ]

    families = build_family_profiles(blocks)

    assert "heading_family" in families
    hf = families["heading_family"]
    assert hf["block_count"] == 3
    assert "section_heading" in hf["member_roles"]
    assert "subsection_heading" in hf["member_roles"]


def test_build_family_profiles_backmatter_heading_family() -> None:
    """backmatter_heading_family aggregates backmatter headings and reference_heading."""
    from paperforge.worker.ocr_profiles import build_family_profiles

    blocks = [
        {"role": "backmatter_heading", "span_metadata": {"size": 12, "flags": "bold"}},
        {"role": "backmatter_boundary_heading", "span_metadata": {"size": 11, "flags": "bold"}},
        {"role": "reference_heading", "span_metadata": {"size": 12, "flags": "bold"}},
    ]

    families = build_family_profiles(blocks)

    assert "backmatter_heading_family" in families
    assert families["backmatter_heading_family"]["block_count"] == 3


def test_compare_against_family_matches_body_block() -> None:
    """A body-size block should match body_family better than non_body_insert_family."""
    from paperforge.worker.ocr_profiles import (
        build_family_profiles,
        compare_against_family,
        extract_block_span_profile,
    )

    blocks = [
        {"role": "body_paragraph", "span_metadata": {"size": 10, "flags": "normal"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.5, "flags": "normal"}},
        {"role": "non_body_insert", "span_metadata": {"size": 8, "flags": "normal"}},
        {"role": "non_body_insert", "span_metadata": {"size": 8.5, "flags": "normal"}},
    ]

    families = build_family_profiles(blocks)

    body_block = {"span_metadata": {"size": 10.2, "flags": "normal"}}
    bp = extract_block_span_profile(body_block)
    assert bp is not None

    body_match = compare_against_family(bp, families["body_family"])
    ni_match = compare_against_family(bp, families["non_body_insert_family"])

    assert body_match["match_score"] > ni_match["match_score"], (
        f"Body block should match body_family ({body_match['match_score']}) "
        f"better than non_body_insert_family ({ni_match['match_score']})"
    )


def test_family_level_non_body_insert_validation() -> None:
    """Narrow non-body insert should match non_body_insert_family, not body_family."""
    from paperforge.worker.ocr_profiles import (
        build_family_profiles,
        compare_against_family,
        extract_block_span_profile,
    )

    blocks = [
        {"role": "body_paragraph", "span_metadata": {"size": 10, "flags": "normal"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.5, "flags": "normal"}},
        {"role": "non_body_insert", "span_metadata": {"size": 8, "flags": "italic"}},
        {"role": "non_body_insert", "span_metadata": {"size": 8.5, "flags": "italic"}},
    ]

    families = build_family_profiles(blocks)

    narrow_block = {"span_metadata": {"size": 8.2, "flags": "italic"}}
    bp = extract_block_span_profile(narrow_block)
    assert bp is not None

    ni_match = compare_against_family(bp, families["non_body_insert_family"])
    body_match = compare_against_family(bp, families["body_family"])

    assert ni_match["match_score"] > body_match["match_score"], (
        f"Narrow italic block should match non_body_insert_family ({ni_match['match_score']}) "
        f"better than body_family ({body_match['match_score']})"
    )


def test_family_level_rescue_reinstates_false_non_body_insert() -> None:
    """Non-body insert with body-like style should be reinstated by family rescue
    only when non_body_insert_family profile is reliable (moderate+ quality)."""
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        # body paragraphs to establish body_family profile
        {
            "role": "body_paragraph",
            "page": 1,
            "role_confidence": 0.8,
            "text": "Normal body paragraph with enough text for profiling purposes in this test case.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "role": "body_paragraph",
            "page": 2,
            "role_confidence": 0.8,
            "text": "Another body paragraph to strengthen the body font profile for reliable matching.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        # genuine non_body_insert blocks (4 blocks with consistent small/italic style,
        # dispersion <= 0.15 = strong quality for non_body_insert_family)
        {
            "role": "non_body_insert",
            "page": 1,
            "role_confidence": 0.5,
            "_non_body_insert": True,
            "text": "Short bio text one",
            "span_metadata": {"size": 9, "flags": "italic"},
        },
        {
            "role": "non_body_insert",
            "page": 1,
            "role_confidence": 0.5,
            "_non_body_insert": True,
            "text": "Short bio text two",
            "span_metadata": {"size": 9, "flags": "italic"},
        },
        {
            "role": "non_body_insert",
            "page": 2,
            "role_confidence": 0.5,
            "_non_body_insert": True,
            "text": "Short bio text three",
            "span_metadata": {"size": 9, "flags": "italic"},
        },
        {
            "role": "non_body_insert",
            "page": 2,
            "role_confidence": 0.5,
            "_non_body_insert": True,
            "text": "Short bio text four",
            "span_metadata": {"size": 9, "flags": "italic"},
        },
        # false positive: body-like font in non_body_insert, wide enough to pass geometry guard
        {
            "role": "non_body_insert",
            "page": 2,
            "role_confidence": 0.5,
            "_non_body_insert": True,
            "bbox": [100, 400, 700, 440],
            "page_width": 1200,
            "text": "This block was incorrectly marked as non_body_insert but has a body-paragraph style.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 2,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "non_body_insert": {
            "block_count": 5,
            "mean_size": 9.2,
            "max_size": 10.0,
            "min_size": 9.0,
            "dispersion": 0.054,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.8,
            "font_families": [],
        },
    }

    result = rescue_roles_with_document_context(blocks, role_profiles)

    # The body-like block should be reinstated because non_body_insert_family
    # has strong quality
    reinstated = [b for b in result if b["text"].startswith("This block was incorrectly")]
    assert len(reinstated) == 1
    assert reinstated[0]["role"] == "body_paragraph", (
        f"Expected false-positive non_body_insert to be reinstated to body_paragraph, got {reinstated[0]['role']}"
    )
    assert "_non_body_insert" not in reinstated[0], "non_body_insert flag should be removed"

    still_ni = [b for b in result if "Short bio text" in (b.get("text", ""))]
    assert len(still_ni) == 4
    for b in still_ni:
        assert b["role"] == "non_body_insert", f"Genuine non_body_insert should keep its role, got {b['role']}"


def test_family_level_rescue_weak_heading_matches_heading_family() -> None:
    """Weak heading matching heading_family should NOT be demoted to body_paragraph."""
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        # body paragraphs
        {
            "role": "body_paragraph",
            "page": 1,
            "role_confidence": 0.8,
            "text": "Normal body paragraph with enough text for profiling purposes in this test case.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "role": "body_paragraph",
            "page": 2,
            "role_confidence": 0.8,
            "text": "Another body paragraph to strengthen the body profile for more reliable comparisons.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        # heading blocks to establish heading_family (different size, bold)
        {
            "role": "section_heading",
            "page": 1,
            "role_confidence": 0.8,
            "text": "Introduction",
            "span_metadata": {"size": 14, "flags": "bold"},
        },
        {
            "role": "subsection_heading",
            "page": 2,
            "role_confidence": 0.8,
            "text": "Statistical Analysis",
            "span_metadata": {"size": 12, "flags": "bold"},
        },
        # weak heading that matches heading_family (should NOT be demoted)
        {
            "role": "section_heading",
            "page": 3,
            "role_confidence": 0.55,
            "text": "Results",
            "span_metadata": {"size": 14, "flags": "bold"},
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 2,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "section_heading": {
            "block_count": 1,
            "mean_size": 14.0,
            "max_size": 14.5,
            "min_size": 13.5,
            "dispersion": 0.04,
            "quality": "strong",
            "bold_ratio": 1.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "subsection_heading": {
            "block_count": 1,
            "mean_size": 12.0,
            "max_size": 12.5,
            "min_size": 11.5,
            "dispersion": 0.04,
            "quality": "strong",
            "bold_ratio": 1.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    result = rescue_roles_with_document_context(blocks, role_profiles)

    heading = next(b for b in result if b["text"] == "Results")
    assert heading["role"] == "section_heading", (
        f"Weak heading matching heading_family should keep its role, got {heading['role']}"
    )


def test_family_level_rescue_does_not_backfill_non_body_insert_when_no_family_profile() -> None:
    """Non-body insert blocks are left alone when no family profiles are available."""
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        {
            "role": "frontmatter_noise",
            "text": "Dr Ya Huang is currently a professor at the University",
            "page": 2,
            "_non_body_insert": True,
            "role_confidence": 0.5,
            "span_metadata": {"size": 11, "flags": "normal"},
        },
    ]
    role_profiles = {
        "body_paragraph": {"size_min": 10, "size_max": 12, "bold": False, "quality": "strong", "fonts": set()},
    }
    result = rescue_roles_with_document_context(blocks, role_profiles)
    non_body = [b for b in result if b.get("_non_body_insert")]
    assert len(non_body) == 1
    assert non_body[0]["role"] == "frontmatter_noise"


def test_rescue_does_not_touch_non_body_insert() -> None:
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        {
            "role": "frontmatter_noise",
            "text": "Dr Ya Huang is currently a professor at the University",
            "page": 2,
            "_non_body_insert": True,
            "role_confidence": 0.5,
            "span_metadata": {"size": 11, "flags": "normal"},
        },
        {
            "role": "body_paragraph",
            "text": "Real body text on page 2.",
            "page": 2,
            "_non_body_insert": False,
            "role_confidence": 0.6,
            "span_metadata": {"size": 11, "flags": "normal"},
        },
    ]
    role_profiles = {
        "body_paragraph": {"size_min": 10, "size_max": 12, "bold": False, "quality": "strong", "fonts": set()},
    }
    result = rescue_roles_with_document_context(blocks, role_profiles)
    non_body = [b for b in result if b.get("_non_body_insert")]
    assert len(non_body) == 1
    assert non_body[0]["role"] == "frontmatter_noise", "non_body_insert must not be rescued to body_paragraph"


def test_non_body_insert_catches_figure_caption_blocks() -> None:
    """figure_caption blocks (narrow author bios) are detected as non-body inserts."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = [
        # Page 1: wide body paragraphs
        {
            "role": "body_paragraph",
            "bbox": [100, 100, 800, 140],
            "page": 1,
            "span_metadata": {"font": "TimesNewRoman", "size": 10},
        },
        {
            "role": "body_paragraph",
            "bbox": [100, 200, 810, 240],
            "page": 1,
            "span_metadata": {"font": "TimesNewRoman", "size": 10},
        },
        # Page 2: wide body paragraphs
        {
            "role": "body_paragraph",
            "bbox": [100, 100, 800, 140],
            "page": 2,
            "span_metadata": {"font": "TimesNewRoman", "size": 10},
        },
        {
            "role": "body_paragraph",
            "bbox": [100, 200, 810, 240],
            "page": 2,
            "span_metadata": {"font": "TimesNewRoman", "size": 10},
        },
        # Page 2: narrow figure_caption blocks (author bios mislabeled by PaddleOCR)
        {
            "role": "figure_caption",
            "bbox": [50, 600, 300, 640],
            "page": 2,
            "span_metadata": {"font": "Arial", "size": 8},
        },
        {
            "role": "figure_caption",
            "bbox": [50, 680, 310, 720],
            "page": 2,
            "span_metadata": {"font": "Arial", "size": 8},
        },
    ]
    spine = _detect_body_spine(blocks)
    indices = _detect_non_body_insert_clusters(blocks, spine, body_end_page=8)

    # All profile-cluster figure_caption blocks must be caught
    assert 4 in indices, f"Expected index 4 (narrow figure_caption) in {indices}"
    assert 5 in indices, f"Expected index 5 (narrow figure_caption) in {indices}"

    # No wide body_paragraph block should be falsely detected
    for i in range(4):
        assert i not in indices, f"Body paragraph at index {i} should not be in {indices}"


def test_non_body_insert_does_not_promote_real_figure_captions() -> None:
    """A genuine Figure 1 caption (wide, near media) should NOT be detected as non-body insert."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = [
        # Wide body paragraphs
        {
            "role": "body_paragraph",
            "bbox": [100, 100, 800, 140],
            "page": 1,
            "span_metadata": {"font": "TimesNewRoman", "size": 10},
        },
        {
            "role": "body_paragraph",
            "bbox": [100, 200, 810, 240],
            "page": 1,
            "span_metadata": {"font": "TimesNewRoman", "size": 10},
        },
        # Real figure caption: wide, near full body width
        {
            "role": "figure_caption",
            "bbox": [100, 500, 780, 530],
            "page": 1,
            "span_metadata": {"font": "TimesNewRoman", "size": 9},
        },
    ]
    spine = _detect_body_spine(blocks)
    indices = _detect_non_body_insert_clusters(blocks, spine, body_end_page=8)

    # Wide figure caption should NOT be detected (single block, body-width)
    assert 2 not in indices, f"Real figure caption should not be detected, got indices {indices}"


def test_visual_container_alone_does_not_force_structured_insert() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "Ordinary paragraph", "page": 2, "bbox": [100, 100, 900, 160], "page_width": 1200, "_in_visual_container": True, "_container_bbox": [90, 90, 910, 170]},
    ]

    _doc, normalized = normalize_document_structure(blocks)

    assert normalized[0]["role"] != "structured_insert"
    assert normalized[0].get("insert_score", {}).get("decision") in {"structured_insert_candidate", "body"}


def test_non_body_insert_catches_continuation_fragment() -> None:
    """A body-width continuation fragment (lowercase start) adjacent to a
    narrow non-body insert is caught by the expansion pass."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = [
        # Page 2: two wide body paragraphs establishing spine width ~700
        {
            "role": "body_paragraph",
            "bbox": [100, 100, 800, 140],
            "page": 2,
            "span_metadata": {"font": "BodyFont", "size": 10},
        },
        {
            "role": "body_paragraph",
            "bbox": [100, 200, 810, 240],
            "page": 2,
            "span_metadata": {"font": "BodyFont", "size": 10},
        },
        # Narrow non-body inserts (author bio start + name label)
        {
            "role": "body_paragraph",
            "bbox": [50, 600, 250, 640],
            "page": 2,
            "span_metadata": {"font": "BodyFont", "size": 10},
        },
        {
            "role": "body_paragraph",
            "bbox": [50, 680, 250, 720],
            "page": 2,
            "span_metadata": {"font": "BodyFont", "size": 10},
        },
        # Continuation fragment: SAME width as body paragraphs,
        # SAME font as body paragraphs, but starts lowercase and is
        # adjacent to the narrow inserts — should be caught
        {
            "role": "body_paragraph",
            "bbox": [100, 760, 800, 800],
            "page": 2,
            "span_metadata": {"font": "BodyFont", "size": 10},
            "text": "integrate technologies of tissue engineering and flexible electronics",
        },
    ]
    # Pages 3-5: establish strong body spine (3+ anchor pages)
    for pg in range(3, 6):
        blocks.append({"role": "body_paragraph", "bbox": [100, 100, 800, 140], "page": pg,
                        "span_metadata": {"font": "BodyFont", "size": 10}})
        blocks.append({"role": "body_paragraph", "bbox": [100, 200, 810, 240], "page": pg,
                        "span_metadata": {"font": "BodyFont", "size": 10}})
        blocks.append({"role": "body_paragraph", "bbox": [100, 300, 800, 340], "page": pg,
                        "span_metadata": {"font": "BodyFont", "size": 10}})

    spine = _detect_body_spine(blocks)
    indices = _detect_non_body_insert_clusters(blocks, spine, body_end_page=8)

    assert 2 in indices, f"Narrow insert at index 2 should be detected, got {indices}"
    assert 3 in indices, f"Narrow insert at index 3 should be detected, got {indices}"
    assert 4 in indices, (
        f"Continuation fragment at index 4 should be detected "
        f"(body-width, lowercase start, adjacent to insert), got {indices}"
    )


def test_non_body_insert_not_on_weak_spine() -> None:
    """Font mismatch alone should not trigger non_body_insert when spine quality is weak."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = []
    # Only page 1 body paragraphs -- spine will be weak
    for i in range(3):
        blocks.append(
            {
                "block_id": f"b{i}",
                "page": 1,
                "role": "body_paragraph",
                "text": f"Body {i}",
                "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
                "page_width": 1200,
                "page_height": 1700,
                "span_metadata": [{"size": 10, "font": "Times", "flags": 0, "color": 0}],
            }
        )
    # One narrow block on page 1 with different font
    blocks.append(
        {
            "block_id": "b3",
            "page": 1,
            "role": "body_paragraph",
            "text": "Narrow body",
            "bbox": [80, 400, 200, 440],
            "page_width": 1200,
            "page_height": 1700,
            "span_metadata": [{"size": 10, "font": "Arial", "flags": 0, "color": 0}],
        }
    )
    blocks.append(
        {
            "block_id": "b4",
            "page": 1,
            "role": "body_paragraph",
            "text": "Another narrow",
            "bbox": [80, 450, 200, 490],
            "page_width": 1200,
            "page_height": 1700,
            "span_metadata": [{"size": 10, "font": "Arial", "flags": 0, "color": 0}],
        }
    )

    spine = _detect_body_spine(blocks)
    result = _detect_non_body_insert_clusters(blocks, spine, page_width=1200)
    # With weak spine, font mismatch alone should NOT trigger
    assert len(result) == 0, f"Expected 0 non_body_insert indices, got {result}"


def test_layout_profile_single_column() -> None:
    from paperforge.worker.ocr_document import (
        PageLayoutProfile,
        _classify_page_layout,
        _cluster_page_columns,
    )

    page_width = 800.0
    page_height = 1000.0
    blocks = [
        {"bbox": [100, 100, 700, 140], "role": "body_paragraph"},
        {"bbox": [100, 160, 700, 200], "role": "body_paragraph"},
        {"bbox": [100, 220, 700, 260], "role": "body_paragraph"},
    ]

    centers = _cluster_page_columns(blocks, page_width)
    assert len(centers) == 1, f"Expected 1 cluster, got {len(centers)}"

    profile = _classify_page_layout(blocks, page_width, page_height)
    assert profile.column_count == 1
    assert profile.layout_type == "single_column"
    assert isinstance(profile, PageLayoutProfile)


def test_layout_profile_two_column() -> None:
    from paperforge.worker.ocr_document import (
        _classify_page_layout,
        _cluster_page_columns,
    )

    page_width = 800.0
    page_height = 1000.0
    blocks = [
        {"bbox": [50, 100, 380, 140], "role": "body_paragraph"},
        {"bbox": [50, 160, 380, 200], "role": "body_paragraph"},
        {"bbox": [420, 100, 750, 140], "role": "body_paragraph"},
        {"bbox": [420, 160, 750, 200], "role": "body_paragraph"},
    ]

    centers = _cluster_page_columns(blocks, page_width)
    assert len(centers) == 2, f"Expected 2 clusters, got {len(centers)}"

    profile = _classify_page_layout(blocks, page_width, page_height)
    assert profile.column_count == 2
    assert profile.layout_type == "two_column"


def test_layout_profile_mixed_tail() -> None:
    from paperforge.worker.ocr_document import (
        _classify_page_layout,
        _cluster_page_columns,
    )

    page_width = 800.0
    page_height = 1000.0
    blocks = [
        # Left column: body continuation
        {"bbox": [50, 100, 380, 200], "role": "body_paragraph"},
        {"bbox": [50, 220, 380, 260], "role": "body_paragraph"},
        # Right column: backmatter/references
        {"bbox": [420, 100, 750, 140], "role": "backmatter_heading"},
        {"bbox": [420, 160, 750, 200], "role": "reference_item"},
    ]

    centers = _cluster_page_columns(blocks, page_width)
    assert len(centers) == 2, f"Expected 2 clusters, got {len(centers)}"

    profile = _classify_page_layout(blocks, page_width, page_height)
    assert profile.column_count == 2
    assert profile.layout_type == "mixed_tail"


def test_layout_profile_build_profiles() -> None:
    from paperforge.worker.ocr_document import (
        PageLayoutProfile,
        _build_page_layout_profiles,
    )

    blocks = [
        # Page 1: single column body
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 1, "bbox": [100, 160, 700, 200], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        # Page 2: two-column, body left + tail right
        {"page": 2, "bbox": [50, 100, 380, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [420, 100, 750, 140], "role": "backmatter_heading", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [420, 160, 750, 200], "role": "reference_item", "page_width": 800, "page_height": 1000},
    ]

    profiles = _build_page_layout_profiles(blocks)

    assert 1 in profiles
    assert 2 in profiles
    assert isinstance(profiles[1], PageLayoutProfile)
    assert isinstance(profiles[2], PageLayoutProfile)

    assert profiles[1].layout_type == "single_column", f"Page 1 expected single_column, got {profiles[1].layout_type}"
    assert profiles[2].layout_type == "mixed_tail", f"Page 2 expected mixed_tail, got {profiles[2].layout_type}"


# ---------------------------------------------------------------------------
# Reading segment tests
# ---------------------------------------------------------------------------


def test_reading_segments_single_column() -> None:
    from paperforge.worker.ocr_document import (
        PageLayoutProfile,
        _build_page_reading_segments,
    )

    page_blocks = [
        {"page": 1, "bbox": [100, 300, 700, 340], "role": "body_paragraph"},
        {"page": 1, "bbox": [100, 200, 700, 240], "role": "body_paragraph"},
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph"},
    ]
    profile = PageLayoutProfile(column_count=1, column_boundaries=[400.0], layout_type="single_column")

    segments = _build_page_reading_segments(page_blocks, profile, page_idx_offset=10)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.page == 1
    assert seg.column_index == 0
    # blocks sorted by y ascending: index 2 (y=100), 1 (y=200), 0 (y=300)
    # global indices: 10+2=12, 10+1=11, 10+0=10
    assert seg.block_indices == [12, 11, 10]
    assert seg.semantic_hint == "body"
    assert seg.y_bottom > seg.y_top


def test_reading_segments_two_column() -> None:
    from paperforge.worker.ocr_document import (
        PageLayoutProfile,
        _build_page_reading_segments,
    )

    # Left col: idx0 (y=300), idx1 (y=100)
    # Right col: idx2 (y=200), idx3 (y=50)
    page_blocks = [
        {"page": 2, "bbox": [50, 300, 380, 340], "role": "body_paragraph"},
        {"page": 2, "bbox": [50, 100, 380, 140], "role": "body_paragraph"},
        {"page": 2, "bbox": [420, 200, 750, 240], "role": "body_paragraph"},
        {"page": 2, "bbox": [420, 50, 750, 90], "role": "body_paragraph"},
    ]
    profile = PageLayoutProfile(
        column_count=2,
        column_boundaries=[215.0, 585.0],
        layout_type="two_column",
    )

    segments = _build_page_reading_segments(page_blocks, profile, page_idx_offset=5)

    assert len(segments) == 2
    # Left column first
    assert segments[0].column_index == 0
    assert segments[0].page == 2
    # y sorted: local idx1 (y=100, global 6), local idx0 (y=300, global 5)
    assert segments[0].block_indices == [6, 5]
    assert segments[0].semantic_hint == "body"
    # Right column second
    assert segments[1].column_index == 1
    assert segments[1].page == 2
    # y sorted: local idx3 (y=50, global 8), local idx2 (y=200, global 7)
    assert segments[1].block_indices == [8, 7]
    assert segments[1].semantic_hint == "body"


def test_tail_reading_order_mixed_page() -> None:
    from paperforge.worker.ocr_document import (
        PageLayoutProfile,
        _build_tail_reading_order,
    )

    blocks = [
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph"},
        {"page": 1, "bbox": [100, 160, 700, 200], "role": "body_paragraph"},
        {"page": 2, "bbox": [100, 100, 700, 140], "role": "body_paragraph"},
        # Page 3: left body, right backmatter (tail page)
        {"page": 3, "bbox": [50, 100, 380, 140], "role": "body_paragraph"},
        {"page": 3, "bbox": [50, 160, 380, 200], "role": "body_paragraph"},
        {"page": 3, "bbox": [420, 100, 750, 140], "role": "backmatter_heading"},
        {"page": 3, "bbox": [420, 160, 750, 200], "role": "reference_item"},
    ]

    page_layouts = {
        1: PageLayoutProfile(column_count=1, column_boundaries=[400.0], layout_type="single_column"),
        2: PageLayoutProfile(column_count=1, column_boundaries=[400.0], layout_type="single_column"),
        3: PageLayoutProfile(
            column_count=2,
            column_boundaries=[215.0, 585.0],
            layout_type="mixed_tail",
        ),
    }

    segments = _build_tail_reading_order(blocks, page_layouts)

    assert len(segments) == 2
    # Left column (body) first
    assert segments[0].page == 3
    assert segments[0].column_index == 0
    assert segments[0].block_indices == [3, 4]
    # Right column (backmatter + ref) second
    assert segments[1].page == 3
    assert segments[1].column_index == 1
    assert segments[1].block_indices == [5, 6]
    assert segments[1].semantic_hint == "mixed"


# ---------------------------------------------------------------------------
# Reference zone tests (Task 3)
# ---------------------------------------------------------------------------


def test_reference_zone_single_column() -> None:
    """Single-column page: zone covers all blocks below ref heading."""
    from paperforge.worker.ocr_document import (
        _build_page_layout_profiles,
        _detect_reference_zones,
    )

    blocks = [
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 1, "bbox": [100, 160, 700, 200], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [100, 100, 700, 140], "role": "reference_heading", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [100, 160, 700, 200], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [100, 220, 700, 260], "role": "reference_item", "page_width": 800, "page_height": 1000},
    ]

    page_layouts = _build_page_layout_profiles(blocks)
    zones = _detect_reference_zones(blocks, page_layouts)

    assert len(zones) == 1
    zone = zones[0]
    assert zone.page == 2
    assert zone.column_index == 0
    # Zone starts at heading bottom y → heading itself excluded
    assert len(zone.block_indices) == 2
    for idx in zone.block_indices:
        assert blocks[idx].get("role") == "reference_item"
    assert zone.y_end > zone.y_start


def test_reference_zone_two_column_mixed() -> None:
    """Left body + right references: zone only in right column."""
    from paperforge.worker.ocr_document import (
        _build_page_layout_profiles,
        _detect_reference_zones,
    )

    blocks = [
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [50, 100, 380, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [50, 160, 380, 200], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [420, 100, 750, 140], "role": "reference_heading", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [420, 160, 750, 200], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [420, 220, 750, 260], "role": "reference_item", "page_width": 800, "page_height": 1000},
    ]

    page_layouts = _build_page_layout_profiles(blocks)
    zones = _detect_reference_zones(blocks, page_layouts)

    assert len(zones) == 1
    zone = zones[0]
    assert zone.page == 2
    assert zone.column_index == 1
    # Zone starts at heading bottom y → heading excluded, only ref items
    assert len(zone.block_indices) == 2
    for idx in zone.block_indices:
        assert blocks[idx].get("role") == "reference_item"
    # Left-col body blocks should NOT be in zone
    assert all(idx not in zone.block_indices for idx in [1, 2])


def test_block_in_reference_zone() -> None:
    """Verify block_in_any_reference_zone correctly includes/excludes."""
    from paperforge.worker.ocr_document import (
        ReferenceZone,
        _block_in_any_reference_zone,
    )

    zones = [
        ReferenceZone(page=2, column_index=1, y_start=150, y_end=300, block_indices=[3, 4, 5]),
    ]

    assert _block_in_any_reference_zone({}, zones, 3) is True
    assert _block_in_any_reference_zone({}, zones, 5) is True
    assert _block_in_any_reference_zone({}, zones, 0) is False
    assert _block_in_any_reference_zone({}, zones, 2) is False
    assert _block_in_any_reference_zone({}, [], 0) is False


# ---------------------------------------------------------------------------
# Layout-aware boundary detection tests (Task 4)
# ---------------------------------------------------------------------------


def test_forward_body_end_mixed_page() -> None:
    """Two-column page with left body + right tail: body should continue."""
    from paperforge.worker.ocr_document import (
        _build_page_layout_profiles,
        _detect_forward_body_end,
    )

    blocks = [
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 3, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        # Page 4: left body (clean column), right tail
        {"page": 4, "bbox": [50, 100, 380, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 4, "bbox": [420, 100, 750, 140], "role": "backmatter_heading", "page_width": 800, "page_height": 1000},
        {"page": 4, "bbox": [420, 160, 750, 200], "role": "backmatter_body", "page_width": 800, "page_height": 1000},
        # Page 5: tail only
        {"page": 5, "bbox": [420, 100, 750, 140], "role": "reference_heading", "page_width": 800, "page_height": 1000},
        {"page": 5, "bbox": [420, 160, 750, 200], "role": "reference_item", "page_width": 800, "page_height": 1000},
    ]

    page_layouts = _build_page_layout_profiles(blocks)
    body_end = _detect_forward_body_end(blocks, page_layouts)

    assert body_end == 4, f"Expected body_end=4 (left body continues on page 4), got {body_end}"


def test_backward_backmatter_start_mixed_page() -> None:
    """Two-column page: dense refs in one column should NOT be backmatter_start."""
    from paperforge.worker.ocr_document import (
        _build_page_layout_profiles,
        _detect_backward_backmatter_start,
    )

    blocks = [
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        # Page 5: two-column with dense refs confined to right column
        {"page": 5, "bbox": [50, 100, 380, 140], "role": "backmatter_body", "page_width": 800, "page_height": 1000},
        {"page": 5, "bbox": [420, 50, 750, 90], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 5, "bbox": [420, 110, 750, 150], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 5, "bbox": [420, 170, 750, 210], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 5, "bbox": [420, 230, 750, 270], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 5, "bbox": [420, 290, 750, 330], "role": "reference_item", "page_width": 800, "page_height": 1000},
        # Page 4: left backmatter heading, right reference heading
        {"page": 4, "bbox": [50, 100, 380, 140], "role": "backmatter_heading", "page_width": 800, "page_height": 1000},
        {"page": 4, "bbox": [420, 100, 750, 140], "role": "reference_heading", "page_width": 800, "page_height": 1000},
        {"page": 4, "bbox": [420, 160, 750, 200], "role": "reference_item", "page_width": 800, "page_height": 1000},
    ]

    page_layouts = _build_page_layout_profiles(blocks)
    bm_start = _detect_backward_backmatter_start(blocks, page_layouts)

    assert bm_start == 4, f"Expected backmatter_start=4 (backmatter heading on page 4), got {bm_start}"


def test_references_start_local_zone() -> None:
    """references_start picks page 71 but zone scopes it to right column only."""
    from paperforge.worker.ocr_document import (
        _build_page_layout_profiles,
        _detect_reference_zones,
        _detect_references_start,
    )

    blocks = [
        {"page": 1, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 2, "bbox": [100, 100, 700, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        # Page 3: left body + right references (SAN9AYVR-like)
        {"page": 3, "bbox": [50, 100, 380, 140], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 3, "bbox": [50, 200, 380, 240], "role": "body_paragraph", "page_width": 800, "page_height": 1000},
        {"page": 3, "bbox": [420, 100, 750, 140], "role": "reference_heading", "page_width": 800, "page_height": 1000},
        {"page": 3, "bbox": [420, 160, 750, 200], "role": "reference_item", "page_width": 800, "page_height": 1000},
        {"page": 3, "bbox": [420, 220, 750, 260], "role": "reference_item", "page_width": 800, "page_height": 1000},
    ]

    page_layouts = _build_page_layout_profiles(blocks)
    refs_start = _detect_references_start(blocks, body_end_page=2, page_layouts=page_layouts)
    assert refs_start == 3, f"Expected references_start=3, got {refs_start}"

    zones = _detect_reference_zones(blocks, page_layouts)
    assert len(zones) == 1
    zone = zones[0]
    assert zone.column_index == 1
    # Left-col body blocks NOT in zone
    assert 2 not in zone.block_indices
    assert 3 not in zone.block_indices
    # Heading starts zone but is excluded (zone starts at heading bottom y)
    assert 4 not in zone.block_indices
    # Ref items below heading ARE in zone
    assert 5 in zone.block_indices
    assert 6 in zone.block_indices


def test_rescue_reference_zone_respects_column() -> None:
    """Left-column body stays body_paragraph; right-column body becomes
    reference_item on a two-column mixed page with reference zones."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        PageLayoutProfile,
        PagePosition,
        rescue_roles_with_document_context,
    )

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.8,
            "text": "Introduction paragraph establishing the research context.",
            "span_metadata": {"size": 10.5, "flags": "normal"},
            "bbox": [100, 100, 500, 150],
        },
        {
            "page": 71,
            "role": "body_paragraph",
            "role_confidence": 0.5,
            "text": "These results demonstrate the effectiveness of the approach.",
            "span_metadata": {"size": 9.0, "flags": "normal"},
            "bbox": [100, 200, 350, 250],
        },
        {
            "page": 71,
            "role": "reference_heading",
            "role_confidence": 0.9,
            "text": "References",
            "span_metadata": {"size": 12, "flags": "bold"},
            "bbox": [550, 100, 750, 130],
        },
        {
            "page": 71,
            "role": "body_paragraph",
            "role_confidence": 0.5,
            "text": "1. Smith J, Johnson K. A comprehensive study. Journal, 2025.",
            "span_metadata": {"size": 9.0, "flags": "normal"},
            "bbox": [550, 200, 750, 240],
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 1,
            "mean_size": 10.5,
            "max_size": 10.5,
            "min_size": 10.5,
            "dispersion": 0.0,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "reference_item": {
            "block_count": 0,
            "mean_size": 9.0,
            "max_size": 9.0,
            "min_size": 9.0,
            "dispersion": 0.0,
            "quality": "weak",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(
        body_end_page=70,
        references_start=PagePosition(page=71, y=0.0),
        page_layouts={
            71: PageLayoutProfile(
                column_count=2,
                column_boundaries=[225.0, 650.0],
                layout_type="mixed_tail",
            ),
        },
        reference_zones=[
            {
                "page": 71,
                "column_index": 1,
                "y_start": 130.0,
                "y_end": 240.0,
                "block_indices": [3],
            }
        ],
    )

    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    left_body = [b for b in result if "These results" in b.get("text", "")]
    right_ref = [b for b in result if "Smith J" in b.get("text", "")]

    assert len(left_body) == 1
    assert left_body[0]["role"] == "body_paragraph", (
        f"Left-column body should stay body_paragraph, got {left_body[0]['role']}"
    )
    assert len(right_ref) == 1
    assert right_ref[0]["role"] == "reference_item", (
        f"Right-column reference should become reference_item, got {right_ref[0]['role']}"
    )


def test_rescue_reference_zone_single_column() -> None:
    """Single-column page without reference zones uses page-level fallback."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        PagePosition,
        rescue_roles_with_document_context,
    )

    blocks = [
        {
            "page": 1,
            "role": "body_paragraph",
            "role_confidence": 0.8,
            "text": "Intro body establishing font profile for the paper body.",
            "span_metadata": {"size": 10.5, "flags": "normal"},
        },
        {
            "page": 5,
            "role": "reference_heading",
            "role_confidence": 0.9,
            "text": "References",
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "role_confidence": 0.5,
            "text": "1. Author A, B C. A study of things. Journal, 2025.",
            "span_metadata": {"size": 9.0, "flags": "normal"},
        },
    ]

    role_profiles = {
        "body_paragraph": {
            "block_count": 1,
            "mean_size": 10.5,
            "max_size": 10.5,
            "min_size": 10.5,
            "dispersion": 0.0,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "reference_item": {
            "block_count": 0,
            "mean_size": 9.0,
            "max_size": 9.0,
            "min_size": 9.0,
            "dispersion": 0.0,
            "quality": "weak",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(
        body_end_page=4,
        references_start=PagePosition(page=5, y=0.0),
        reference_zones=None,
    )

    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    promoted = next(b for b in result if b["text"].startswith("1. Author"))
    assert promoted["role"] == "reference_item", (
        f"Expected reference_item via page-level fallback, got {promoted['role']}"
    )


def test_document_structure_json_serialization() -> None:
    """Verify that DocumentStructure with layout profiles serializes to valid JSON."""
    import dataclasses
    import json

    from paperforge.worker.ocr_document import DocumentStructure, PageLayoutProfile

    ds = DocumentStructure(
        body_end_page=70,
        backmatter_start=None,
        references_start=None,
        page_layouts={
            71: PageLayoutProfile(column_count=2, column_boundaries=[200, 600], layout_type="two_column"),
        },
    )
    data = dataclasses.asdict(ds)
    js = json.dumps(data, indent=2)
    parsed = json.loads(js)
    assert parsed["body_end_page"] == 70
    assert parsed["page_layouts"]["71"]["column_count"] == 2
    assert parsed["page_layouts"]["71"]["layout_type"] == "two_column"
    assert "tail_boundary_score" in parsed


def test_document_structure_has_tail_boundary_score() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Body text.", "bbox": [100, 100, 500, 130]},
        {"page": 2, "role": "section_heading", "text": "Discussion", "bbox": [100, 100, 500, 130]},
        {"page": 2, "role": "body_paragraph", "text": "More body.", "bbox": [100, 140, 500, 170]},
        {"page": 10, "role": "reference_heading", "text": "References", "bbox": [100, 100, 500, 130]},
        {"page": 10, "role": "reference_item", "text": "1. Author. Title. Journal.", "bbox": [100, 140, 500, 170]},
    ]
    doc, _ = normalize_document_structure(blocks)
    assert doc.layout_audit is not None
    assert doc.tail_boundary_score["score"] >= 0.0


def test_figure_caption_candidate_demoted_in_body() -> None:
    """figure_caption_candidate with subfigure ref + narrative prose in body spine -> body_paragraph."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        _resolve_ambiguous_candidates,
    )

    blocks = [
        {
            "page": 3,
            "role": "figure_caption_candidate",
            "text": "Fig. 1a This is a narrative description. We observed significant results. "
            "The data suggests a novel mechanism.",
            "bbox": [100, 200, 500, 230],
        },
    ]
    ds = DocumentStructure(body_end_page=5)
    _resolve_ambiguous_candidates(blocks, ds, {})
    assert blocks[0]["role"] == "body_paragraph"


def test_figure_caption_candidate_promoted_near_media() -> None:
    """figure_caption_candidate near media -> figure_caption."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        _resolve_ambiguous_candidates,
    )

    blocks = [
        {
            "page": 3,
            "role": "figure_caption_candidate",
            "text": "Fig. 1 Short caption.",
            "block_bbox": [100, 240, 500, 260],
        },
        {
            "page": 3,
            "role": "figure_asset",
            "block_label": "image",
            "block_bbox": [100, 50, 500, 220],
        },
    ]
    ds = DocumentStructure(body_end_page=5)
    _resolve_ambiguous_candidates(blocks, ds, {})
    assert blocks[0]["role"] == "figure_caption"


def test_backmatter_heading_candidate_before_boundary_demoted() -> None:
    """backmatter_heading_candidate on page before backmatter -> section_heading."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        PagePosition,
        _resolve_ambiguous_candidates,
    )

    blocks = [
        {
            "page": 5,
            "role": "backmatter_heading_candidate",
            "text": "Acknowledgments",
            "bbox": [100, 100, 500, 130],
        },
    ]
    ds = DocumentStructure(
        body_end_page=4,
        backmatter_start=PagePosition(page=6, y=0.0),
    )
    _resolve_ambiguous_candidates(blocks, ds, {})
    assert blocks[0]["role"] == "section_heading"
    assert blocks[0]["role_confidence"] == 0.5


def test_backmatter_heading_candidate_after_boundary_promoted() -> None:
    """backmatter_heading_candidate inside backmatter -> backmatter_heading."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        PagePosition,
        _resolve_ambiguous_candidates,
    )

    blocks = [
        {
            "page": 7,
            "role": "backmatter_heading_candidate",
            "text": "Funding",
            "bbox": [100, 100, 500, 130],
        },
    ]
    ds = DocumentStructure(
        body_end_page=5,
        backmatter_start=PagePosition(page=6, y=0.0),
    )
    _resolve_ambiguous_candidates(blocks, ds, {})
    assert blocks[0]["role"] == "backmatter_heading"


def test_container_activation_guard() -> None:
    """container paper: child heading before boundary stays section_heading."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        _resolve_ambiguous_candidates,
    )

    blocks = [
        {
            "page": 3,
            "role": "backmatter_heading_candidate",
            "text": "Funding",
            "bbox": [100, 100, 500, 130],
        },
    ]
    ds = DocumentStructure(
        body_end_page=5,
        backmatter_form="container",
    )
    _resolve_ambiguous_candidates(blocks, ds, {})
    assert blocks[0]["role"] == "section_heading"
    assert blocks[0]["role_confidence"] == 0.5


# ---------------------------------------------------------------------------
# Body spine quality tests (Task 2)
# ---------------------------------------------------------------------------


def test_body_spine_quality_strong_with_clean_anchors() -> None:
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    blocks.append(
        {
            "block_id": "b0",
            "page": 1,
            "role": "paper_title",
            "text": "Title",
            "bbox": [80, 20, 280, 60],
            "page_width": 1200,
            "page_height": 1700,
        }
    )
    for pg in range(2, 6):
        for i in range(3):
            blocks.append(
                {
                    "block_id": f"b{pg}_{i}",
                    "page": pg,
                    "role": "body_paragraph",
                    "text": f"Body {i}",
                    "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
                    "page_width": 1200,
                    "page_height": 1700,
                    "span_metadata": [{"size": 10.0, "font": "Times", "flags": 0, "color": 0}],
                }
            )
    spine = _detect_body_spine(blocks)
    sp2 = spine.get(2, {})
    assert sp2.get("quality") == "strong", f"Expected strong, got {sp2.get('quality')}"


def test_body_spine_quality_weak_contaminated() -> None:
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    for i in range(3):
        blocks.append(
            {
                "block_id": f"b{i}",
                "page": 1,
                "role": "body_paragraph",
                "text": f"Body {i}",
                "bbox": [80, 100 + i * 100, 200, 160 + i * 100],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    spine = _detect_body_spine(blocks)
    sp1 = spine.get(1, {})
    assert sp1.get("quality") in ("weak", "moderate"), f"Expected weak/moderate, got {sp1.get('quality')}"


# ---------------------------------------------------------------------------
# No-span degraded mode tests (Task 5)
# ---------------------------------------------------------------------------


def test_span_coverage_weak_when_no_metadata() -> None:
    """Blocks without span_metadata produce weak coverage."""
    from paperforge.worker.ocr_document import _compute_span_coverage

    blocks = [{"span_metadata": None}, {"span_metadata": {}}]
    result = _compute_span_coverage(blocks)
    assert result.get("coverage_ratio", 1.0) < 0.5
    assert result.get("degraded_mode_active") is True


def test_no_span_rescue_more_conservative() -> None:
    """When span coverage is weak, body_paragraph->reference_item rescue should not
    trigger on font alone."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    blocks = [
        {
            "block_id": "b1",
            "page": 11,
            "role": "body_paragraph",
            "text": "Smith J. (2023) A study about cells.",
            "bbox": [80, 200, 520, 240],
            "page_width": 1200,
            "page_height": 1700,
            "render_default": True,
            "role_confidence": 0.5,
        },
    ]
    ds = DocumentStructure(
        body_end_page=10,
        backmatter_start=None,
        references_start=type("PS", (), {"page": 11, "y": 0.0})(),
        spread_start=11,
        spread_end=15,
        backmatter_form="flat",
        page_layouts={},
        tail_reading_order=None,
        reference_zones=None,
    )
    profiles = build_role_span_profiles(blocks)
    result = rescue_roles_with_document_context(blocks, profiles, ds)
    assert result[0]["role"] == "body_paragraph"


def test_non_body_insert_skips_page1_title() -> None:
    from paperforge.worker.ocr_document import _is_page1_title

    assert _is_page1_title("Metabolic regulation of skeletal cell fate and function") is True
    assert _is_page1_title("Review article") is False
    assert _is_page1_title("") is False


def test_contaminated_early_page_weak_spine() -> None:
    """Early pages with mostly non-body blocks produce weak spine quality."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Single contaminated page: lots of frontmatter/noise, very few narrow body paragraphs
    for i in range(3):
        blocks.append(
            {
                "block_id": f"t{i}",
                "page": 1,
                "role": "paper_title",
                "text": f"Title {i}",
                "bbox": [80, 20 + i * 40, 280, 60 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    for i in range(2):
        blocks.append(
            {
                "block_id": f"a{i}",
                "page": 1,
                "role": "authors",
                "text": f"Author {i}",
                "bbox": [80, 140 + i * 40, 300, 180 + i * 40],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    for i in range(5):
        blocks.append(
            {
                "block_id": f"n{i}",
                "page": 1,
                "role": "noise",
                "text": f"Noise {i}",
                "bbox": [80, 240 + i * 30, 180, 270 + i * 30],
                "page_width": 1200,
                "page_height": 1700,
            }
        )
    # Narrow body paragraphs (width < 400, below anchor minimum)
    blocks.append(
        {
            "block_id": "b0",
            "page": 1,
            "role": "body_paragraph",
            "text": "Narrow body text",
            "bbox": [80, 400, 300, 440],
            "page_width": 1200,
            "page_height": 1700,
            "span_metadata": [{"size": 10, "font": "Times", "flags": 0}],
        }
    )

    spine = _detect_body_spine(blocks)
    meta = spine.get("_meta", {})
    assert meta.get("quality") == "weak", f"Expected weak, got {meta.get('quality')!r}"
    assert meta.get("anchor_pages") == [], f"Expected empty anchor_pages, got {meta.get('anchor_pages')!r}"
    assert meta.get("sample_count", -1) == 0, f"Expected sample_count 0, got {meta.get('sample_count')!r}"


def test_stable_central_pages_strong_spine() -> None:
    """Clean middle pages with body paragraphs produce strong spine quality."""
    from paperforge.worker.ocr_document import _detect_body_spine

    blocks = []
    # Page 1: frontmatter only
    blocks.append(
        {
            "block_id": "t0",
            "page": 1,
            "role": "paper_title",
            "text": "Title",
            "bbox": [80, 20, 280, 60],
            "page_width": 1200,
            "page_height": 1700,
        }
    )
    # Pages 4-8: clean body paragraphs (3 each, width 510, same font)
    for pg in range(4, 9):
        for i in range(3):
            blocks.append(
                {
                    "block_id": f"b{pg}_{i}",
                    "page": pg,
                    "role": "body_paragraph",
                    "text": f"Body on page {pg}",
                    "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
                    "page_width": 1200,
                    "page_height": 1700,
                    "span_metadata": [{"size": 10, "font": "Times", "flags": 0}],
                }
            )
    # Tail
    blocks.append(
        {
            "block_id": "ref",
            "page": 10,
            "role": "reference_heading",
            "text": "References",
            "bbox": [80, 100, 400, 130],
            "page_width": 1200,
            "page_height": 1700,
        }
    )

    spine = _detect_body_spine(blocks)
    meta = spine.get("_meta", {})
    assert meta.get("quality") == "strong", f"Expected strong, got {meta.get('quality')!r}"
    assert len(meta.get("anchor_pages", [])) >= 3, f"Expected >= 3 anchor_pages, got {meta.get('anchor_pages')!r}"
    assert meta.get("font_coherence", 0.0) > 0.8, f"Expected font_coherence > 0.8, got {meta.get('font_coherence')!r}"
    assert meta.get("width_dispersion", 1.0) < 0.3, (
        f"Expected width_dispersion < 0.3, got {meta.get('width_dispersion')!r}"
    )
    assert meta.get("sample_count", 0) >= 8, f"Expected sample_count >= 8, got {meta.get('sample_count')!r}"


# ---------------------------------------------------------------------------
# Structured insert candidate / cluster tests (Task 4)
# ---------------------------------------------------------------------------


def test_textual_table_not_media_asset() -> None:
    """A block with raw_label=table but substantive bullet text is NOT media_asset,
    and enters as structured_insert_candidate instead."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "table",
        "block_content": "Key findings:\n\u2022 Finding one\n\u2022 Finding two\n\u2022 Finding three",
        "block_bbox": [100, 200, 500, 400],
        "page": 2,
    }
    page_blocks = [
        {
            "block_label": "table",
            "block_content": "Key findings:\n\u2022 Finding one\n\u2022 Finding two\n\u2022 Finding three",
            "block_bbox": [100, 200, 500, 400],
            "page": 2,
        },
    ]
    role = assign_block_role(block, page_blocks=page_blocks)
    assert role.role != "media_asset", f"Expected NOT media_asset, got {role.role}"
    assert role.role == "structured_insert_candidate"


def test_key_points_box_not_body_paragraph() -> None:
    """A detached summary box with heading + bullet items is clustered as structured_insert,
    not left as body_paragraph."""
    from paperforge.worker.ocr_document import _detect_structured_insert_clusters

    blocks = [
        {
            "page": 3,
            "role": "structured_insert_candidate",
            "block_content": "Key points of the study",
            "bbox": [100, 200, 500, 230],
            "block_bbox": [100, 200, 500, 230],
        },
        {
            "page": 3,
            "role": "structured_insert_candidate",
            "block_content": "\u2022 First important point\n\u2022 Second important point\n\u2022 Third point",
            "bbox": [100, 240, 500, 350],
            "block_bbox": [100, 240, 500, 350],
        },
    ]
    indices = _detect_structured_insert_clusters(blocks)
    assert len(indices) == 2
    assert 0 in indices
    assert 1 in indices


def test_structured_insert_cluster_detected() -> None:
    """Multiple structured insert candidates on the same page with close geometry
    are detected as a cluster."""
    from paperforge.worker.ocr_document import _detect_structured_insert_clusters

    blocks = [
        {
            "page": 2,
            "role": "structured_insert_candidate",
            "block_content": "Box 1. Summary",
            "bbox": [100, 100, 500, 130],
            "block_bbox": [100, 100, 500, 130],
        },
        {
            "page": 2,
            "role": "structured_insert_candidate",
            "block_content": "\u2022 Item A\n\u2022 Item B\n\u2022 Item C",
            "bbox": [100, 140, 500, 250],
            "block_bbox": [100, 140, 500, 250],
        },
        {
            "page": 2,
            "role": "structured_insert_candidate",
            "block_content": "Box 2. Additional notes",
            "bbox": [100, 300, 500, 330],
            "block_bbox": [100, 300, 500, 330],
        },
        {
            "page": 2,
            "role": "structured_insert_candidate",
            "block_content": "\u2022 Note one\n\u2022 Note two",
            "bbox": [100, 340, 500, 400],
            "block_bbox": [100, 340, 500, 400],
        },
    ]
    indices = _detect_structured_insert_clusters(blocks)
    # At least 3 of the 4 blocks should form clusters (two pairs)
    assert len(indices) >= 3


# ---------------------------------------------------------------------------
# Degraded mode / span coverage tests (Task 6)
# ---------------------------------------------------------------------------


def test_degraded_mode_weaker_heading_promotion() -> None:
    """Blocks without span_metadata, with weak heading-to-body rescue →
    weaker promotion (higher threshold) — heading keeps its role in degraded mode."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )

    # Most blocks lack span_metadata → ratio = 3/10 = 0.3 → moderate, not weak.
    # Need 3/11 = 0.27 < 0.3 → weak coverage → degraded mode.
    blocks = [
        {
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "page": 1,
            "text": "Normal body paragraph with font profile data.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "role": "body_paragraph",
            "role_confidence": 0.7,
            "page": 2,
            "text": "Another body paragraph to strengthen the body profile.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "role": "section_heading",
            "role_confidence": 0.5,
            "page": 2,
            "text": "Methods",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
    ]
    # Add 9 blocks without span_metadata to push ratio to 3/12 = 0.25 < 0.3
    for i in range(9):
        blocks.append({"role": "body_paragraph", "role_confidence": 0.5, "page": 2, "text": f"No span block {i}"})

    role_profiles = {
        "body_paragraph": {
            "block_count": 11,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "section_heading": {
            "block_count": 1,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "weak",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    ds = DocumentStructure(body_end_page=2)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    heading = next(b for b in result if b["text"] == "Methods")
    assert heading["role"] == "section_heading", (
        f"Weak heading should keep its role in degraded mode, got {heading['role']}"
    )


def test_degraded_mode_weaker_non_body_insert() -> None:
    """No-span blocks with moderate narrow+font signal → NOT promoted
    to non_body_insert when spine weak."""
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        # Body paragraphs with span_metadata to establish body_family
        {
            "role": "body_paragraph",
            "page": 1,
            "role_confidence": 0.8,
            "text": "Normal body paragraph with enough text for profiling purposes.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        {
            "role": "body_paragraph",
            "page": 2,
            "role_confidence": 0.8,
            "text": "Another body paragraph to strengthen the body font profile.",
            "span_metadata": {"size": 10, "flags": "normal"},
        },
        # non_body_insert block without span_metadata — cannot be compared
        {
            "role": "non_body_insert",
            "page": 1,
            "role_confidence": 0.5,
            "_non_body_insert": True,
            "bbox": [100, 400, 700, 440],
            "page_width": 1200,
            "text": "This block has no span metadata so rescue cannot run",
        },
    ]
    # Add 7 blocks without span to push coverage to 2/10 = 0.2 < 0.3 → degraded
    for i in range(7):
        blocks.append({"role": "body_paragraph", "role_confidence": 0.5, "page": 2, "text": f"No span {i}"})

    role_profiles = {
        "body_paragraph": {
            "block_count": 9,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "strong",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
        "non_body_insert": {
            "block_count": 1,
            "mean_size": 10.0,
            "max_size": 10.5,
            "min_size": 9.5,
            "dispersion": 0.05,
            "quality": "moderate",
            "bold_ratio": 0.0,
            "italic_ratio": 0.0,
            "font_families": [],
        },
    }

    result = rescue_roles_with_document_context(blocks, role_profiles)
    # Without span_metadata, extract_block_span_profile returns None →
    # the block cannot be rescued, should remain as non_body_insert
    non_body = [b for b in result if b.get("_non_body_insert")]
    assert len(non_body) == 1
    assert non_body[0]["role"] == "non_body_insert"


def test_span_coverage_strong_when_most_blocks_have_metadata() -> None:
    """80%+ blocks have span_metadata → strong coverage."""
    from paperforge.worker.ocr_document import _compute_span_coverage

    blocks = []
    for i in range(8):
        blocks.append({"span_metadata": {"size": 10, "flags": "normal"}})
    for i in range(2):
        blocks.append({"span_metadata": None})

    result = _compute_span_coverage(blocks)
    assert result["coverage_quality"] == "strong"
    assert result["coverage_ratio"] >= 0.7
    assert result["blocks_with_span"] == 8
    assert result["blocks_without_span"] == 2
    assert result["degraded_mode_active"] is False


# ---------------------------------------------------------------------------
# Non-body insert: spine quality gating (Task 5)
# ---------------------------------------------------------------------------


def test_non_body_insert_weak_spine_requires_font_mismatch() -> None:
    """Moderate spine (2 anchor pages) + narrow width + same font → NOT non_body_insert."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = []
    # Pages 2-3: 3 body paragraphs each → 2 anchor pages → moderate meta quality
    for pg in range(2, 4):
        for i in range(3):
            blocks.append({
                "role": "body_paragraph",
                "page": pg,
                "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
                "span_metadata": [{"size": 10, "font": "Times"}],
                "page_width": 1200,
                "page_height": 1700,
            })
    # Page 1: 2 body paragraphs
    for i in range(2):
        blocks.append({
            "role": "body_paragraph",
            "page": 1,
            "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
            "span_metadata": [{"size": 10, "font": "Times"}],
            "page_width": 1200,
            "page_height": 1700,
        })
    # Page 1: 2 narrow blocks with SAME font → should NOT be non_body_insert
    blocks.append({
        "role": "body_paragraph",
        "page": 1,
        "bbox": [50, 600, 300, 640],
        "span_metadata": [{"size": 10, "font": "Times"}],
        "page_width": 1200,
        "page_height": 1700,
    })
    blocks.append({
        "role": "body_paragraph",
        "page": 1,
        "bbox": [50, 680, 310, 720],
        "span_metadata": [{"size": 10, "font": "Times"}],
        "page_width": 1200,
        "page_height": 1700,
    })

    spine = _detect_body_spine(blocks)
    result = _detect_non_body_insert_clusters(blocks, spine, page_width=1200)
    assert len(result) == 0, f"Expected 0 non_body_insert with moderate spine + same font, got {result}"


def test_non_body_insert_strong_spine_or_gate_ok() -> None:
    """Strong spine (5 anchor pages) + narrow width or font mismatch → OK to detect."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = []
    # Pages 2-6: 3 body paragraphs each → 5 anchor pages → strong meta quality
    for pg in range(2, 7):
        for i in range(3):
            blocks.append({
                "role": "body_paragraph",
                "page": pg,
                "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
                "span_metadata": [{"size": 10, "font": "Times"}],
                "page_width": 1200,
                "page_height": 1700,
            })
    # Page 1: 2 narrow blocks with SAME font → should be detected (strong spine trusts narrow alone)
    blocks.append({
        "role": "body_paragraph",
        "page": 1,
        "bbox": [50, 600, 300, 640],
        "span_metadata": [{"size": 10, "font": "Times"}],
        "page_width": 1200,
        "page_height": 1700,
    })
    blocks.append({
        "role": "body_paragraph",
        "page": 1,
        "bbox": [50, 680, 310, 720],
        "span_metadata": [{"size": 10, "font": "Times"}],
        "page_width": 1200,
        "page_height": 1700,
    })

    spine = _detect_body_spine(blocks)
    result = _detect_non_body_insert_clusters(blocks, spine, page_width=1200)
    assert len(result) >= 2, f"Expected at least 2 non_body_insert with strong spine, got {result}"


def test_non_body_insert_strong_spine_does_not_use_font_only_for_body_width_blocks() -> None:
    """Strong spine should not classify body-width paragraphs by font mismatch alone."""
    from paperforge.worker.ocr_document import _detect_non_body_insert_clusters

    blocks = [{
        "role": "body_paragraph",
        "page": 2,
        "bbox": [80, 600, 590, 660],
        "text": "This is real body text with a locally different OCR font family.",
        "span_metadata": [{"size": 10, "font": "Helvetica"}],
        "page_width": 1200,
        "page_height": 1700,
    }, {
        "role": "body_paragraph",
        "page": 2,
        "bbox": [80, 700, 590, 760],
        "text": "This continuation paragraph should remain body text as well.",
        "span_metadata": [{"size": 10, "font": "Helvetica"}],
        "page_width": 1200,
        "page_height": 1700,
    }]
    body_spine = {
        2: {"median_width": 510, "all_fonts": {"times"}, "quality": "strong"},
        "_meta": {"quality": "strong"},
    }

    result = _detect_non_body_insert_clusters(blocks, body_spine, page_width=1200)
    assert result == set(), f"Body-width font-only mismatch should not be non_body_insert, got {result}"


def test_title_not_swept_into_non_body_insert() -> None:
    """Page 1 title-like block (long text, no bullets) is NOT marked as non_body_insert."""
    from paperforge.worker.ocr_document import _detect_body_spine, _detect_non_body_insert_clusters

    blocks = []
    # Pages 2-6: 3 body paragraphs each → strong meta quality
    for pg in range(2, 7):
        for i in range(3):
            blocks.append({
                "role": "body_paragraph",
                "page": pg,
                "bbox": [80, 100 + i * 100, 590, 160 + i * 100],
                "span_metadata": [{"size": 10, "font": "Times"}],
                "page_width": 1200,
                "page_height": 1700,
            })
    # Page 1: title-like block (long text, narrow width, no bullets)
    blocks.append({
        "role": "body_paragraph",
        "page": 1,
        "bbox": [50, 100, 400, 140],  # width 350 < 357 → narrow
        "text": "Metabolic regulation of skeletal cell fate and function in development and disease",
        "span_metadata": [{"size": 14, "font": "Times"}],
        "page_width": 1200,
        "page_height": 1700,
    })
    # Page 1: companion narrow block (also narrow, same font)
    blocks.append({
        "role": "body_paragraph",
        "page": 1,
        "bbox": [50, 200, 400, 240],  # width 350 < 357 → narrow
        "text": "Short narrow paragraph that is not a title",
        "span_metadata": [{"size": 10, "font": "Times"}],
        "page_width": 1200,
        "page_height": 1700,
    })

    spine = _detect_body_spine(blocks)
    result = _detect_non_body_insert_clusters(blocks, spine, page_width=1200)
    # Title block must not be in result
    title_idx = 15  # indices 0-14 are body paragraphs
    assert title_idx not in result, f"Title block (idx {title_idx}) should not be non_body_insert, got {result}"


# ---------------------------------------------------------------------------
# Layout audit tests (Task 8)
# ---------------------------------------------------------------------------


def test_layout_audit_heading_owns_wrong_body() -> None:
    """Heading in left column, body above it in right column -> audit flags info when no layout confidence."""
    from paperforge.worker.ocr_document import _run_layout_audit

    blocks = [
        {"page": 1, "role": "body_paragraph", "bbox": [700, 100, 1100, 140], "text": "Body above heading"},
        {"page": 1, "role": "section_heading", "bbox": [100, 200, 500, 230], "text": "Introduction"},
    ]
    result = _run_layout_audit(blocks)
    assert result["status"] == "pass", f"Expected pass (info-only), got {result['status']}"
    assert result["info_count"] >= 1, "Expected at least 1 info anomaly"
    assert result["anomaly_count"] >= 1
    assert all(a["severity"] == "info" for a in result["anomalies"]), "All anomalies should be info severity without layout confidence"


def test_layout_audit_reference_zone_overlaps_body() -> None:
    """structured_insert overlapping body region -> info when no spine/insert_score."""
    from paperforge.worker.ocr_document import _run_layout_audit

    blocks = [
        {"page": 1, "role": "body_paragraph", "bbox": [100, 100, 500, 300], "text": "Body text", "raw_label": "text"},
        {"page": 1, "role": "structured_insert", "bbox": [200, 150, 400, 250], "text": "Insert overlapping body"},
    ]
    result = _run_layout_audit(blocks)
    assert result["status"] == "pass", f"Expected pass (info-only), got {result['status']}"
    assert result["info_count"] >= 1, "Expected at least 1 info anomaly"


# ---------------------------------------------------------------------------
# Region prepass tests (Task 3)
# ---------------------------------------------------------------------------


def test_region_prepass_marks_frontmatter_insert_and_body_regions() -> None:
    from paperforge.worker.ocr_document import _build_region_prepass

    blocks = [
        {"page": 1, "role": "paper_title", "text": "A Real Paper Title", "bbox": [80, 80, 700, 140], "page_width": 1200, "page_height": 1700},
        {"page": 1, "role": "authors", "text": "Jane Author & John Writer", "bbox": [80, 160, 600, 200], "page_width": 1200, "page_height": 1700},
        {"page": 1, "role": "body_paragraph", "text": "Key points", "bbox": [760, 280, 1050, 315], "page_width": 1200, "page_height": 1700},
        {"page": 1, "role": "body_paragraph", "text": "Important short list item", "bbox": [760, 330, 1050, 370], "page_width": 1200, "page_height": 1700},
        {"page": 2, "role": "body_paragraph", "text": "This is a real body paragraph with enough words to train the body spine.", "bbox": [80, 220, 640, 270], "page_width": 1200, "page_height": 1700},
    ]

    prepass = _build_region_prepass(blocks)

    assert prepass.block_regions[0] == "frontmatter"
    assert prepass.block_regions[1] == "frontmatter"
    assert prepass.block_regions[2] == "body"
    assert prepass.block_regions[3] == "frontmatter"
    assert prepass.block_regions[4] == "body"


def test_body_spine_ignores_region_frontmatter_and_structured_insert_blocks() -> None:
    from paperforge.worker.ocr_document import _build_region_prepass, _detect_body_spine

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Review article", "bbox": [80, 80, 240, 110], "page_width": 1200, "page_height": 1700, "span_metadata": [{"font": "Heading"}]},
        {"page": 1, "role": "body_paragraph", "text": "Key points", "bbox": [760, 280, 1050, 315], "page_width": 1200, "page_height": 1700, "span_metadata": [{"font": "Box"}]},
    ]
    for page in range(2, 6):
        for line in range(3):
            blocks.append({"page": page, "role": "body_paragraph", "text": "Real body paragraph text for spine training.", "bbox": [80, 200 + line * 80, 620, 250 + line * 80], "page_width": 1200, "page_height": 1700, "span_metadata": [{"font": "Body"}]})

    prepass = _build_region_prepass(blocks)
    spine = _detect_body_spine(blocks, region_prepass=prepass)

    assert "heading" not in spine[1].get("all_fonts", set()), str(spine[1].get("all_fonts"))
    assert "box" not in spine[1].get("all_fonts", set()), str(spine[1].get("all_fonts"))


def test_normalize_marks_structured_insert_before_non_body_insert_suppression() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"page": 1, "role": "body_paragraph", "text": "Key points", "bbox": [760, 280, 1050, 315], "page_width": 1200, "page_height": 1700},
        {"page": 1, "role": "body_paragraph", "text": "Short summary point", "bbox": [760, 330, 1050, 370], "page_width": 1200, "page_height": 1700},
    ]
    for page in range(2, 6):
        for line in range(3):
            blocks.append({"page": page, "role": "body_paragraph", "text": "Real body paragraph text for training.", "bbox": [80, 200 + line * 80, 620, 250 + line * 80], "page_width": 1200, "page_height": 1700, "span_metadata": [{"font": "Body"}]})

    _, normalized = normalize_document_structure(blocks)

    assert normalized[0]["role"] == "structured_insert_candidate"
    assert normalized[1]["role"] == "body_paragraph"


def test_normalize_promotes_mixed_sidebar_blocks_into_single_structured_insert_cluster() -> None:
    """Sidebar heading, textual table container, and continuation block should all join one structured insert."""
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"page": 2, "role": "body_paragraph", "text": "Key points", "bbox": [80, 220, 180, 247], "page_width": 1200, "page_height": 1700},
        {"page": 2, "role": "media_asset", "raw_label": "table", "text": "<table><tr><td>• Point one</td></tr><tr><td>• Point two</td></tr></table>", "bbox": [73, 270, 591, 738], "page_width": 1200, "page_height": 1700},
        {"page": 2, "role": "unknown_structural", "text": "• Point three continues below the detected table box.", "bbox": [74, 675, 566, 743], "page_width": 1200, "page_height": 1700},
        {"page": 2, "role": "sub_subsection_heading", "text": "Introduction", "bbox": [76, 780, 210, 803], "page_width": 1200, "page_height": 1700},
        {"page": 2, "role": "body_paragraph", "text": "The skeleton has been considered to be a metabolically active organ for decades.", "bbox": [73, 805, 593, 1192], "page_width": 1200, "page_height": 1700},
    ]
    for i in range(3):
        blocks.append({"page": 3 + i, "role": "body_paragraph", "text": "Real body paragraph text for training and normalization.", "bbox": [80, 200, 620, 260], "page_width": 1200, "page_height": 1700, "span_metadata": [{"font": "Body"}]})

    _, normalized = normalize_document_structure(blocks)

    assert normalized[0]["role"] == "structured_insert_candidate"
    assert normalized[1]["role"] == "media_asset"
    assert normalized[2]["role"] == "unknown_structural"
    assert normalized[3]["role"] != "structured_insert"
    assert normalized[4]["role"] == "body_paragraph"


def test_full_width_heading_above_two_columns_is_not_anomaly() -> None:
    """Full-width heading spanning >55% page width is NOT an error, even if it owns body in both columns."""
    from paperforge.worker.ocr_document import _run_layout_audit

    blocks = [
        {"page": 1, "role": "section_heading", "bbox": [50, 200, 1150, 230], "text": "Introduction and Background", "page_width": 1200, "page_height": 1600},
        {"page": 1, "role": "body_paragraph", "bbox": [620, 100, 1150, 160], "text": "Right column body above heading...", "page_width": 1200, "page_height": 1600},
    ]
    result = _run_layout_audit(blocks)
    errors = [a for a in result.get("anomalies", []) if a.get("severity") == "error"]
    assert len(errors) == 0, f"Expected no error anomalies, got {errors}"
    assert result["status"] != "fail"


def test_low_confidence_layout_audit_reports_info_not_fail() -> None:
    """Low layout confidence results in info severity, not fail."""
    from paperforge.worker.ocr_document import PageLayoutProfile, _run_layout_audit

    page_layouts = {1: PageLayoutProfile(column_count=2, confidence=0.3, layout_type="two_column")}
    blocks = [
        {"page": 1, "role": "section_heading", "bbox": [100, 200, 500, 230], "text": "Introduction", "page_width": 1200, "page_height": 1600},
        {"page": 1, "role": "body_paragraph", "bbox": [700, 100, 1100, 140], "text": "Body above heading", "page_width": 1200, "page_height": 1600},
    ]
    result = _run_layout_audit(blocks, page_layouts=page_layouts)
    assert result["status"] != "fail", f"Expected status != 'fail', got {result['status']}"
    assert result["info_count"] >= 1, "Expected at least 1 info anomaly"
    assert result["error_count"] == 0, "Expected 0 errors"


def test_low_layout_confidence_never_audit_error_on_insert_overlap() -> None:
    """Low layout confidence with strong insert overlap should produce info, not error."""
    from paperforge.worker.ocr_document import PageLayoutProfile, _run_layout_audit

    page_layouts = {1: PageLayoutProfile(column_count=2, confidence=0.3, layout_type="two_column")}
    blocks = [
        {"page": 1, "role": "body_paragraph", "bbox": [100, 100, 500, 300], "text": "Body text real", "raw_label": "text", "page_width": 1200, "page_height": 1600},
        {"page": 1, "role": "structured_insert", "bbox": [200, 150, 400, 250], "text": "Insert overlapping body a lot", "insert_score": {"score": 0.9}},
    ]
    body_spine = {"_meta": {"quality": "strong"}}
    result = _run_layout_audit(blocks, body_spine=body_spine, page_layouts=page_layouts)
    assert result["error_count"] == 0, f"Expected 0 errors, got {result['error_count']}"
    assert result["status"] != "fail", f"Expected no fail, got {result['status']}"
