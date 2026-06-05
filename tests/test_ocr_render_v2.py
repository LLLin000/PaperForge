from __future__ import annotations


def test_render_fulltext_uses_resolved_metadata_and_object_links(tmp_path) -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"page": 1, "block_id": "p1_b1", "role": "abstract_heading", "text": "Abstract", "render_default": True},
        {"page": 1, "block_id": "p1_b2", "role": "abstract_body", "text": "Background text.", "render_default": True},
        {"page": 2, "block_id": "p2_b1", "role": "section_heading", "text": "1 Introduction", "render_default": True},
        {"page": 2, "block_id": "p2_b2", "role": "body_paragraph", "text": "Intro body.", "render_default": True},
    ]
    resolved_metadata = {
        "title": {"value": "Paper Title"},
        "authors": {"value": ["Alice", "Bob"]},
        "journal": {"value": "Journal A"},
        "year": {"value": 2024},
        "doi": {"value": "10.1000/xyz"},
    }
    figure_inventory = {
        "matched_figures": [{"figure_id": "figure_001", "confidence": 0.91, "flags": []}],
    }
    table_inventory = {
        "tables": [{"table_id": "table_001", "has_asset": True}],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert "# Paper Title" in md
    assert "Authors:" in md
    assert "## 1 Introduction" in md or "### 1 Introduction" in md
    assert "![[figures/figure_001.md]]" in md or "![[render/figures/figure_001.md]]" in md
