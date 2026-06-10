from __future__ import annotations


def test_block_signature_extraction_preserves_observation_without_final_role():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p2_b14",
        "page": 2,
        "raw_label": "paragraph_title",
        "text": "III. RESULTS AND DISCUSSION",
        "bbox": [207, 141, 504, 162],
        "span_metadata": {"font_size": 9.35, "bold": False},
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "heading_roman"
    assert result["marker_signature"]["raw_marker"] == "III"
    assert result["marker_signature"]["kind"] == "heading"
    assert result["layout_signature"]["width"] == 297
    assert result["raw_label"] == "paragraph_title"
    assert result["bbox"] == [207, 141, 504, 162]
    assert result["raw_observation"]["page_width"] == 1200
    assert result["role"] == "unassigned"


def test_block_signature_numbered_heading():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p3_b1",
        "page": 3,
        "raw_label": "paragraph_title",
        "text": "2.3 Statistical Analysis",
        "bbox": [100, 500, 800, 530],
        "span_metadata": {"size": 12.0, "flags": "bold"},
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "heading_numbered"
    assert result["marker_signature"]["number"] == "2.3"
    assert result["role"] == "unassigned"


def test_block_signature_figure_prefix():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p5_b3",
        "page": 5,
        "raw_label": "figure_title",
        "text": "Figure 3. Expression levels of target genes.",
        "bbox": [200, 800, 1000, 830],
        "span_metadata": {"size": 10.0, "flags": "italic"},
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "figure_number"
    assert result["marker_signature"]["kind"] == "figure"
    assert result["marker_signature"]["number"] == 3
    assert result["role"] == "unassigned"


def test_block_signature_table_prefix():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p6_b1",
        "page": 6,
        "raw_label": "text",
        "text": "Table 2. Patient demographics.",
        "bbox": [150, 200, 1050, 230],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "table_number"
    assert result["marker_signature"]["kind"] == "table"
    assert result["marker_signature"]["number"] == 2
    assert result["role"] == "unassigned"


def test_block_signature_reference_numeric_bracket_payload():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p8_b2",
        "page": 8,
        "raw_label": "text",
        "text": "[12] Example reference entry.",
        "bbox": [100, 120, 500, 150],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)
    marker = result["marker_signature"]

    assert marker["type"] == "reference_numeric_bracket"
    assert marker["kind"] == "reference"
    assert marker["number"] == 12
    assert marker["raw_marker"] == "[12]"


def test_block_signature_reference_numeric_parenthesis_payload():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p8_b3",
        "page": 8,
        "raw_label": "text",
        "text": "(7) Another reference entry.",
        "bbox": [100, 160, 500, 190],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)
    marker = result["marker_signature"]

    assert marker["type"] == "reference_numeric_parenthesis"
    assert marker["kind"] == "reference"
    assert marker["number"] == 7


def test_block_signature_body_text():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p4_b5",
        "page": 4,
        "raw_label": "text",
        "text": "The results demonstrate a significant increase in expression.",
        "bbox": [100, 300, 1100, 330],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "none"
    assert result["marker_signature"]["kind"] == "generic_text"
    assert result["role"] == "unassigned"


def test_block_signature_layout_properties():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p1_b1",
        "page": 1,
        "raw_label": "text",
        "text": "Some centered text.",
        "bbox": [400, 100, 800, 130],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    layout = result["layout_signature"]
    assert layout["width"] == 400
    assert layout["height"] == 30
    assert layout["left"] == 400
    assert layout["top"] == 100
    assert layout["right"] == 800
    assert layout["bottom"] == 130
    assert layout["x_center"] == 600
    assert layout["width_bucket"] == 400
    assert layout["x_center_bucket"] == 600
    assert layout["x_ratio"] == 0.5
    assert layout["width_ratio"] == 0.3333


def test_block_signature_span_signature():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p1_b1",
        "page": 1,
        "raw_label": "paragraph_title",
        "text": "Introduction",
        "bbox": [100, 200, 500, 230],
        "span_metadata": {"size": 14.0, "flags": "bold", "font": "Times-Bold"},
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    span_sig = result["span_signature"]
    assert span_sig["font_size"] == 14.0
    assert span_sig["font_size_median"] == 14.0
    assert span_sig["font_size_bucket"] == 14.0
    assert span_sig["font_family_norm"] == "Times-Bold"
    assert span_sig["bold"] is True
    assert span_sig["italic"] is False
    assert span_sig["span_count"] == 1


def test_block_signature_list_span_metadata_keeps_mean_size_and_family():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p2_b1",
        "page": 2,
        "raw_label": "text",
        "text": "This is body text with two spans.",
        "bbox": [100, 100, 600, 140],
        "span_metadata": [
            {"size": 10.0, "font": "Times-Roman", "flags": 0},
            {"size": 10.5, "font": "Times-Roman", "flags": 0},
        ],
    }

    result = build_block_signatures(block)
    span_sig = result["span_signature"]

    assert span_sig["font_size"] == 10.25
    assert span_sig["font_size_median"] == 10.25
    assert span_sig["font_size_bucket"] == 10.0
    assert span_sig["font_family_norm"] == "Times-Roman"
    assert span_sig["span_count"] == 2


def test_old_style_numbered_reference_is_typed_as_reference_numeric_dot():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p10_b1",
        "page": 10,
        "raw_label": "text",
        "text": "1 Smith J, Jones B. Title of paper. Journal. 2020",
        "bbox": [100, 120, 500, 150],
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)
    marker = result["marker_signature"]

    assert marker["type"] == "reference_numeric_dot"
    assert marker["kind"] == "reference"
    assert marker["number"] == 1


def test_heading_numbered_still_works_for_real_headings():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p3_b1",
        "page": 3,
        "raw_label": "paragraph_title",
        "text": "2.3 Statistical Analysis",
        "bbox": [100, 500, 800, 530],
        "span_metadata": {"size": 12.0, "flags": "bold"},
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "heading_numbered"
    assert result["marker_signature"]["number"] == "2.3"


def test_block_signature_missing_bbox_returns_zero_layout_signature():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p9_b1",
        "page": 9,
        "raw_label": "text",
        "text": "No bbox block",
    }

    result = build_block_signatures(block)
    layout = result["layout_signature"]

    assert layout["width"] == 0
    assert layout["x_center"] == 0
    assert layout["width_bucket"] == 0
    assert layout["x_ratio"] == 0.0
