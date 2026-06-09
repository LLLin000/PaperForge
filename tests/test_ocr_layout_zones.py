from __future__ import annotations


class FakeNode:
    def __init__(self, node_id, node_type, text="", bbox=(0, 0, 0, 0)):
        self.node_id = node_id
        self.node_type = node_type
        self.text = text
        self.bbox = bbox


def test_two_column_body_zone_orders_left_then_right_when_semantically_continuous() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones, order_body_spine

    nodes = [
        FakeNode("L1", "paragraph", "Left intro", (80, 100, 500, 160)),
        FakeNode("R1", "paragraph", "Right intro", (700, 110, 1120, 170)),
        FakeNode("L2", "paragraph", "Left methods", (80, 200, 500, 260)),
        FakeNode("R2", "paragraph", "Right methods", (700, 210, 1120, 270)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)
    ordered = order_body_spine(nodes, zones, mode="column_major")

    assert [node.node_id for node in ordered] == ["L1", "L2", "R1", "R2"]


def test_zone_detects_two_column_from_body_nodes() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones

    nodes = [
        FakeNode("L1", "paragraph", "a", (80, 100, 500, 160)),
        FakeNode("R1", "paragraph", "b", (700, 110, 1120, 170)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)

    assert len(zones) == 1
    assert zones[0].regime_type == "two_col"


def test_zone_detects_single_column() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones

    nodes = [
        FakeNode("L1", "paragraph", "a", (100, 80, 1100, 200)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)

    assert zones[0].regime_type == "single_col"


def test_default_mode_preserves_original_order() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones, order_body_spine

    nodes = [
        FakeNode("A", "paragraph", "first", (80, 100, 500, 160)),
        FakeNode("C", "paragraph", "third", (700, 200, 1120, 260)),
        FakeNode("B", "paragraph", "second", (80, 300, 500, 360)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)
    ordered = order_body_spine(nodes, zones, mode="prior_preserving")

    assert [node.node_id for node in ordered] == ["A", "C", "B"]


def test_infer_zones_emits_explicit_region_bus_artifact() -> None:
    from paperforge.worker.ocr_document import infer_zones

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
            "block_id": "p2_b1",
            "page": 2,
            "text": "Body text",
            "marker_signature": {"type": "none"},
            "span_signature": {"font_size_median": 9.5},
            "layout_signature": {"width": 260},
        },
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family", "sample_pages": [2]},
        "reference_family_anchor": {"status": "REJECT", "family_name": "reference_family", "item_count": 0},
    }

    zones = infer_zones(blocks, anchors)

    assert set(zones) >= {
        "frontmatter_main_zone",
        "frontmatter_side_zone",
        "body_zone",
        "reference_zone",
        "display_zone",
        "tail_nonref_hold_zone",
        "preproof_cover_zone",
    }
    assert zones["body_zone"]["status"] == "ACCEPT"
    assert "p2_b1" in zones["body_zone"]["block_ids"]


def test_analyze_document_structure_computes_region_bus_before_role_normalization_side_effects() -> None:
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
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
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
            "role": "reference_heading",
            "text": "References",
            "marker_signature": {"type": "canonical_section_name"},
            "span_signature": {"font_size_median": 10.0},
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

    doc = analyze_document_structure(blocks)

    assert doc.region_bus is not None
    assert "p7_b2" in doc.region_bus["tail_nonref_hold_zone"]["block_ids"]
    assert "p7_b2" not in doc.region_bus["body_zone"]["block_ids"]
    assert "p8_b2" in doc.region_bus["reference_zone"]["block_ids"]
    assert "p8_b3" in doc.region_bus["reference_zone"]["block_ids"]
