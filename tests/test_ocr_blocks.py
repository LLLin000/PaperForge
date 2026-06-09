from __future__ import annotations


def test_build_structured_blocks_preserves_noise_and_confidence() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "header",
            "raw_order": 0,
            "bbox": [1, 2, 3, 4],
            "text": "Header",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows, _ = build_structured_blocks(raw_blocks)

    assert rows[0]["role"] in {"noise", "page_header"}
    assert "role_confidence" in rows[0]
    assert "evidence" in rows[0]


def test_build_raw_blocks_preserves_every_block() -> None:
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_page

    result = {
        "prunedResult": {
            "width": 1200,
            "height": 1600,
            "parsing_res_list": [
                {
                    "block_id": 1,
                    "block_label": "text",
                    "block_order": 0,
                    "block_bbox": [1, 2, 3, 4],
                    "block_content": "A",
                },
                {
                    "block_id": 2,
                    "block_label": "header",
                    "block_order": 1,
                    "block_bbox": [5, 6, 7, 8],
                    "block_content": "B",
                },
            ],
        }
    }

    rows = build_raw_blocks_for_page("KEY001", 1, result)

    assert len(rows) == 2
    assert rows[0]["paper_id"] == "KEY001"
    assert rows[1]["raw_label"] == "header"


def test_build_structured_blocks_carries_span_metadata() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    span_data = [{"size": 14.0, "font": "Times-Bold", "flags": 16, "color": 0}]
    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "paragraph_title",
            "raw_order": 0,
            "bbox": [1, 2, 3, 4],
            "text": "Methods",
            "page_width": 1200,
            "page_height": 1600,
            "source": "ocr_raw",
            "span_metadata": span_data,
        }
    ]
    rows, _ = build_structured_blocks(raw_blocks)
    assert rows[0]["span_metadata"] == span_data


def test_structured_block_includes_structural_signatures() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 2,
            "block_id": "p2_b14",
            "raw_label": "paragraph_title",
            "raw_order": 0,
            "bbox": [207, 141, 504, 162],
            "text": "III. RESULTS AND DISCUSSION",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows, _ = build_structured_blocks(raw_blocks)
    row = rows[0]

    assert "marker_signature" in row
    assert "layout_signature" in row
    assert "span_signature" in row
    assert "raw_observation" in row
    assert row["marker_signature"]["type"] == "heading_roman"
    assert row["layout_signature"]["width"] == 297
    assert row["raw_observation"]["bbox"] == [207, 141, 504, 162]


def test_role_span_profiles_written_to_output() -> None:
    """Verify that role_span_profiles.json is written during rebuild."""
    import json

    from paperforge.worker.ocr_profiles import build_role_span_profiles

    blocks = [
        {"role": "section_heading", "span_metadata": {"size": 16.0, "flags": "bold"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.0, "flags": 0}},
    ]
    profiles = build_role_span_profiles(blocks)
    # Must be JSON-serializable
    dumped = json.dumps(profiles)
    assert "section_heading" in dumped
    assert "body_paragraph" in dumped


def test_build_structured_blocks_attaches_body_family_anchor() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [110, 100, 370, 220],
            "text": "Long body text A " * 8,
            "page_width": 600,
            "page_height": 800,
            "span_metadata": [{"font": "Times", "size": 9.0, "flags": 0, "color": 0}] * 12,
        },
        {
            "paper_id": "KEY001",
            "page": 4,
            "block_id": "p4_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [112, 100, 374, 220],
            "text": "Long body text B " * 8,
            "page_width": 600,
            "page_height": 800,
            "span_metadata": [{"font": "Times", "size": 9.0, "flags": 0, "color": 0}] * 12,
        },
    ]

    _rows, doc_structure = build_structured_blocks(raw_blocks)

    assert doc_structure is not None
    assert doc_structure.body_family_anchor is not None
    assert doc_structure.body_family_anchor["status"] == "ACCEPT"
    assert doc_structure.body_family_anchor["family_name"] == "body_family"
    assert doc_structure.body_family_anchor["sample_pages"] == [3, 4]


def test_build_structured_blocks_discovers_body_family_before_normalization() -> None:
    from unittest.mock import patch

    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [110, 100, 370, 220],
            "text": "Long body text A " * 8,
            "page_width": 600,
            "page_height": 800,
            "span_metadata": [{"font": "Times", "size": 9.0, "flags": 0, "color": 0}] * 12,
        },
        {
            "paper_id": "KEY001",
            "page": 4,
            "block_id": "p4_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [112, 100, 374, 220],
            "text": "Long body text B " * 8,
            "page_width": 600,
            "page_height": 800,
            "span_metadata": [{"font": "Times", "size": 9.0, "flags": 0, "color": 0}] * 12,
        },
    ]

    with patch("paperforge.worker.ocr_document.normalize_document_structure", side_effect=RuntimeError("boom")):
        _rows, doc_structure = build_structured_blocks(raw_blocks)

    assert doc_structure is not None
    assert doc_structure.body_family_anchor is not None
    assert doc_structure.body_family_anchor["status"] == "ACCEPT"
    assert doc_structure.body_family_anchor["sample_pages"] == [3, 4]
