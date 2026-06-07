from __future__ import annotations


def test_structured_block_has_render_default_for_body() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [100, 200, 900, 300],
            "text": "This is a body paragraph with enough text to be meaningful and avoid the short-text threshold.",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows, _ = build_structured_blocks(raw_blocks)
    assert rows[0]["role"] == "body_paragraph"
    assert rows[0]["render_default"] is True
    assert rows[0]["index_default"] is True


def test_structured_block_marks_noise_as_not_renderable() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "header",
            "raw_order": 0,
            "bbox": [1, 2, 100, 20],
            "text": "Running head: SOME JOURNAL",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows, _ = build_structured_blocks(raw_blocks)
    assert rows[0]["role"] in {"noise", "page_header"}
    assert rows[0]["render_default"] is False


def test_heading_role_is_not_figure_text() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "5.1 Bone",
        "block_bbox": [606, 732, 709, 759],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1191, page_height=1684)

    assert role.role in {"section_heading", "subsection_heading"}


def test_figure_caption_role_beats_body_paragraph() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "Figure 4 RT-qPCR results. Temporal changes in messenger RNA...",
        "block_bbox": [373, 1101, 1143, 1258],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role == "figure_caption"


def test_paragraph_title_is_heading_prior() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "5 In vitro PEMF studies",
        "block_bbox": [94, 1328, 387, 1356],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1191, page_height=1684)

    assert role.role in {"section_heading", "subsection_heading"}
    assert role.confidence >= 0.7


def test_paragraph_title_with_trailing_dot_numbering_is_strong_heading() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "8. Conclusion and outlook",
        "block_bbox": [94, 1328, 520, 1356],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1191, page_height=1684)

    assert role.role == "section_heading"
    assert role.confidence >= 0.7


def test_figure_title_is_caption_prior() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "figure_title",
        "block_content": "Figure 2. Representative pathology records.",
        "block_bbox": [300, 1180, 980, 1250],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role in {"figure_caption", "figure_caption_candidate"}
    assert role.confidence >= 0.8


def test_unknown_structural_for_unrecognized() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "xyz",
        "block_bbox": [100, 100, 200, 120],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role in {"body_paragraph", "unknown_structural"}
    assert role.confidence < 0.8


def test_stabilize_role_classifies_paper_title() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    assignment = assign_block_role(
        block={
            "block_label": "paragraph_title",
            "block_content": "Test Paper About Science",
            "page": 1,
            "block_bbox": [100, 50, 900, 100],
        },
        page_blocks=[],
        page_height=1000,
    )

    assert assignment.role == "paper_title"


def test_stabilize_abstract_heading_is_not_body() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    assignment = assign_block_role(
        block={"block_label": "paragraph_title", "block_content": "Abstract"},
        page_blocks=[],
    )

    assert assignment.role == "abstract_heading"


def test_stabilize_frontmatter_noise_not_section_heading() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    for noise in ("OPEN ACCESS", "CITATION", "COPYRIGHT", "KEYWORDS", "EDITED BY", "REVIEWED BY"):
        assignment = assign_block_role(
            block={"block_label": "paragraph_title", "block_content": noise},
            page_blocks=[],
        )
        assert assignment.role not in ("section_heading", "subsection_heading"), f"{noise} should not be a heading"


def test_backmatter_heading_not_paper_title() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    for text in ["Generative AI statement", "Acknowledgments", "Funding", "Conflict of interest"]:
        block = {
            "block_label": "paragraph_title",
            "block_content": text,
            "page": 1,
            "block_bbox": [100, 50, 500, 80],
        }
        assignment = assign_block_role(block, page_blocks=[], page_height=1000)
        assert assignment.role != "paper_title", f"'{text}' should not be paper_title"


def test_backmatter_heading_gets_backmatter_role() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    backmatter_phrases = [
        "Author contributions",
        "Funding",
        "Acknowledgments",
        "Conflict of interest",
        "Generative AI statement",
    ]
    for text in backmatter_phrases:
        block = {
            "block_label": "paragraph_title",
            "block_content": text,
            "page": 20,
            "block_bbox": [100, 600, 500, 630],
        }
        assignment = assign_block_role(block, page_blocks=[], page_height=1000)
        assert assignment.role.startswith("backmatter_"), f"'{text}' should get backmatter_ role, got {assignment.role}"


def test_references_heading_gets_reference_role() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    assignment = assign_block_role(
        block={"block_label": "paragraph_title", "block_content": "References"},
        page_blocks=[],
    )
    assert assignment.role == "reference_heading", (
        f"paragraph_title 'References' should be reference_heading, got {assignment.role}"
    )

    assignment_text = assign_block_role(
        block={"block_label": "text", "block_content": "References"},
        page_blocks=[],
    )
    assert assignment_text.role == "reference_heading", (
        f"text 'References' should be reference_heading, got {assignment_text.role}"
    )


def test_body_with_noise_phrase_below_backmatter_heading() -> None:
    """Text block with 'supplementary material' under backmatter heading -> backmatter_body, not frontmatter_noise."""
    from paperforge.worker.ocr_roles import assign_block_role

    page_blocks = [
        {
            "block_label": "paragraph_title",
            "block_content": "Supplementary material",
            "block_bbox": [604, 536, 909, 567],
            "page": 22,
        },
        {
            "block_label": "text",
            "block_content": "The Supplementary Material for this article can be found online.",
            "block_bbox": [604, 590, 1096, 662],
            "page": 22,
        },
    ]
    assignment = assign_block_role(
        page_blocks[1],
        page_blocks=page_blocks,
        page_width=1191,
    )
    assert assignment.role == "body_paragraph", (
        f"Role layer should stay conservative and leave tail ownership to render, got {assignment.role}"
    )


def test_style_aware_unnumbered_heading_detection() -> None:
    """Unnumbered headings with distinct visual style are detected as headings.

    The current assign_block_role ignores span_metadata (size, flags),
    relying only on block_label and text patterns.  Two text blocks with
    heading-like style (different sizes, bold) should both be detected as
    headings, and a truly ordinary body block should not be promoted.
    """
    from paperforge.worker.ocr_roles import assign_block_role

    big_heading = {
        "block_label": "text",
        "block_content": "Clinical Outcomes",
        "span_metadata": {"size": 16, "flags": "bold"},
        "block_bbox": [96, 300, 500, 330],
        "page": 5,
    }
    sub_heading = {
        "block_label": "text",
        "block_content": "Histological Analysis",
        "span_metadata": {"size": 14, "flags": "bold"},
        "block_bbox": [96, 450, 500, 480],
        "page": 5,
    }
    body_block = {
        "block_label": "text",
        "block_content": "Immunohistochemical staining revealed significant differences between the treatment and control groups across all time points examined.",
        "span_metadata": {"size": 10, "flags": "normal"},
        "block_bbox": [96, 500, 1090, 620],
        "page": 5,
    }

    page_blocks = [big_heading, sub_heading, body_block]

    big_role = assign_block_role(
        big_heading,
        page_blocks=page_blocks,
        page_height=1000,
    )
    sub_role = assign_block_role(
        sub_heading,
        page_blocks=page_blocks,
        page_height=1000,
    )
    body_role = assign_block_role(
        body_block,
        page_blocks=page_blocks,
        page_height=1000,
    )

    heading_roles = {"section_heading", "subsection_heading", "backmatter_heading"}
    assert big_role.role in heading_roles, (
        f"Big heading should be detected as heading, got {big_role.role}"
    )
    assert sub_role.role in heading_roles, (
        f"Sub heading should be detected as heading, got {sub_role.role}"
    )
    assert body_role.role not in {"section_heading", "backmatter_heading", "subsection_heading"}, (
        f"Body should not be promoted to heading, got {body_role.role}"
    )


def test_backmatter_body_cross_column_ownership() -> None:
    """Body in right column attaches to nearest right-column heading, not left-column one."""
    from paperforge.worker.ocr_roles import assign_block_role

    page_blocks = [
        {
            "block_label": "paragraph_title",
            "block_content": "Conflict of interest",
            "block_bbox": [94, 536, 338, 565],
            "page": 22,
        },
        {
            "block_label": "paragraph_title",
            "block_content": "Supplementary material",
            "block_bbox": [604, 536, 909, 567],
            "page": 22,
        },
        {
            "block_label": "text",
            "block_content": "The Supplementary Material for this article can be found online.",
            "block_bbox": [604, 590, 1096, 662],
            "page": 22,
        },
    ]
    assignment = assign_block_role(
        page_blocks[2],
        page_blocks=page_blocks,
        page_width=1191,
    )
    assert assignment.role == "body_paragraph", (
        f"Role layer should stay conservative and leave tail ownership to render, got {assignment.role}"
    )


def test_heading_level_from_profile_match() -> None:
    """After profile aggregation, headings should be classified by
    profile match, not hardcoded font size."""
    pass  # Placeholder — will be updated after refactor


def test_body_citation_not_authors() -> None:
    from paperforge.worker.ocr_roles import assign_block_role
    block = {
        "block_label": "text",
        "block_content": "In Section 5, the focus is on ES based bioelectronics $^{8,49}$",
        "block_bbox": [100, 500, 800, 540],
        "page": 3,
    }
    result = assign_block_role(block, page_blocks=[block], page_width=1200, page_height=1600)
    assert result.role == "body_paragraph", f"Expected body_paragraph, got {result.role}"
    assert result.confidence >= 0.5


def test_frontmatter_author_zone_still_works() -> None:
    from paperforge.worker.ocr_roles import assign_block_role
    block = {
        "block_label": "text",
        "block_content": "Alice Smith, Bob Jones, Charlie Brown",
        "block_bbox": [100, 300, 800, 330],
        "page": 1,
    }
    result = assign_block_role(block, page_blocks=[block], page_width=1200, page_height=1600)
    assert result.role == "authors", f"Expected authors, got {result.role}"


def test_figure_caption_candidate_for_narrative_body() -> None:
    """Fig. 26c addresses ... with body-style text → figure_caption_candidate."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "Fig. 26c addresses the signaling pathway in detail and demonstrates the mechanism of action for the compound.",
        "block_bbox": [100, 500, 900, 550],
        "page": 3,
    }

    role = assign_block_role(block, page_blocks=[block], page_width=1200, page_height=1600)

    assert role.role == "figure_caption_candidate", (
        f"Narrative body text with Fig prefix should be candidate, got {role.role}"
    )


def test_backmatter_heading_candidate_on_late_page() -> None:
    """Funding on page 10 → backmatter_heading_candidate."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "Funding",
        "block_bbox": [100, 600, 500, 630],
        "page": 10,
    }

    role = assign_block_role(block, page_blocks=[], page_height=1000)

    assert role.role == "backmatter_heading_candidate", (
        f"Funding on page 10 should be backmatter_heading_candidate, got {role.role}"
    )


def test_figure_title_label_becomes_candidate() -> None:
    """raw label figure_title with Fig. 2 test → figure_caption_candidate."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "figure_title",
        "block_content": "Fig. 2 test",
        "block_bbox": [300, 1100, 700, 1130],
        "page": 3,
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role == "figure_caption_candidate", (
        f"figure_title label should produce candidate, got {role.role}"
    )


def test_formal_figure_caption_still_direct() -> None:
    """Figure 3. Expression of ... near media → figure_caption (unchanged)."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "Figure 3. Expression of target proteins",
        "block_bbox": [200, 1300, 900, 1330],
        "page": 3,
    }
    media_block = {
        "block_label": "image",
        "block_content": "",
        "block_bbox": [200, 900, 900, 1250],
        "page": 3,
    }

    page_blocks = [block, media_block]

    role = assign_block_role(block, page_blocks=page_blocks, page_width=1200, page_height=1600)

    assert role.role == "figure_caption", (
        f"Formal figure caption near media should be figure_caption, got {role.role}"
    )


def test_weak_backmatter_boundary_signal_emits_candidate():
    """A paragraph with backmatter boundary text but no bold span_metadata
    should emit backmatter_boundary_candidate, not backmatter_boundary_heading."""
    from paperforge.worker.ocr_roles import assign_block_role
    block = {
        "block_label": "paragraph_title",
        "block_content": "ADDITIONAL INFORMATION",
        "block_bbox": [100, 1200, 500, 1240],
        "page": 8,
    }
    page_blocks = [block] + [
        {
            "block_label": "text",
            "block_content": f"Some body text {i}",
            "block_bbox": [100, 200 + i * 100, 500, 260 + i * 100],
            "page": 8,
        }
        for i in range(5)
    ]
    result = assign_block_role(
        block, page_blocks=page_blocks, page_width=600, page_height=1600
    )
    assert result.role == "backmatter_boundary_candidate", (
        f"Expected backmatter_boundary_candidate, got {result.role}"
    )


def test_author_byline_not_section_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    # Author byline with & on page 1
    block = {"block_label": "paragraph_title", "block_content": "John Smith & Jane Doe", "block_bbox": [100, 50, 500, 80], "page": 1}
    page_blocks = [block,
        {"block_label": "text", "block_content": "Some frontmatter", "block_bbox": [100, 100, 500, 130], "page": 1},
        {"block_label": "text", "block_content": "Some abstract content", "block_bbox": [100, 200, 500, 230], "page": 1},
    ]
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=800)
    assert result.role not in ("section_heading", "subsection_heading", "sub_subsection_heading"), (
        f"Author byline got heading role: {result.role}"
    )


def test_correspondence_marker_not_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    block = {"block_label": "paragraph_title", "block_content": "*Correspondence: john@example.com", "block_bbox": [100, 500, 500, 530], "page": 1}
    page_blocks = [block]
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=800)
    assert result.role in ("frontmatter_noise", "unknown_structural"), (
        f"Correspondence got role: {result.role}"
    )


def test_backmatter_boundary_detects_on_early_page() -> None:
    """Backmatter boundary should be detectable on papers with fewer
    than 8 pages, without a hard page gate."""
    from paperforge.worker.ocr_roles import _is_backmatter_boundary_heading
    block = {
        "span_metadata": {"size": 12.0, "flags": "bold"},
        "text": "ADDITIONAL INFORMATION AND DECLARATIONS",
        "page": 5,
    }
    result = _is_backmatter_boundary_heading(block, 5, 10)
    assert result  # After fix: 5/10 = 50% in second half, has container words + bold
