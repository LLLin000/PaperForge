from __future__ import annotations

import pytest


def test_middle_page_body_family_anchor_uses_dominant_repeated_family() -> None:
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {
            "page": 3,
            "text": "Long body text A " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "page": 4,
            "text": "Long body text B " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "x_center": 242},
        },
        {
            "page": 4,
            "text": "Figure 1.",
            "marker_signature": {"type": "figure_number"},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 210, "x_center": 260},
        },
    ]

    anchor = discover_body_family_anchor(blocks, page_count=8)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "body_family"
    assert anchor["sample_pages"] == [3, 4]


def test_body_family_anchor_excludes_last_page_for_small_documents() -> None:
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {
            "page": 2,
            "text": "Core body text A " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "page": 3,
            "text": "Core body text B " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "x_center": 242},
        },
        {
            "page": 4,
            "text": "Tail text A " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 250, "x_center": 230},
        },
        {
            "page": 5,
            "text": "Tail text B " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 250, "x_center": 230},
        },
        {
            "page": 5,
            "text": "Tail text C " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 250, "x_center": 230},
        },
    ]

    anchor = discover_body_family_anchor(blocks, page_count=5)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "body_family"
    assert anchor["sample_pages"] == [2, 3]


def test_body_family_anchor_skips_media_dominated_pages_by_area() -> None:
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {
            "page": 3,
            "text": "Body text page three " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "height": 110, "x_center": 240},
            "bbox": [100, 100, 360, 210],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "page": 4,
            "text": "Figure 1.",
            "marker_signature": {"type": "figure_number"},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 560, "height": 520, "x_center": 300},
            "bbox": [20, 80, 580, 600],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "page": 4,
            "text": "Body text on contaminated page " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "height": 110, "x_center": 240},
            "bbox": [100, 620, 360, 730],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "page": 5,
            "text": "Body text page five " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "height": 112, "x_center": 242},
            "bbox": [100, 100, 362, 212],
            "page_width": 600,
            "page_height": 800,
        },
    ]

    anchor = discover_body_family_anchor(blocks, page_count=8)

    assert anchor["status"] == "ACCEPT"
    assert anchor["sample_pages"] == [3, 5]


def test_body_family_anchor_skips_reference_like_tail_pages() -> None:
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {
            "page": 3,
            "text": "Body text page three " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "page": 4,
            "text": "[1] Smith et al. 2020 Journal entry text " * 4,
            "marker_signature": {"type": "reference_numeric_bracket"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 255, "x_center": 238},
        },
        {
            "page": 5,
            "text": "Body text page five " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "x_center": 242},
        },
    ]

    anchor = discover_body_family_anchor(blocks, page_count=8)

    assert anchor["status"] == "ACCEPT"
    assert anchor["sample_pages"] == [3, 5]


def test_body_family_anchor_skips_frontmatter_like_pages() -> None:
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {
            "page": 2,
            "text": "$^{1}$ Department of Testing, Example University",
            "marker_signature": {"type": "affiliation_marker"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 280, "x_center": 260},
        },
        {
            "page": 3,
            "text": "Body text page three " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260, "x_center": 240},
        },
        {
            "page": 4,
            "text": "Body text page four " * 8,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 262, "x_center": 242},
        },
    ]

    anchor = discover_body_family_anchor(blocks, page_count=8)

    assert anchor["status"] == "ACCEPT"
    assert anchor["sample_pages"] == [3, 4]


def test_body_family_anchor_is_not_fragmented_by_line_or_length_buckets() -> None:
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {
            "page": 3,
            "text": "Dense body paragraph with stable styling " * 6,
            "marker_signature": {"type": "none"},
            "span_signature": {
                "font_size_median": 9.0,
                "font_size_bucket": 9.0,
                "font_family_norm": "Times",
            },
            "layout_signature": {
                "width": 260,
                "width_bucket": 250,
                "x_center": 240,
                "x_center_bucket": 250,
                "line_count": 5,
            },
        },
        {
            "page": 4,
            "text": "Dense body paragraph with a few extra words for variation " * 6,
            "marker_signature": {"type": "none"},
            "span_signature": {
                "font_size_median": 9.0,
                "font_size_bucket": 9.0,
                "font_family_norm": "Times",
            },
            "layout_signature": {
                "width": 262,
                "width_bucket": 250,
                "x_center": 242,
                "x_center_bucket": 250,
                "line_count": 9,
            },
        },
    ]

    anchor = discover_body_family_anchor(blocks, page_count=8)

    assert anchor["status"] == "ACCEPT"
    assert anchor["sample_pages"] == [3, 4]


def test_reference_family_anchor_comes_from_marker_and_family_evidence_not_final_role() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 8,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 8,
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 8,
            "text": "[2] Another reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"
    assert anchor["item_count"] == 2


def test_reference_family_anchor_heading_is_binding_but_not_sufficient_alone() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 8,
            "text": "Bibliography",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 8,
            "text": "Closing remarks without numbered references",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks)

    assert anchor["status"] == "HOLD"
    assert anchor["family_name"] == "reference_family"


def test_reference_family_anchor_can_accept_without_heading_when_tail_family_is_strong() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 9,
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[2] Another reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[3] Third reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 3},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks, page_count=10)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"


def test_reference_family_anchor_scopes_marker_count_to_winning_family() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 10,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[1] Example reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[2] Another reference",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
        {
            "page": 3,
            "text": "[99] Unrelated inline note",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 99},
            "span_signature": {"font_size_median": 7.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 180, "x_center": 520},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks, page_count=10)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"
    assert anchor["marker_count"] == 2


def test_reference_family_anchor_prefers_best_tail_family_over_bigger_non_tail_family() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 3,
            "text": "[1] Early inline note",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 7.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 180, "x_center": 520},
            "role": "unassigned",
        },
        {
            "page": 4,
            "text": "[2] Another inline note",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 7.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 182, "x_center": 518},
            "role": "unassigned",
        },
        {
            "page": 5,
            "text": "[3] Third inline note",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 3},
            "span_signature": {"font_size_median": 7.0, "font_family_norm": "Arial"},
            "layout_signature": {"width": 181, "x_center": 521},
            "role": "unassigned",
        },
        {
            "page": 9,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 9,
            "text": "[10] Tail reference one",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 10},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[11] Tail reference two",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 11},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[12] Tail reference three",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 12},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 251, "x_center": 241},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks, page_count=10)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"
    assert anchor["font_family_norm"] == "Times"
    assert anchor["sample_pages"] == [9, 10]


def test_reference_family_anchor_rejects_fragmented_tail_family() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 8,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 8,
            "text": "[1] Fragmented reference one",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "[2] Fragmented reference two",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks, page_count=10)

    assert anchor["status"] == "HOLD"
    assert anchor["family_name"] == "reference_family"


def test_reference_family_anchor_accepts_near_terminal_tail_family_with_late_non_reference_page() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 8,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 8,
            "text": "[1] Tail reference one",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 9,
            "text": "[2] Tail reference two",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "Appendix A. Supplementary author notes",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 320, "x_center": 250},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks, page_count=10)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"
    assert anchor["sample_pages"] == [8, 9]


def test_reference_family_anchor_accepts_single_page_penultimate_tail_family() -> None:
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {
            "page": 9,
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
            "layout_signature": {"width": 120},
            "role": "unassigned",
        },
        {
            "page": 9,
            "text": "[1] Tail reference one",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "x_center": 240},
            "role": "unassigned",
        },
        {
            "page": 9,
            "text": "[2] Tail reference two",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 2},
            "span_signature": {"font_size_median": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 252, "x_center": 242},
            "role": "unassigned",
        },
        {
            "page": 10,
            "text": "Appendix A. Supplementary author notes",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 320, "x_center": 250},
            "role": "unassigned",
        },
    ]

    anchor = discover_reference_family_anchor(blocks, page_count=10)

    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"
    assert anchor["sample_pages"] == [9]


def test_partition_zone_families_separates_legend_like_from_body_like() -> None:
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {
            "block_id": "p4_b1",
            "zone": "body_zone",
            "text": "Long narrative paragraph " * 6,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260},
        },
        {
            "block_id": "p4_b2",
            "zone": "body_zone",
            "text": "Figure 2. Long legend text",
            "marker_signature": {"type": "figure_number", "number": 2},
            "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 220},
        },
    ]
    anchors = {"body_family_anchor": {"status": "ACCEPT", "family_name": "body_family"}}

    partitioned = partition_zone_families(blocks, anchors)
    assert partitioned["p4_b1"]["style_family"] == "body_like"
    assert partitioned["p4_b2"]["style_family"] == "legend_like"


def test_partition_zone_families_marks_reference_like_from_reference_anchor() -> None:
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {
            "block_id": "p9_b1",
            "zone": "backmatter_zone",
            "text": "[1] Example reference entry with authors and journal",
            "marker_signature": {"type": "reference_numeric_bracket", "number": 1},
            "span_signature": {"font_size_median": 8.5, "font_size_bucket": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        }
    ]
    anchors = {
        "reference_family_anchor": {
            "status": "ACCEPT",
            "family_name": "reference_family",
            "font_family_norm": "Times",
            "font_size_bucket": 8.5,
            "width_bucket": 250,
            "x_center_bucket": 250,
        }
    }

    partitioned = partition_zone_families(blocks, anchors)
    assert partitioned["p9_b1"]["style_family"] == "reference_like"


def test_partition_zone_families_surfaces_style_family_on_blocks_for_downstream_use() -> None:
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {
            "block_id": "p4_b1",
            "zone": "body_zone",
            "text": "Long narrative paragraph " * 6,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"},
            "layout_signature": {"width": 260},
        }
    ]

    partitioned = partition_zone_families(
        blocks,
        {"body_family_anchor": {"status": "ACCEPT", "family_name": "body_family"}},
    )

    assert partitioned["p4_b1"]["style_family"] == "body_like"
    assert blocks[0]["style_family"] == "body_like"
    assert blocks[0]["style_family_authority"] == "body_zone_with_anchor"


def test_partition_zone_families_does_not_mark_body_zone_style_match_as_reference_like() -> None:
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {
            "block_id": "p4_b1",
            "zone": "body_zone",
            "text": "Long narrative paragraph without citation list structure " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.5, "font_size_bucket": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        }
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family"},
        "reference_family_anchor": {
            "status": "ACCEPT",
            "family_name": "reference_family",
            "font_family_norm": "Times",
            "font_size_bucket": 8.5,
            "width_bucket": 250,
            "x_center_bucket": 250,
            "sample_pages": [9, 10],
        },
    }

    partitioned = partition_zone_families(blocks, anchors)

    assert partitioned["p4_b1"]["style_family"] == "body_like"
    assert partitioned["p4_b1"]["authority"] != "reference_family_anchor"


def test_partition_zone_families_does_not_mark_late_body_zone_style_match_as_reference_like() -> None:
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {
            "block_id": "p9_b1",
            "page": 9,
            "zone": "body_zone",
            "text": "Long late-page narrative paragraph without numbered reference structure " * 3,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.5, "font_size_bucket": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        }
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family"},
        "reference_family_anchor": {
            "status": "ACCEPT",
            "family_name": "reference_family",
            "font_family_norm": "Times",
            "font_size_bucket": 8.5,
            "width_bucket": 250,
            "x_center_bucket": 250,
            "sample_pages": [9, 10],
        },
    }

    partitioned = partition_zone_families(blocks, anchors)

    assert partitioned["p9_b1"]["style_family"] == "body_like"
    assert partitioned["p9_b1"]["authority"] != "reference_family_anchor"


def test_partition_zone_families_does_not_mark_backmatter_prose_style_match_as_reference_like() -> None:
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {
            "block_id": "p10_b1",
            "page": 10,
            "zone": "backmatter_zone",
            "text": "Appendix discussion prose continues the argument in full sentences without numbered entries, author-year formatting, or list-like citation structure. " * 2,
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 8.5, "font_size_bucket": 8.5, "font_family_norm": "Times"},
            "layout_signature": {"width": 250, "width_bucket": 250, "x_center": 240, "x_center_bucket": 250},
        }
    ]
    anchors = {
        "reference_family_anchor": {
            "status": "ACCEPT",
            "family_name": "reference_family",
            "font_family_norm": "Times",
            "font_size_bucket": 8.5,
            "width_bucket": 250,
            "x_center_bucket": 250,
            "sample_pages": [9, 10],
        }
    }

    partitioned = partition_zone_families(blocks, anchors)

    assert partitioned["p10_b1"]["style_family"] != "reference_like"
    assert partitioned["p10_b1"]["authority"] != "reference_family_anchor"

def test_table_roman_prefix_family_not_reference_like():
    from paperforge.worker.ocr_families import _classify_style_family

    block = {
        "text": "Table II. Mechanical properties...",
        "marker_signature": {"type": "citation_line"},
        "zone": "display_zone",
        "raw_label": "figure_title",
        "bbox": [100, 100, 800, 130],
    }
    family, authority = _classify_style_family(block, {}, {})
    assert family == "table_caption_like"
    assert authority == "table_marker"


def test_page_continuation_marker_is_not_reference():
    """Page continuation markers like "13 of 18", "13. of 18", "Page 13 of 18", "13/18" should NOT be classified as reference family."""
    from paperforge.worker.ocr_families import _is_reference_family_candidate

    markers = [
        {"text": "13 of 18", "bbox": [0, 0, 60, 10], "marker_signature": {"type": "reference_numeric_dot"}, "span_signature": {"font_size_median": 9.0}, "layout_signature": {"width": 60}},
        {"text": "13. of 18", "bbox": [0, 0, 65, 10], "marker_signature": {"type": "reference_numeric_dot"}, "span_signature": {"font_size_median": 9.0}, "layout_signature": {"width": 65}},
        {"text": "Page 13 of 18", "bbox": [0, 0, 90, 10], "marker_signature": {"type": "reference_numeric_dot"}, "span_signature": {"font_size_median": 9.0}, "layout_signature": {"width": 90}},
        {"text": "13/18", "bbox": [0, 0, 40, 10], "marker_signature": {"type": "reference_numeric_dot"}, "span_signature": {"font_size_median": 9.0}, "layout_signature": {"width": 40}},
    ]
    for marker in markers:
        assert not _is_reference_family_candidate(marker), f"'{marker['text']}' should not be reference family"


def test_real_reference_is_still_reference():
    """Real references like "13. Smith J, Wang L. Cartilage repair in 2018." should still be classified as reference family."""
    from paperforge.worker.ocr_families import _is_reference_family_candidate

    ref = {
        "text": "13. Smith J, Wang L. Cartilage repair in 2018. Journal of Orthopaedic Research.",
        "bbox": [100, 0, 500, 20],
        "marker_signature": {"type": "reference_numeric_dot"},
        "span_signature": {"font_size_median": 10.0},
        "layout_signature": {"width": 400},
    }
    assert _is_reference_family_candidate(ref), "Real reference should still be classified as reference family"
