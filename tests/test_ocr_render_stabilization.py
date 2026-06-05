from __future__ import annotations


def test_stabilize_render_suppresses_frontmatter_noise() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "section_heading", "text": "OPEN ACCESS", "render_default": True},
        {"paper_id": "KEY001", "page": 1, "block_id": "b2", "role": "section_heading", "text": "CITATION", "render_default": True},
        {"paper_id": "KEY001", "page": 1, "block_id": "b3", "role": "body_paragraph", "text": "Real body text should render.", "render_default": True},
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
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "abstract_heading", "text": "Abstract", "render_default": True},
        {"paper_id": "KEY001", "page": 1, "block_id": "b2", "role": "abstract_body", "text": "This is the abstract text.", "render_default": True},
        {"paper_id": "KEY001", "page": 2, "block_id": "b3", "role": "section_heading", "text": "1 Introduction", "render_default": True},
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
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "body_paragraph", "text": "Body text.", "render_default": True},
        {"paper_id": "KEY001", "page": 2, "block_id": "b2", "role": "figure_caption", "text": "Figure 1. Results.", "render_default": True},
        {"paper_id": "KEY001", "page": 3, "block_id": "b3", "role": "section_heading", "text": "2 Discussion", "render_default": True},
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
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "body_paragraph",
         "text": "Expression $ ^{1} $ and $ ^{\\u2020} $ should be compact.", "render_default": True},
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
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "table_html",
         "text": "<table><tr><td>data</td></tr></table>", "render_default": True},
        {"paper_id": "KEY001", "page": 1, "block_id": "b2", "role": "body_paragraph",
         "text": "Real body text.", "render_default": True},
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
        json.dumps({"role": "paper_title", "text": "Test Paper"}) + "\n"
        + json.dumps({"role": "authors", "text": "Alice Smith, Bob Jones"}) + "\n"
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


def test_stabilize_reference_content_mapped() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    assignment = assign_block_role(
        block={"block_label": "reference_content", "block_content": "Smith J. et al. (2024) A study on...", "page": 20},
        page_blocks=[],
    )

    assert assignment.role == "reference_item"
    assert assignment.confidence >= 0.8
