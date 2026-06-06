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
