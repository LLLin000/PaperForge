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
    pub_idx = md.index("## Publisher's note")
    smith_idx = md.index("Smith J.")
    jones_idx = md.index("Jones B.")

    assert smith_idx > pub_idx, "First reference item should appear under References, after backmatter"
    assert jones_idx > pub_idx, "Second reference item should appear under References, after backmatter"
    assert smith_idx > ref_idx and jones_idx > ref_idx, "Reference items should appear after References heading"


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
    assert "## Generative AI statement" in md
    assert "## Publisher's note" in md

    refs_idx = md.index("## References")
    gen_ai_idx = md.index("## Generative AI statement")
    pub_idx = md.index("## Publisher's note")
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


def test_normalize_ocr_math_text_delimiter_spacing() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text("$ ^{8,49} $") == "$^{8,49}$"
    assert normalize_ocr_math_text("$ \\\\mu $m") == "$\\\\mu$m"


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
    result = normalize_ocr_math_text("TGF-$\\\\beta$")
    assert "TGF-$\\\\beta$" in result


def test_normalize_ocr_math_text_display_math() -> None:
    from paperforge.worker.ocr_math import normalize_ocr_math_text
    assert normalize_ocr_math_text("$$ ... $$") == "$$...$$"
