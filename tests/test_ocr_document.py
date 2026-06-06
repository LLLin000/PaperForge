from __future__ import annotations


def test_analyze_document_structure_flat_backmatter() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, PagePosition, analyze_document_structure

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
        {"page": 1, "role": "body_paragraph", "role_confidence": 0.7, "text": "Intro body paragraph with enough text to establish a profile.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 2, "role": "body_paragraph", "role_confidence": 0.7, "text": "Methods section describing the experimental setup in full detail.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 3, "role": "frontmatter_noise", "role_confidence": 0.6, "text": "This block was misclassified as frontmatter noise but is actually body text.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 4, "role": "reference_heading", "role_confidence": 0.9, "text": "References"},
        {"page": 4, "role": "reference_item", "role_confidence": 0.7, "text": "[1] Author A, Journal, 2025"},
    ]

    role_profiles = {
        "body_paragraph": {"block_count": 2, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
                          "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
                          "italic_ratio": 0.0, "font_families": []},
        "frontmatter_noise": {"block_count": 1, "mean_size": 8.0, "max_size": 8.5, "min_size": 7.5,
                            "dispersion": 0.05, "quality": "weak", "bold_ratio": 0.0,
                            "italic_ratio": 0.0, "font_families": []},
    }

    ds = DocumentStructure(body_end_page=3)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    rescued = next(b for b in result if b["text"].startswith("This block was misclassified"))
    assert rescued["role"] == "body_paragraph", (
        f"Expected body_paragraph, got {rescued['role']}"
    )


def test_rescue_body_paragraph_to_reference_item() -> None:
    """body_paragraph with ref-like font in references section → reference_item."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        PagePosition,
        rescue_roles_with_document_context,
    )

    blocks = [
        {"page": 1, "role": "body_paragraph", "role_confidence": 0.7, "text": "Main body paragraph that is long enough for context.",
         "span_metadata": {"size": 10.5, "flags": "normal"}},
        {"page": 5, "role": "reference_heading", "role_confidence": 0.9, "text": "References"},
        {"page": 5, "role": "body_paragraph", "role_confidence": 0.5, "text": "1. Smith J, Johnson K. A study on something. Journal, 2025.",
         "span_metadata": {"size": 9.0, "flags": "normal"}},
    ]

    role_profiles = {
        "body_paragraph": {"block_count": 1, "mean_size": 10.5, "max_size": 10.5, "min_size": 10.5,
                          "dispersion": 0.0, "quality": "strong", "bold_ratio": 0.0,
                          "italic_ratio": 0.0, "font_families": []},
        "reference_item": {"block_count": 0, "mean_size": 9.0, "max_size": 9.0, "min_size": 9.0,
                          "dispersion": 0.0, "quality": "weak", "bold_ratio": 0.0,
                          "italic_ratio": 0.0, "font_families": []},
    }

    ds = DocumentStructure(body_end_page=4, references_start=PagePosition(page=5, y=0))
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    promoted = next(b for b in result if b["text"].startswith("1. Smith"))
    assert promoted["role"] == "reference_item", (
        f"Expected reference_item, got {promoted['role']}"
    )


def test_rescue_weak_heading_demoted_to_body() -> None:
    """Weak heading (confidence < 0.6) with body-like font → body_paragraph."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )

    blocks = [
        {"page": 1, "role": "body_paragraph", "role_confidence": 0.7, "text": "Some intro body text that provides a long enough context for profiling.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 2, "role": "body_paragraph", "role_confidence": 0.7, "text": "More body text to strengthen the body profile for better font matching.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 2, "role": "section_heading", "role_confidence": 0.5, "text": "Methods",
         "span_metadata": {"size": 10, "flags": "normal"}},
    ]

    role_profiles = {
        "body_paragraph": {"block_count": 2, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
                          "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
                          "italic_ratio": 0.0, "font_families": []},
        "section_heading": {"block_count": 0, "mean_size": 12.0, "max_size": 12.0, "min_size": 12.0,
                          "dispersion": 0.0, "quality": "no_data", "bold_ratio": 1.0,
                          "italic_ratio": 0.0, "font_families": []},
    }

    ds = DocumentStructure(body_end_page=2)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    demoted = next(b for b in result if b["text"] == "Methods")
    assert demoted["role"] == "body_paragraph", (
        f"Expected body_paragraph, got {demoted['role']}"
    )


def test_rescue_strong_numbered_heading_not_demoted() -> None:
    """Strong numbered heading (e.g. '5.1 Results') should NOT be demoted."""
    from paperforge.worker.ocr_document import (
        DocumentStructure,
        rescue_roles_with_document_context,
    )

    blocks = [
        {"page": 1, "role": "body_paragraph", "role_confidence": 0.7, "text": "Body paragraph one with enough text to contribute to a font profile.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 2, "role": "section_heading", "role_confidence": 0.5, "text": "5.1 Results",
         "span_metadata": {"size": 10, "flags": "normal"}},
    ]

    role_profiles = {
        "body_paragraph": {"block_count": 1, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
                          "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
                          "italic_ratio": 0.0, "font_families": []},
    }

    ds = DocumentStructure(body_end_page=2)
    result = rescue_roles_with_document_context(blocks, role_profiles, ds)

    heading = next(b for b in result if b["text"] == "5.1 Results")
    assert heading["role"] == "section_heading", (
        f"Expected section_heading preserved, got {heading['role']}"
    )


def test_rescue_no_document_structure_derived() -> None:
    """rescue_roles_with_document_context should derive structure when not provided."""
    from paperforge.worker.ocr_document import rescue_roles_with_document_context

    blocks = [
        {"page": 1, "role": "body_paragraph", "role_confidence": 0.7, "text": "Body text that is long enough for establishing a font profile here.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 2, "role": "body_paragraph", "role_confidence": 0.7, "text": "More body text here to help build a solid body paragraph profile.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 2, "role": "frontmatter_noise", "role_confidence": 0.6, "text": "Misclassified text block that should be rescued to body paragraph.",
         "span_metadata": {"size": 10, "flags": "normal"}},
        {"page": 3, "role": "reference_heading", "role_confidence": 0.9, "text": "References"},
        {"page": 3, "role": "reference_item", "role_confidence": 0.7, "text": "[1] Author A, Journal, 2025"},
    ]

    role_profiles = {
        "body_paragraph": {"block_count": 2, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
                          "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
                          "italic_ratio": 0.0, "font_families": []},
        "frontmatter_noise": {"block_count": 1, "mean_size": 8.0, "max_size": 8.5, "min_size": 7.5,
                            "dispersion": 0.05, "quality": "weak", "bold_ratio": 0.0,
                            "italic_ratio": 0.0, "font_families": []},
    }

    result = rescue_roles_with_document_context(blocks, role_profiles)

    rescued = next(b for b in result if b["text"].startswith("Misclassified"))
    assert rescued["role"] == "body_paragraph", (
        f"Expected body_paragraph, got {rescued['role']}"
    )


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
    assert 2 in indices, f"Expected index 2 in {indices}"
    assert 3 in indices, f"Expected index 3 in {indices}"


def test_non_body_insert_not_backfilled_to_body() -> None:
    """Verify that non_body_insert blocks are not rescued to body_paragraph."""
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "TEST001", "page": 1, "block_id": "p1_b1",
            "raw_label": "text", "raw_order": 0,
            "bbox": [50, 200, 300, 240],
            "text": "The author biography section provides a brief overview of the professional background of each contributor",
            "page_width": 1200, "page_height": 1600, "source": "ocr_raw",
        },
        {
            "paper_id": "TEST001", "page": 1, "block_id": "p1_b2",
            "raw_label": "text", "raw_order": 1,
            "bbox": [50, 280, 310, 320],
            "text": "Biographical information about each author is listed in the supplementary materials for this manuscript",
            "page_width": 1200, "page_height": 1600, "source": "ocr_raw",
        },
        # A wide body paragraph
        {
            "paper_id": "TEST001", "page": 1, "block_id": "p1_b3",
            "raw_label": "text", "raw_order": 2,
            "bbox": [100, 600, 800, 640],
            "text": "The following experimental results demonstrate the effect of the treatment on cell migration and proliferation assays performed in triplicate",
            "page_width": 1200, "page_height": 1600, "source": "ocr_raw",
        },
    ]
    rows = build_structured_blocks(raw_blocks)
    non_body = [r for r in rows if r.get("role") == "non_body_insert"]
    assert len(non_body) == 2, f"Expected 2 non_body_insert, got {len(non_body)}"
    for r in non_body:
        assert r.get("render_default") is False, f"non_body_insert should not render: {r}"


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
