from __future__ import annotations


def test_stabilize_render_suppresses_frontmatter_noise() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "section_heading",
            "text": "OPEN ACCESS",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "section_heading",
            "text": "CITATION",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b3",
            "role": "body_paragraph",
            "text": "Real body text should render.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "OPEN ACCESS" not in md
    assert "CITATION" not in md
    assert "Real body text should render." in md


def test_stabilize_render_output_starts_with_metadata_and_abstract() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    resolved_metadata = {
        "title": {"value": "Test Paper Title"},
        "authors": {"value": ["Author A", "Author B"]},
        "journal": {"value": "Test Journal"},
        "year": {"value": 2025},
        "doi": {"value": "10.1000/xyz"},
    }
    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "abstract_heading",
            "text": "Abstract",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "abstract_body",
            "text": "This is the abstract text.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 2,
            "block_id": "b3",
            "role": "section_heading",
            "text": "1 Introduction",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
        figure_inventory={},
        table_inventory={},
    )

    lines = md.strip().split("\n")
    assert lines[0].startswith("# Test Paper Title")
    title_idx = next(i for i, l in enumerate(lines) if l.startswith("# Test"))
    abstract_idx = next(i for i, l in enumerate(lines) if "Abstract" in l and l.startswith("##"))
    intro_idx = next(i for i, l in enumerate(lines) if "Introduction" in l)
    assert title_idx < abstract_idx < intro_idx


def test_stabilize_figure_not_appended_at_end() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "Body text.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 2,
            "block_id": "b2",
            "role": "figure_caption",
            "text": "Figure 1. Results.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "b3",
            "role": "section_heading",
            "text": "2 Discussion",
            "render_default": True,
        },
    ]
    figure_inventory = {
        "matched_figures": [{"figure_id": "fig_001", "page": 2}],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory=figure_inventory,
        table_inventory={},
    )

    discussion_idx = md.index("2 Discussion")
    fig_link_idx = md.index("![[render/figures/fig_001.md]]")
    assert fig_link_idx < discussion_idx


def test_stabilize_latex_normalization() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "Expression $ ^{1} $ and $ ^{\\u2020} $ should be compact.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "$^{1}$" in md
    assert "$ ^{1} $" not in md
    assert "$^{\\u2020}$" in md or "$^{†}$" in md


def test_stabilize_no_inline_table_html() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "table_html",
            "text": "<table><tr><td>data</td></tr></table>",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Real body text.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "<table>" not in md
    assert "Real body text." in md


def test_stabilize_author_recovery_from_ocr() -> None:
    from paperforge.worker.ocr_metadata import extract_frontmatter_candidates, resolve_metadata
    import json, tempfile, pathlib

    blocks_data = (
        json.dumps({"role": "paper_title", "text": "Test Paper"})
        + "\n"
        + json.dumps({"role": "authors", "text": "Alice Smith, Bob Jones"})
        + "\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(blocks_data)
        tmppath = pathlib.Path(f.name)

    try:
        candidates = extract_frontmatter_candidates(tmppath)
        resolved = resolve_metadata({"title": "Test Paper"}, candidates)
        authors = resolved.get("authors", {})
        assert len(authors.get("value", [])) > 0, "Authors should be recovered from OCR"
        assert "Alice Smith" in authors["value"]
    finally:
        tmppath.unlink()


def test_stabilize_heading_sanity_downgrades_long_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    # A very long section_heading (>100 chars) should be downgraded to body text
    long_text = "This is a very long heading that exceeds one hundred characters and should definitely be downgraded to a body paragraph instead of being rendered as a heading"
    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "section_heading",
            "text": long_text,
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Normal body text.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    # The long heading should NOT appear as a markdown heading
    assert "## " + long_text not in md
    # But the text itself should still be present (downgraded)
    assert long_text in md


def test_stabilize_heading_sanity_downgrades_multi_sentence_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    # A heading with multiple sentence-ending periods should be downgraded
    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "section_heading",
            "text": "This is a heading. It has multiple sentences. This is the third one.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Normal body text.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "## This is a heading" not in md
    assert "This is a heading. It has multiple sentences." in md


def test_stabilize_heading_sanity_allows_valid_short_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "section_heading",
            "text": "1 Introduction",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "## 1 Introduction" in md


def test_stabilize_heading_sanity_downgrades_verb_heavy_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    # A heading longer than 50 chars with common sentence verbs should be downgraded
    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "section_heading",
            "text": "This is a method that was used for the experiment and has many words",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Normal body text.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "## This is a method" not in md
    assert "This is a method that was used" in md


def test_stabilize_heading_sanity_allows_verb_short_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    # A short heading with verbs is OK (under 50 chars)
    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "section_heading",
            "text": "Results are shown",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "## Results are shown" in md


def test_stabilize_reference_content_mapped() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    assignment = assign_block_role(
        block={"block_label": "reference_content", "block_content": "Smith J. et al. (2024) A study on...", "page": 20},
        page_blocks=[],
    )

    assert assignment.role == "reference_item"
    assert assignment.confidence >= 0.8


def test_stabilize_page_marker_count_matches_page_count() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "Page 1 body.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Page 3 body.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=5,
    )

    page_markers = [line for line in md.split("\n") if line.strip().startswith("<!-- page")]
    expected_page_count = 5
    assert len(page_markers) == expected_page_count, (
        f"Expected {expected_page_count} page markers, got {len(page_markers)}"
    )


def test_stabilize_references_renders_as_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b2",
            "role": "reference_item",
            "text": "Smith J, Jones B. (2024) A study on something. Journal of Examples.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "## References" in md
    assert "Smith J, Jones B." in md


def test_stabilize_reference_items_grouped_under_heading() -> None:
    """Reference items stay under ## References, not claimed by later headings."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b2",
            "role": "reference_item",
            "text": "Smith J. (2024) A study.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Publisher's note",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "Springer Nature remains neutral.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b5",
            "role": "reference_item",
            "text": "Jones B. (2023) Another study.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    ref_idx = md.index("## References")
    pub_idx = md.index("**Publisher's note**")
    smith_idx = md.index("Smith J.")
    jones_idx = md.index("Jones B.")

    assert smith_idx > pub_idx, "First reference item should appear under References, after backmatter"
    assert jones_idx > pub_idx, "Second reference item should appear under References, after backmatter"
    assert smith_idx > ref_idx and jones_idx > ref_idx, "Reference items should appear after References heading"


def test_render_mixed_tail_page_ordering() -> None:
    """Mixed tail page rendered via tail_reading_order segments.

    Blocks have no bbox data so _order_tail_blocks falls back to FIFO,
    which cannot attach backmatter bodies to their headings when bodies
    appear before headings in source order — bodies end up as orphans
    emitted after references.  tail_reading_order overrides this to
    produce correct human reading order.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown
    from paperforge.worker.ocr_document import DocumentStructure

    blocks = [
        {
            "paper_id": "KEY001", "page": 1, "block_id": "b1",
            "role": "body_paragraph",
            "text": "Introduction text here.",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b4",
            "role": "backmatter_body",
            "text": "No AI generated content was used.",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b6",
            "role": "backmatter_body",
            "text": "Springer Nature remains neutral.",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b2",
            "role": "body_paragraph",
            "text": "Left column body continuation text.",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Generative AI statement",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b5",
            "role": "backmatter_heading",
            "text": "Publisher's note",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b7",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b8",
            "role": "reference_item",
            "text": "Smith J, Jones B. (2024) A study on electric fields.",
            "render_default": True,
            "raw_label": "text",
        },
    ]

    ds = DocumentStructure(
        spread_start=71,
        spread_end=71,
        tail_reading_order=[
            {
                "page": 71, "column_index": 0,
                "block_indices": [3],
                "semantic_hint": "body",
                "y_top": 50, "y_bottom": 100,
            },
            {
                "page": 71, "column_index": 0,
                "block_indices": [4, 1],
                "semantic_hint": "backmatter",
                "y_top": 200, "y_bottom": 300,
            },
            {
                "page": 71, "column_index": 1,
                "block_indices": [5, 2],
                "semantic_hint": "backmatter",
                "y_top": 50, "y_bottom": 150,
            },
            {
                "page": 71, "column_index": 1,
                "block_indices": [6, 7],
                "semantic_hint": "references",
                "y_top": 350, "y_bottom": 450,
            },
        ],
    )

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        document_structure=ds,
    )

    body_idx = md.index("Left column body continuation text.")
    gen_ai_idx = md.index("**Generative AI statement**")
    gen_ai_body_idx = md.index("No AI generated content was used.")
    pub_idx = md.index("**Publisher's note**")
    pub_body_idx = md.index("Springer Nature remains neutral.")
    ref_idx = md.index("## References")
    smith_idx = md.index("Smith J, Jones B.")

    assert body_idx < gen_ai_idx, "Left body should come before Generative AI backmatter"
    assert gen_ai_idx < gen_ai_body_idx, "Generative AI heading should come before its body"
    assert gen_ai_body_idx < pub_idx, "Left backmatter should come before right backmatter"
    assert pub_idx < pub_body_idx, "Publisher's note heading should come before its body"
    assert pub_body_idx < ref_idx, "Backmatter body should come before References"
    assert ref_idx < smith_idx, "References heading should come before items"


def test_render_tail_reading_order_does_not_push_tail_page_after_next_page() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown
    from paperforge.worker.ocr_document import DocumentStructure

    blocks = [
        {
            "paper_id": "KEY001", "page": 70, "block_id": "b70",
            "role": "body_paragraph", "text": "Page 70 body.", "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b71a",
            "role": "body_paragraph", "text": "Page 71 tail body.", "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b71h",
            "role": "backmatter_heading", "text": "Acknowledgements", "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b71r",
            "role": "reference_heading", "text": "References", "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 71, "block_id": "b71i",
            "role": "reference_item", "text": "1. Ref on page 71.", "render_default": True,
            "raw_label": "text",
        },
        {
            "paper_id": "KEY001", "page": 72, "block_id": "b72",
            "role": "reference_item", "text": "2. Ref on page 72.", "render_default": True,
            "raw_label": "text",
        },
    ]

    ds = DocumentStructure(
        spread_start=71,
        spread_end=71,
        tail_reading_order=[
            {
                "page": 71, "column_index": 0,
                "block_indices": [1, 2],
                "semantic_hint": "mixed",
                "y_top": 100, "y_bottom": 300,
            },
            {
                "page": 71, "column_index": 1,
                "block_indices": [3, 4],
                "semantic_hint": "references",
                "y_top": 400, "y_bottom": 700,
            },
        ],
    )

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=72,
        document_structure=ds,
    )

    page71_marker = md.index("<!-- page 71 -->")
    page71_body = md.index("Page 71 tail body.")
    page71_ref = md.index("1. Ref on page 71.")
    page72_marker = md.index("<!-- page 72 -->")
    page72_ref = md.index("2. Ref on page 72.")

    assert page71_marker < page71_body < page71_ref < page72_marker < page72_ref


def test_non_body_insert_not_in_fulltext() -> None:
    """Verify non_body_insert blocks do not appear in fulltext.md."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"role": "non_body_insert", "text": "Dr Ya Huang is currently...", "page": 1,
         "bbox": [50, 200, 300, 240], "render_default": False,
         "raw_label": "text", "page_width": 1200, "page_height": 1600},
        {"role": "body_paragraph", "text": "Real body text here.", "page": 1,
         "bbox": [100, 600, 800, 640], "render_default": True,
         "raw_label": "text", "page_width": 1200, "page_height": 1600},
    ]
    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )
    assert "Ya Huang" not in md, "non_body_insert should not appear in fulltext"
    assert "Real body text" in md, "body_paragraph should appear"


def test_stabilize_tail_zone_references_kept_separate() -> None:
    """Multi-page tail: reference items on continuation page stay under References."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b2",
            "role": "reference_item",
            "text": "Smith J. (2024) A study on electric fields.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Generative AI statement",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "The authors declare no AI-generated content.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b5",
            "role": "backmatter_heading",
            "text": "Publisher's note",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b6",
            "role": "backmatter_body",
            "text": "Springer Nature remains neutral.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 23,
            "block_id": "b7",
            "role": "reference_item",
            "text": "Jones B. (2023) Another study on galvanotaxis.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 23,
            "block_id": "b8",
            "role": "reference_item",
            "text": "Cai J. (2020) Additional reference.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=23,
    )

    assert "## References" in md
    assert "**Generative AI statement**" in md
    assert "**Publisher's note**" in md

    refs_idx = md.index("## References")
    gen_ai_idx = md.index("**Generative AI statement**")
    pub_idx = md.index("**Publisher's note**")
    decl_idx = md.index("The authors declare no AI-generated content.")
    springer_idx = md.index("Springer Nature remains neutral.")
    smith_idx = md.index("Smith J.")
    jones_idx = md.index("Jones B.")
    cai_idx = md.index("Cai J.")

    assert decl_idx < refs_idx, "Gen AI body should appear before References"
    assert springer_idx < refs_idx, "Publisher's note body should appear before References"
    assert smith_idx > refs_idx, "Page 22 reference item should be under References"
    assert jones_idx > refs_idx, "Page 23 reference item should be under References, not dropped"
    assert cai_idx > refs_idx, "Page 23 second reference item should be under References"
    assert "<!-- page 22" in md, "Page marker for page 22 should be present"
    assert "<!-- page 23" in md, "Page marker for page 23 should be present"


def test_fallback_preserves_tail_roles():
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"paper_id": "KEY", "page": 5, "block_id": "b1", "role": "backmatter_heading", "text": "Funding", "render_default": True, "bbox": [80, 200, 320, 240], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 5, "block_id": "b2", "role": "backmatter_body", "text": "This work was supported by Grant A.", "render_default": True, "bbox": [80, 280, 520, 340], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 5, "block_id": "b3", "role": "reference_item", "text": "Smith J. (2023)", "render_default": True, "bbox": [80, 400, 520, 440], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "**Funding**" in md, "backmatter_heading should be preserved"
    assert "This work was supported" in md, "backmatter_body should be preserved"
    assert "Smith J." in md, "reference_item should be preserved"


def test_normalize_ocr_math_text_delimiter_spacing() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text("$ ^{8,49} $") == "$^{8,49}$"
    assert normalize_ocr_math_text(r"$ \mu $m") == r"$\mu$m"


def test_normalize_ocr_math_text_citation_superscript() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    result = normalize_ocr_math_text("systems.$^{1-3}$One")
    assert "$^{1-3}$" in result
    assert "One" in result


def test_normalize_ocr_math_text_prose_boundary() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text("comparative$C_T$") == "comparative $C_T$"


def test_normalize_ocr_math_text_hyphen_preserved() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    result = normalize_ocr_math_text(r"TGF-$\beta$")
    assert r"TGF-$\beta$" in result


def test_normalize_ocr_math_text_relop_followed_by_digit() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text(r"$\geq$100") == r"$\geq$ 100"
    assert normalize_ocr_math_text(r"$\leq$0.5") == r"$\leq$ 0.5"
    assert normalize_ocr_math_text(r"$\sim$1000") == r"$\sim$ 1000"
    assert normalize_ocr_math_text(r"$\approx$3.14") == r"$\approx$ 3.14"


def test_normalize_ocr_math_text_relop_followed_by_unit() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    result = normalize_ocr_math_text(r"$\sim$1000Scm^{-1}")
    assert r"$\sim$ 1000Scm^{-1}" in result


def test_normalize_ocr_math_text_greek_letter_compound_preserved() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text(r"NF-$\kappa$B") == r"NF-$\kappa$B"
    assert normalize_ocr_math_text(r"TGF-$\beta$") == r"TGF-$\beta$"


def test_normalize_ocr_math_text_display_math() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text("$$ ... $$") == "$$...$$"


def test_structured_insert_renders_as_single_callout_without_swallowing_body() -> None:
    """structured_insert should render as one callout and must not absorb body text."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "b1",
            "role": "section_heading",
            "text": "2 Results",
            "render_default": True,
            "bbox": [80, 50, 500, 80],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "b2",
            "role": "structured_insert",
            "text": "Key points:\n\u2022 Point one\n\u2022 Point two",
            "render_default": False,
            "index_default": False,
            "bbox": [80, 100, 500, 200],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "b3",
            "role": "body_paragraph",
            "text": "Body text continues here.",
            "render_default": True,
            "bbox": [80, 220, 500, 250],
            "page_width": 1200,
            "page_height": 1700,
        },
    ]
    md = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={}, figure_inventory={}, table_inventory={})

    assert "2 Results" in md
    assert "Key points" in md, "structured_insert heading should render"
    assert "Point one" in md, "structured_insert content should render"
    assert "Point two" in md, "structured_insert content should render"
    assert md.count("[!NOTE]") == 1, f"Expected exactly one callout, got markdown:\n{md}"
    assert "Body text continues" in md


def test_adjacent_structured_insert_blocks_merge_into_one_callout() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "s1",
            "role": "structured_insert",
            "text": "Key points",
            "render_default": False,
            "index_default": False,
            "bbox": [80, 100, 200, 130],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "s2",
            "role": "structured_insert",
            "text": "• Point one\n• Point two",
            "render_default": False,
            "index_default": False,
            "bbox": [80, 140, 500, 260],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "Main body resumes here.",
            "render_default": True,
            "bbox": [80, 320, 500, 360],
            "page_width": 1200,
            "page_height": 1700,
        },
    ]

    md = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={}, figure_inventory={}, table_inventory={})

    assert md.count("[!NOTE]") == 1, f"Expected merged callout, got markdown:\n{md}"
    assert "Key points" in md
    assert "Point one" in md
    assert "Point two" in md
    assert "Key points\n\n> • Point one" not in md, f"Merged callout should not contain blank separator:\n{md}"
    assert "Main body resumes here." in md


def test_malformed_sidebar_tail_fragment_is_dropped_when_continuation_block_follows() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "s1",
            "role": "structured_insert",
            "text": "<table><tr><td>• Point one</td></tr><tr><td>cell dysfunctionatic and leukaemic cells• their tumorigenic spread.</td></tr></table>",
            "render_default": False,
            "index_default": False,
            "bbox": [80, 140, 500, 260],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY",
            "page": 2,
            "block_id": "s2",
            "role": "structured_insert",
            "text": "• Metabolic disturbance is linked to skeletal cell dysfunction during bone pathology, and bone-metastatic and leukaemic cells hijack skeletal cell metabolism to support their tumorigenic spread.",
            "render_default": False,
            "index_default": False,
            "bbox": [80, 265, 500, 320],
            "page_width": 1200,
            "page_height": 1700,
        },
    ]

    md = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={}, figure_inventory={}, table_inventory={})

    assert "cell dysfunctionatic and leukaemic cells• their tumorigenic spread." not in md
    assert "Metabolic disturbance is linked to skeletal cell dysfunction" in md


def test_section_heading_renders_with_prefix() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown
    blocks = [
        {"paper_id": "KEY", "page": 3, "block_id": "b1", "role": "section_heading", "text": "1 Introduction", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
    ]
    md = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={}, figure_inventory={}, table_inventory={})
    assert "## 1 Introduction" in md, f"Expected ## prefix, got: {md[:200]}"


def test_unumbered_subsection_headings_use_double_hash_by_default() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"paper_id": "KEY", "page": 2, "block_id": "h1", "role": "sub_subsection_heading", "text": "Introduction", "render_default": True, "bbox": [80, 200, 300, 230], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 2, "block_id": "h2", "role": "subsection_heading", "text": "2.5 Electrical stimulation", "render_default": True, "bbox": [80, 260, 700, 300], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    lines = md.splitlines()
    assert "## Introduction" in lines
    assert "### 2.5 Electrical stimulation" in lines


# === 2GN9LMCW / 7C8829BD guard tests (Task 7 -- preserve tail mainline) ===


def test_2gn9lmcw_container_ordering() -> None:
    """2GN9LMCW container backmatter ordering: ADDITIONAL INFORMATION -> Funding -> Grant Disclosures."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b1", "role": "reference_heading", "text": "References", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b2", "role": "reference_item", "text": "Smith J. (2024) A study on electric fields in cellular systems.", "render_default": True, "bbox": [80, 250, 500, 280], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b3", "role": "backmatter_heading", "text": "ADDITIONAL INFORMATION", "render_default": True, "bbox": [80, 300, 500, 330], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b4", "role": "backmatter_body", "text": "Additional information and correspondence regarding this article.", "render_default": True, "bbox": [80, 340, 500, 370], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b5", "role": "backmatter_heading", "text": "Funding", "render_default": True, "bbox": [80, 400, 500, 430], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b6", "role": "backmatter_body", "text": "This work was supported by Grant No. 12345 from the National Science Foundation.", "render_default": True, "bbox": [80, 440, 500, 470], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b7", "role": "backmatter_heading", "text": "Grant Disclosures", "render_default": True, "bbox": [80, 500, 500, 530], "page_width": 1200, "page_height": 1700},
        {"paper_id": "2GN9LMCW", "page": 5, "block_id": "b8", "role": "backmatter_body", "text": "The authors declare no competing grant disclosures or financial interests.", "render_default": True, "bbox": [80, 540, 500, 570], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    ai_idx = md.index("**ADDITIONAL INFORMATION**")
    ai_body_idx = md.index("Additional information and correspondence")
    funding_idx = md.index("**Funding**")
    funding_body_idx = md.index("Grant No. 12345")
    grant_idx = md.index("**Grant Disclosures**")

    assert ai_idx < ai_body_idx < funding_idx < funding_body_idx < grant_idx, (
        "Container backmatter must maintain order: ADDITIONAL INFORMATION -> Funding -> Grant Disclosures"
    )


def test_7c8829bd_tail_markers_monotonic() -> None:
    """7C8829BD tail page markers stay in monotonic order (body content only)."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    # Note: reference/backmatter roles trigger a separate tail spread
    # rendering pass that re-emits page markers.  We use body_paragraph
    # blocks here to test the baseline monotonicity contract; tail
    # content ordering is verified separately by render-level tests.
    blocks = [
        {"paper_id": "7C8829BD", "page": 70, "block_id": "b70", "role": "body_paragraph", "text": "Page 70 body text.", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
        {"paper_id": "7C8829BD", "page": 71, "block_id": "b71", "role": "body_paragraph", "text": "Page 71 body text.", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
        {"paper_id": "7C8829BD", "page": 72, "block_id": "b72", "role": "body_paragraph", "text": "Page 72 body text.", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
        {"paper_id": "7C8829BD", "page": 73, "block_id": "b73", "role": "body_paragraph", "text": "Page 73 body text.", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
        {"paper_id": "7C8829BD", "page": 74, "block_id": "b74", "role": "body_paragraph", "text": "Page 74 body text.", "render_default": True, "bbox": [80, 200, 500, 230], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=74,
    )

    page_markers = [line.strip() for line in md.split("\n") if line.strip().startswith("<!-- page")]
    marker_pages = [int(m.split()[2]) for m in page_markers]
    assert marker_pages == sorted(marker_pages), (
        "Tail page markers must be in monotonic order"
    )


def test_render_fulltext_abstract_ids_do_not_consume_later_page_blocks_with_same_raw_id() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    doc = DocumentStructure()
    doc.abstract_span = {"heading_block_id": "p1:8", "body_block_ids": ["p1:9", "p1:10"], "status": "ACCEPT"}

    blocks = [
        {"paper_id": "KEY", "page": 1, "block_id": 8, "role": "abstract_heading", "text": "Abstract", "render_default": True, "bbox": [80, 100, 300, 130], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 1, "block_id": 9, "role": "abstract_body", "text": "Abstract body line one.", "render_default": True, "bbox": [80, 140, 900, 200], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 1, "block_id": 10, "role": "abstract_body", "text": "Abstract body line two.", "render_default": True, "bbox": [80, 210, 900, 270], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 2, "block_id": 9, "role": "section_heading", "text": "Conclusion", "render_default": True, "bbox": [80, 100, 400, 130], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 2, "block_id": 10, "role": "body_paragraph", "text": "Later-page body paragraph must survive duplicate raw block ids.", "render_default": True, "bbox": [80, 150, 950, 220], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 2, "block_id": 8, "role": "reference_heading", "text": "References", "render_default": True, "bbox": [80, 260, 400, 290], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        document_structure=doc,
    )

    assert "## Abstract" in md
    assert "## Conclusion" in md
    assert "Later-page body paragraph must survive" in md
    assert "## References" in md


def test_render_fulltext_backmatter_like_section_heading_renders_bold_instead_of_disappearing() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"paper_id": "KEY", "page": 5, "block_id": "h1", "role": "section_heading", "text": "AUTHOR CONTRIBUTIONS", "render_default": True, "bbox": [80, 100, 500, 130], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 5, "block_id": "b1", "role": "body_paragraph", "text": "A.B. designed the study and wrote the first draft.", "render_default": True, "bbox": [80, 150, 1000, 210], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "**AUTHOR CONTRIBUTIONS**" in md
    assert "A.B. designed the study" in md


def test_tail_page_backmatter_headings_claim_same_column_body_paragraphs() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"paper_id": "KEY", "page": 14, "block_id": "e1", "role": "section_heading", "text": "ETHICS STATEMENT", "render_default": True, "bbox": [80, 100, 360, 130], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "e2", "role": "body_paragraph", "text": "Ethics continuation from prior section.", "render_default": True, "bbox": [80, 140, 500, 200], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "a1", "role": "section_heading", "text": "AUTHOR CONTRIBUTIONS", "render_default": True, "bbox": [80, 260, 420, 290], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "a2", "role": "body_paragraph", "text": "A.B. performed the analysis.", "render_default": True, "bbox": [80, 310, 500, 360], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "f1", "role": "backmatter_heading", "text": "FUNDING", "render_default": True, "bbox": [620, 110, 760, 140], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "f2", "role": "body_paragraph", "text": "Supported by grant 123.", "render_default": True, "bbox": [620, 150, 1100, 210], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "k1", "role": "backmatter_heading", "text": "ACKNOWLEDGMENTS", "render_default": True, "bbox": [620, 250, 900, 280], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "k2", "role": "body_paragraph", "text": "We thank the lab members.", "render_default": True, "bbox": [620, 290, 1100, 350], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "r1", "role": "reference_heading", "text": "REFERENCES", "render_default": True, "bbox": [80, 520, 300, 550], "page_width": 1200, "page_height": 1700},
        {"paper_id": "KEY", "page": 14, "block_id": "r2", "role": "reference_item", "text": "Smith J. Reference item.", "render_default": True, "bbox": [80, 570, 500, 620], "page_width": 1200, "page_height": 1700},
    ]

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=14,
    )

    funding_idx = md.index("**FUNDING**")
    funding_body_idx = md.index("Supported by grant 123.")
    ack_idx = md.index("**ACKNOWLEDGMENTS**")
    ack_body_idx = md.index("We thank the lab members.")
    refs_idx = md.index("## REFERENCES")

    assert funding_idx < funding_body_idx < ack_idx < ack_body_idx < refs_idx
