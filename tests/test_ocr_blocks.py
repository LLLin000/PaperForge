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


def test_build_structured_blocks_preserves_seed_without_final_role(tmp_path=None) -> None:
    import tempfile
    from pathlib import Path

    from paperforge.worker.ocr_blocks import build_structured_blocks

    out_dir = tmp_path or Path(tempfile.mkdtemp())
    raw_blocks = [
        {
            "paper_id": "P",
            "page": 1,
            "block_id": "b1",
            "raw_label": "abstract",
            "raw_order": 1,
            "bbox": [90, 100, 900, 150],
            "text": "This label is only a seed.",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows, _doc = build_structured_blocks(raw_blocks, structure_output_dir=out_dir)

    # seed_role is preserved even though normalize_document_structure resolves role
    assert rows[0]["seed_role"]
    assert rows[0]["seed_role"] in {"abstract_body", "abstract_heading"}
    assert "seed_confidence" in rows[0]
    assert "seed_evidence" in rows[0]
    # role is resolved (not "unassigned") because build_structured_blocks calls normalize
    assert rows[0]["role"] != "unassigned"


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


def test_build_structured_blocks_exposes_source_frontmatter_anchors() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "doc_title",
            "raw_order": 0,
            "bbox": [50, 100, 900, 150],
            "text": "Correct Research Title That Is Long Enough",
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b2",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [50, 170, 700, 210],
            "text": "Alice Smith, Bob Jones",
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    _rows, doc_structure = build_structured_blocks(
        raw_blocks,
        source_metadata={
            "title": "Correct Research Title That Is Long Enough",
            "authors": ["Alice Smith", "Bob Jones"],
        },
    )

    anchors = getattr(doc_structure, "source_frontmatter_anchors", {})
    assert anchors["title_source_anchor"]["status"] == "ACCEPT"
    assert anchors["authors_source_anchor"]["status"] == "ACCEPT"


def test_nonpreproof_cover_false_when_page1_has_abstract():
    """page 1 with abstract but no cover marker -> NOT cover."""
    rows = [
        {"page": 1, "seed_role": "paper_title", "text": "Some Title"},
        {"page": 1, "seed_role": "authors", "text": "John Doe"},
        {"page": 1, "seed_role": "abstract_body",
         "text": "This abstract describes the study purpose, methods, results, and conclusions."},
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Keywords: something"},
        {"page": 2, "seed_role": "section_heading", "text": "1. Introduction"},
        {"page": 2, "seed_role": "body_paragraph",
         "text": "Real body text starts here with many words. It has enough length to pass the threshold."},
    ]
    from paperforge.worker.ocr_blocks import _has_nonpreproof_cover_page_one
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_false_when_page1_has_section_heading():
    """page 1 with section heading -> NOT cover even with marker."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Just Accepted"},
        {"page": 1, "seed_role": "paper_title", "text": "Some Title"},
        {"page": 1, "seed_role": "section_heading", "text": "1. Introduction"},
    ]
    from paperforge.worker.ocr_blocks import _has_nonpreproof_cover_page_one
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_true_with_just_accepted_marker():
    """ACS 'Just Accepted' marker + no body -> cover page."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Just Accepted"},
        {"page": 1, "seed_role": "frontmatter_noise",
         "text": "This is a PDF file of an unedited manuscript that has been accepted for publication."},
        {"page": 1, "seed_role": "frontmatter_noise",
         "text": "American Chemical Society"},
        {"page": 2, "seed_role": "paper_title", "text": "Some Title"},
        {"page": 2, "seed_role": "body_paragraph",
         "text": "Real body text starts here with many words to pass the threshold requirement. More words here."},
    ]
    from paperforge.worker.ocr_blocks import _has_nonpreproof_cover_page_one
    assert _has_nonpreproof_cover_page_one(rows) is True


def test_nonpreproof_cover_false_when_no_cover_marker():
    """page 1 with no cover marker text but no body -> NOT cover (too risky)."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Copyright 2023 Publisher"},
        {"page": 2, "seed_role": "section_heading", "text": "Introduction"},
    ]
    from paperforge.worker.ocr_blocks import _has_nonpreproof_cover_page_one
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_false_for_available_online_only():
    """'Available online' alone must NOT trigger cover drop."""
    rows = [
        {"page": 1, "seed_role": "frontmatter_noise", "text": "Available online 12 March 2024"},
        {"page": 1, "seed_role": "abstract_body",
         "text": "This abstract describes the study purpose, methods, and results."},
        {"page": 2, "seed_role": "section_heading", "text": "1. Introduction"},
    ]
    from paperforge.worker.ocr_blocks import _has_nonpreproof_cover_page_one
    assert _has_nonpreproof_cover_page_one(rows) is False


def test_nonpreproof_cover_wired_through_build_structured_blocks(tmp_path):
    """build_structured_blocks drops page 1 for non-preproof cover."""
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {"paper_id": "TEST", "page": 1, "block_id": 0, "raw_label": "text",
         "text": "Just Accepted", "bbox": [0, 0, 100, 20], "page_width": 1200, "page_height": 1600,
         "raw_order": 0},
        {"paper_id": "TEST", "page": 1, "block_id": 1, "raw_label": "text",
         "text": "This is a PDF file of an unedited manuscript that has been accepted for publication.",
         "bbox": [0, 30, 500, 60], "page_width": 1200, "page_height": 1600, "raw_order": 1},
        {"paper_id": "TEST", "page": 2, "block_id": 2, "raw_label": "doc_title",
         "text": "Real Title", "bbox": [0, 100, 500, 150], "page_width": 1200, "page_height": 1600,
         "raw_order": 2},
        {"paper_id": "TEST", "page": 2, "block_id": 3, "raw_label": "text",
         "text": "Real body text starts here with enough words in this paragraph to pass the threshold check correctly.",
         "bbox": [0, 200, 500, 250], "page_width": 1200, "page_height": 1600, "raw_order": 3},
    ]

    rows, doc = build_structured_blocks(raw_blocks, structure_output_dir=tmp_path)
    assert all(r["page"] != 1 for r in rows), "page 1 should be dropped"
    assert any("page_1_cover_dropped_upstream:cover_marker_no_body" in (r.get("evidence") or [])
               for r in rows), "evidence should mark cover drop"
