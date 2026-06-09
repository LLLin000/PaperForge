"""Tests for OCR family anchor discovery."""

from __future__ import annotations


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
