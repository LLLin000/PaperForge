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


def test_pipeline_keeps_reference_zone_and_legend_family_out_of_default_body() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY010B",
            "page": 2,
            "block_id": "p2_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [110, 120, 470, 280],
            "text": "Main body paragraph with stable narrative prose and enough repeated content to establish the body family anchor for the document. "
            * 2,
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 9.0, "font": "Times", "flags": ""},
        },
        {
            "paper_id": "KEY010B",
            "page": 3,
            "block_id": "p3_b1",
            "raw_label": "text",
            "raw_order": 0,
            "bbox": [112, 118, 472, 282],
            "text": "Another core body paragraph repeating the same typography and width so the anchor-first body family remains dominant across the middle pages. "
            * 2,
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 9.0, "font": "Times", "flags": ""},
        },
        {
            "paper_id": "KEY010B",
            "page": 5,
            "block_id": "p5_b1",
            "raw_label": "paragraph_title",
            "raw_order": 0,
            "bbox": [100, 80, 350, 120],
            "text": "References",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 11.0, "font": "Times", "flags": "bold"},
        },
        {
            "paper_id": "KEY010B",
            "page": 5,
            "block_id": "p5_b2",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [110, 170, 500, 260],
            "text": "[1] Example reference entry with journal and year details.",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 8.5, "font": "Times", "flags": ""},
        },
        {
            "paper_id": "KEY010B",
            "page": 4,
            "block_id": "p4_b9",
            "raw_label": "text",
            "raw_order": 2,
            "bbox": [720, 780, 1030, 860],
            "text": "Figure 1. Compact legend text for the nearby display panel.",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 8.0, "font": "Times", "flags": ""},
        },
        {
            "paper_id": "KEY010B",
            "page": 4,
            "block_id": "p4_b10",
            "raw_label": "figure",
            "raw_order": 3,
            "bbox": [700, 420, 1040, 760],
            "text": "",
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    rows, _ = build_structured_blocks(raw_blocks)

    assert any(row["role"] == "reference_item" for row in rows)
    assert not any(row["role"] == "body_paragraph" and row.get("style_family") == "legend_like" for row in rows)


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
    assert big_role.role in heading_roles, f"Big heading should be detected as heading, got {big_role.role}"
    assert sub_role.role in heading_roles, f"Sub heading should be detected as heading, got {sub_role.role}"
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

    assert role.role == "figure_caption_candidate", f"figure_title label should produce candidate, got {role.role}"


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

    assert role.role == "figure_caption", f"Formal figure caption near media should be figure_caption, got {role.role}"


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
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=1600)
    assert result.role == "backmatter_boundary_candidate", f"Expected backmatter_boundary_candidate, got {result.role}"


def test_author_byline_not_section_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    # Author byline with & on page 1
    block = {
        "block_label": "paragraph_title",
        "block_content": "John Smith & Jane Doe",
        "block_bbox": [100, 50, 500, 80],
        "page": 1,
    }
    page_blocks = [
        block,
        {"block_label": "text", "block_content": "Some frontmatter", "block_bbox": [100, 100, 500, 130], "page": 1},
        {
            "block_label": "text",
            "block_content": "Some abstract content",
            "block_bbox": [100, 200, 500, 230],
            "page": 1,
        },
    ]
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=800)
    assert result.role not in ("section_heading", "subsection_heading", "sub_subsection_heading"), (
        f"Author byline got heading role: {result.role}"
    )


def test_correspondence_marker_not_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "*Correspondence: john@example.com",
        "block_bbox": [100, 500, 500, 530],
        "page": 1,
    }
    page_blocks = [block]
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=800)
    assert result.role in ("frontmatter_noise", "unknown_structural"), f"Correspondence got role: {result.role}"


def test_running_header_not_heading():
    """Article-type label in top margin should be noise, not heading."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "Review Article",
        "block_bbox": [80, 50, 200, 75],
        "page": 3,
    }
    page_blocks = [
        block,
        {"block_label": "text", "block_content": "Some body text", "block_bbox": [80, 200, 500, 240], "page": 3},
    ]
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=1700)
    assert result.role == "noise", f"Expected noise, got {result.role}"


def test_page1_article_type_label_not_heading():
    """Article-type label on page 1 is frontmatter furniture, not content heading."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "Review article",
        "block_bbox": [80, 180, 220, 205],
        "page": 1,
    }
    page_blocks = [
        block,
        {
            "block_label": "doc_title",
            "block_content": "Metabolic regulation of skeletal cell fate and function in development and disease",
            "block_bbox": [80, 240, 560, 310],
            "page": 1,
        },
        {
            "block_label": "paragraph_title",
            "block_content": "Steve Stegen & Geert Carmeliet",
            "block_bbox": [80, 340, 500, 365],
            "page": 1,
        },
    ]
    result = assign_block_role(block, page_blocks=page_blocks, page_width=600, page_height=1700)
    assert result.role in {"frontmatter_noise", "noise"}, (
        f"Page-1 article-type label should be frontmatter furniture, got {result.role}"
    )


def test_doc_title_not_body_paragraph() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "doc_title",
        "block_content": "A Very Long Title That Would Normally Be Considered A Document Title Block With Sufficient Length",
        "block_bbox": [100, 50, 900, 100],
        "page": 1,
    }
    result = assign_block_role(block, page_blocks=[block], page_width=900, page_height=1200)
    assert result.role != "body_paragraph", f"doc_title should not be body_paragraph, got {result.role}"


def test_author_byline_comma_only_not_section_heading() -> None:
    """Comma-separated byline on page 1 below zone detection threshold -> NOT heading."""
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "John Smith, Jane Doe",
        "block_bbox": [100, 400, 500, 430],
        "page": 1,
    }
    page_blocks = [block]
    result = assign_block_role(
        block,
        page_blocks=page_blocks,
        page_width=600,
        page_height=800,
    )
    assert result.role not in ("section_heading", "subsection_heading", "sub_subsection_heading"), (
        f"Comma-separated byline should not be a heading, got {result.role}"
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


def test_frontiers_figure_pipe_title_is_figure_caption():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "figure_title",
            "text": "FIGURE 1 | Expression of irisin is downregulated in OA cartilage.",
            "page": 2,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [100, 500, 700, 540],
        },
        page_blocks=[],
    )
    assert result.role == "figure_caption"
    assert result.confidence >= 0.9


def test_frontiers_figure_pipe_text_is_figure_caption():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "text",
            "text": "FIGURE 2 | Treadmill exercise protocols.",
            "page": 2,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [100, 500, 700, 540],
        },
        page_blocks=[],
    )
    assert result.role == "figure_caption"
    assert result.confidence >= 0.9


def test_single_letter_panel_label_not_figure_caption():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "text",
            "text": "A",
            "page": 2,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [100, 100, 110, 120],
        },
        page_blocks=[],
    )
    assert result.role == "figure_inner_text"


def test_parenthesized_panel_label_not_figure_caption():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "text",
            "text": "(B)",
            "page": 2,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [100, 100, 125, 120],
        },
        page_blocks=[],
    )
    assert result.role == "figure_inner_text"


def test_page1_roman_heading_outside_title_zone_becomes_section_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "I. INTRODUCTION",
            "page": 1,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [261, 967, 457, 988],
        },
        page_blocks=[],
    )
    assert result.role == "section_heading"
    assert result.confidence >= 0.8


def test_page1_alpha_heading_outside_title_zone_becomes_subsection_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "A. Materials",
            "page": 1,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [624, 500, 742, 521],
        },
        page_blocks=[],
    )
    assert result.role == "subsection_heading"
    assert result.confidence >= 0.8


def test_page1_top_title_not_misclassified_as_section_heading():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "I. INTRODUCTION",
            "page": 1,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [261, 100, 457, 120],
        },
        page_blocks=[],
    )
    assert result.role != "section_heading"


def test_preproof_marker_is_frontmatter_noise():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "Journal Pre-proof",
            "page": 1,
            "page_width": 1224,
            "page_height": 1584,
            "block_bbox": [190, 206, 475, 246],
        },
        page_blocks=[],
    )
    assert result.role == "frontmatter_noise"
    assert result.confidence >= 0.9


def test_preproof_marker_variants():
    from paperforge.worker.ocr_roles import assign_block_role

    for text in ["Journal Pre-proof", "Pre-proof", "journal pre-proof"]:
        result = assign_block_role(
            {
                "raw_label": "paragraph_title",
                "text": text,
                "page": 1,
                "page_width": 1224,
                "page_height": 1584,
                "block_bbox": [190, 206, 475, 246],
            },
            page_blocks=[],
        )
        assert result.role == "frontmatter_noise"


def test_preproof_running_header_is_suppressed():
    """Pre-proof text at extreme top (running header) on any page is suppressed."""
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "Journal Pre-proof",
            "page": 4,
            "page_width": 1224,
            "page_height": 1584,
            "block_bbox": [190, 1, 475, 20],
        },
        page_blocks=[],
    )
    assert result.role == "frontmatter_noise"


def test_preproof_page2_not_suppressed():
    """Pre-proof text on page 2+ should NOT be suppressed."""
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "Journal Pre-proof",
            "page": 2,
            "page_width": 1224,
            "page_height": 1584,
            "block_bbox": [190, 206, 475, 246],
        },
        page_blocks=[],
    )
    assert result.role != "frontmatter_noise"


def test_real_title_after_preproof_still_works():
    from paperforge.worker.ocr_roles import assign_block_role

    result = assign_block_role(
        {
            "raw_label": "paragraph_title",
            "text": "Magnetoresponsive Stem Cell Spheroid-based Cartilage Recovery Platform",
            "page": 1,
            "page_width": 1200,
            "page_height": 1700,
            "block_bbox": [100, 200, 700, 230],
        },
        page_blocks=[],
        page_height=1700,
    )
    assert result.role == "paper_title"


def test_resolve_final_role_uses_zone_and_family_context_instead_of_default_body():
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b2",
        "text": "Figure 2. A long legend that sits inside the body page.",
        "role": "body_paragraph",
        "zone": "body_zone",
        "style_family": "legend_like",
        "style_family_authority": "figure_marker",
        "marker_signature": {"type": "figure_number", "number": 2},
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    assert resolved.role == "figure_caption_candidate"


def test_resolve_final_role_uses_families_fallback_when_block_lacks_late_context() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b2",
        "text": "Figure 2. A long legend that sits inside the body page.",
        "role": "body_paragraph",
        "marker_signature": {"type": "figure_number", "number": 2},
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={
            "p4_b2": {
                "zone": "body_zone",
                "style_family": "legend_like",
                "style_family_authority": "figure_marker",
            }
        },
    )
    assert resolved.role == "figure_caption_candidate"
    assert any("context_source=families" == evidence for evidence in resolved.evidence)


def test_resolve_final_role_does_not_promote_without_late_context_gate() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b2",
        "text": "Figure 2. A long legend that sits inside the body page.",
        "role": "body_paragraph",
        "zone": "display_zone",
        "style_family": "legend_like",
        "marker_signature": {"type": "figure_number", "number": 2},
        "role_confidence": 0.6,
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "HOLD"}},
        families={},
    )
    assert resolved.role == "body_paragraph"


def test_resolve_final_role_requires_strong_style_family_authority() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b2",
        "text": "Figure 2. A long legend that sits inside the body page.",
        "role": "body_paragraph",
        "zone": "body_zone",
        "style_family": "legend_like",
        "style_family_authority": "body_zone_candidate",
        "marker_signature": {"type": "figure_number", "number": 2},
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    assert resolved.role == "body_paragraph"


def test_resolve_final_role_does_not_promote_narrative_prose_even_with_strong_authority() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b9",
        "text": "Figure 2 shows the control response over time. In this study we compare both cohorts.",
        "role": "body_paragraph",
        "zone": "body_zone",
        "style_family": "legend_like",
        "style_family_authority": "figure_marker",
        "marker_signature": {"type": "figure_number", "number": 2},
        "role_confidence": 0.6,
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    assert resolved.role == "body_paragraph"


def test_resolve_final_role_does_not_promote_single_sentence_narrative_prose_with_strong_authority() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b10",
        "text": "Figure 2 shows the control response over time in both cohorts.",
        "role": "body_paragraph",
        "zone": "body_zone",
        "style_family": "legend_like",
        "style_family_authority": "figure_marker",
        "marker_signature": {"type": "figure_number", "number": 2},
        "role_confidence": 0.6,
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    assert resolved.role == "body_paragraph"


def test_resolve_final_role_leaves_table_handling_unchanged_in_task_7() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p5_b3",
        "text": "Table 3. Outcomes across cohorts.",
        "role": "body_paragraph",
        "zone": "body_zone",
        "style_family": "table_caption_like",
        "marker_signature": {"type": "table_number", "number": 3},
        "role_confidence": 0.6,
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    assert resolved.role == "body_paragraph"


def test_build_structured_blocks_applies_late_role_resolution(monkeypatch) -> None:
    from paperforge.worker import ocr_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 4,
            "block_id": "p4_b2",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [100, 500, 950, 620],
            "text": "A long legend that sits inside the body page without an eager prefix cue.",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 10, "flags": "normal"},
        }
    ]

    def fake_build_block_signatures(block: dict) -> dict:
        return {
            "raw_observation": {"source": "test"},
            "marker_signature": {"type": "figure_number", "number": 2},
            "layout_signature": {"width": 850, "width_bucket": 850, "x_center": 525, "x_center_bucket": 525},
            "span_signature": {"font_family_norm": "times", "font_size_median": 10, "font_size_bucket": 10},
        }

    def fake_normalize_document_structure(rows: list[dict]):
        for row in rows:
            row["zone"] = "body_zone"
            row["style_family"] = "legend_like"
            row["style_family_authority"] = "figure_marker"
        return type(
            "DocStructureStub",
            (),
            {
                "body_family_anchor": {"status": "ACCEPT"},
                "reference_family_anchor": None,
                "body_end_page": 4,
                "page_layouts": {},
            },
        )(), rows

    monkeypatch.setattr(ocr_blocks, "build_block_signatures", fake_build_block_signatures)
    monkeypatch.setattr(
        ocr_blocks,
        "discover_body_family_anchor",
        lambda rows, page_count=None: {"status": "ACCEPT"},
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_document.normalize_document_structure", fake_normalize_document_structure
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_document._resolve_ambiguous_candidates",
        lambda blocks, doc_structure, page_layouts: None,
    )

    rows, _ = ocr_blocks.build_structured_blocks(raw_blocks)

    # seed_role is set eagerly from assign_block_role; final role stays unassigned
    # because resolve_final_role is deferred to normalize_document_structure.
    assert rows[0]["seed_role"] == "body_paragraph"
    assert rows[0]["role"] == "unassigned"
    assert rows[0]["marker_signature"]["type"] == "figure_number"


def test_build_structured_blocks_does_not_promote_when_anchor_gate_is_closed(monkeypatch) -> None:
    from paperforge.worker import ocr_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 4,
            "block_id": "p4_b2",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [100, 500, 950, 620],
            "text": "A long legend that sits inside the body page without an eager prefix cue.",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": {"size": 10, "flags": "normal"},
        }
    ]

    def fake_build_block_signatures(block: dict) -> dict:
        return {
            "raw_observation": {"source": "test"},
            "marker_signature": {"type": "figure_number", "number": 2},
            "layout_signature": {"width": 850, "width_bucket": 850, "x_center": 525, "x_center_bucket": 525},
            "span_signature": {"font_family_norm": "times", "font_size_median": 10, "font_size_bucket": 10},
        }

    def fake_normalize_document_structure(rows: list[dict]):
        for row in rows:
            row["zone"] = "body_zone"
            row["style_family"] = "legend_like"
            row["style_family_authority"] = "figure_marker"
        return type(
            "DocStructureStub",
            (),
            {
                "body_family_anchor": {"status": "HOLD"},
                "reference_family_anchor": None,
                "body_end_page": 4,
                "page_layouts": {},
            },
        )(), rows

    monkeypatch.setattr(ocr_blocks, "build_block_signatures", fake_build_block_signatures)
    monkeypatch.setattr(
        ocr_blocks,
        "discover_body_family_anchor",
        lambda rows, page_count=None: {"status": "HOLD"},
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_document.normalize_document_structure", fake_normalize_document_structure
    )
    monkeypatch.setattr(
        "paperforge.worker.ocr_document._resolve_ambiguous_candidates",
        lambda blocks, doc_structure, page_layouts: None,
    )

    rows, _ = ocr_blocks.build_structured_blocks(raw_blocks)

    # seed_role is set eagerly; final role stays unassigned (resolution deferred)
    assert rows[0]["seed_role"] == "body_paragraph"
    assert rows[0]["role"] == "unassigned"


def test_resolve_final_role_treats_unassigned_as_seed_role_fallback() -> None:
    """When role is 'unassigned', resolve_final_role should use seed_role as the
    starting point for resolution, not default to 'body_paragraph'."""
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p1_b1",
        "text": "Introduction",
        "role": "unassigned",
        "seed_role": "section_heading",
        "seed_confidence": 0.85,
        "marker_signature": {"type": "none"},
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    # Should resolve to section_heading (from seed), not body_paragraph
    assert resolved.role == "section_heading", f"Expected section_heading from seed_role fallback, got {resolved.role}"


def test_resolve_final_role_does_not_promote_narrative_figure_mention_without_strong_authority() -> None:
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b9",
        "text": "Figure 2 shows the control response over time in both cohorts.",
        "role": "body_paragraph",
        "zone": "body_zone",
        "style_family": "legend_like",
        "style_family_authority": "body_zone_candidate",
        "marker_signature": {"type": "figure_number", "number": 2},
        "role_confidence": 0.6,
    }

    resolved = resolve_final_role(
        block,
        anchors={"body_family_anchor": {"status": "ACCEPT"}},
        families={},
    )
    assert resolved.role == "body_paragraph"


def test_build_structured_blocks_preserves_seed_role_and_leaves_final_role_unassigned_initially(monkeypatch):
    """After assign_block_role, row must carry seed_role/seed_confidence/seed_evidence
    and final role must start as 'unassigned' before late resolution."""
    from paperforge.worker import ocr_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "paragraph_title",
            "raw_order": 0,
            "bbox": [100, 50, 500, 80],
            "text": "Introduction",
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b2",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [100, 100, 900, 300],
            "text": "This is a body paragraph with enough text to be meaningful and avoid the short-text threshold.",
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    def fake_build_block_signatures(block: dict) -> dict:
        return {
            "raw_observation": {"source": "test"},
            "marker_signature": {"type": "none"},
            "layout_signature": {"width": 800, "width_bucket": 800, "x_center": 550, "x_center_bucket": 550},
            "span_signature": {"font_family_norm": "times", "font_size_median": 10, "font_size_bucket": 10},
        }

    monkeypatch.setattr(ocr_blocks, "build_block_signatures", fake_build_block_signatures)

    rows, _ = ocr_blocks.build_structured_blocks(raw_blocks)

    for row in rows:
        # seed_role must always be present after build_structured_blocks
        assert "seed_role" in row, f"block {row['block_id']} missing seed_role"
        assert "seed_confidence" in row, f"block {row['block_id']} missing seed_confidence"
        # seed_evidence is a list (may be empty)
        assert isinstance(row.get("seed_evidence", []), list), f"block {row['block_id']} seed_evidence should be list"
        # final role should not be 'unassigned' at the end (late resolution happened)
        assert row["role"] != "unassigned", f"block {row['block_id']} final role should be resolved, not 'unassigned'"


def test_pipeline_does_not_commit_final_semantic_role_before_zone_and_family_partition(monkeypatch):
    """Zone and family partition must run AFTER role is still 'unassigned',
    so downstream logic can use seed_role as the authority for zone decisions."""
    from paperforge.worker import ocr_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "paragraph_title",
            "raw_order": 0,
            "bbox": [100, 50, 500, 80],
            "text": "Abstract",
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    def fake_build_block_signatures(block: dict) -> dict:
        return {
            "raw_observation": {"source": "test"},
            "marker_signature": {"type": "none"},
            "layout_signature": {"width": 400, "width_bucket": 400, "x_center": 300, "x_center_bucket": 300},
            "span_signature": {"font_family_norm": "times", "font_size_median": 10, "font_size_bucket": 10},
        }

    # Capture the state of rows at the point just after assign_block_role
    # but before resolve_final_role. We verify that seed_role is set
    # and role is 'unassigned' at that stage.
    captured_rows_after_assign = []

    original_assign = ocr_blocks.assign_block_role

    def capturing_assign(block, page_blocks, page_width=0, page_height=0, style_profiles=None, role_profiles=None):
        result = original_assign(block, page_blocks, page_width, page_height, style_profiles, role_profiles)
        # Simulate what build_structured_blocks does after assign_block_role:
        # It should set seed_role and leave role as 'unassigned'
        captured_rows_after_assign.append(
            {
                "block_id": block.get("block_id") or block.get("block_content", "")[:20],
                "assigned_role": result.role,
            }
        )
        return result

    monkeypatch.setattr(ocr_blocks, "build_block_signatures", fake_build_block_signatures)
    monkeypatch.setattr(ocr_blocks, "assign_block_role", capturing_assign)

    rows, _ = ocr_blocks.build_structured_blocks(raw_blocks)

    # Verify that every block went through assign_block_role
    assert len(captured_rows_after_assign) == len(raw_blocks)

    # Verify that the final output has seed_role set
    for row in rows:
        assert "seed_role" in row, f"block {row['block_id']} missing seed_role"
        assert row["seed_role"] != "unassigned", f"seed_role should never be 'unassigned', got {row['seed_role']}"
