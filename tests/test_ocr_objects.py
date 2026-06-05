from __future__ import annotations



def test_figure_object_markdown_links_image_and_legend() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    md = render_figure_object_markdown({
        "figure_id": "figure_001",
        "page": 4,
        "caption": "Figure 1. Example.",
        "image_relpath": "assets/figures/figure_001.jpg",
        "confidence": 0.91,
    })

    assert "# Figure 1" in md
    assert "![](../../assets/figures/figure_001.jpg)" in md
    assert "Figure 1. Example." in md


def test_table_object_markdown_includes_image_and_caption() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown

    md = render_table_object_markdown({
        "table_id": "table_001",
        "page": 5,
        "caption": "Table 1. Results.",
        "image_relpath": "assets/tables/table_001.jpg",
        "confidence": 0.88,
    })

    assert "# Table 1" in md
    assert "![](../../assets/tables/table_001.jpg)" in md
    assert "Table 1. Results." in md


def test_orphan_object_markdown() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    md = render_figure_object_markdown({
        "figure_id": "orphan_001",
        "page": 6,
        "caption": "",
        "image_relpath": "assets/orphans/orphan_001.jpg",
        "confidence": 0.3,
    })

    assert "# Orphan Media" in md
    assert "![](../../assets/orphans/orphan_001.jpg)" in md


def test_stabilize_object_wikilink_uses_correct_relative_path() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    md = render_figure_object_markdown({
        "figure_id": "figure_001",
        "page": 5,
        "caption": "Figure 1. Results.",
        "image_relpath": "assets/figures/figure_001.jpg",
        "confidence": 0.9,
    })

    assert "![](../../assets/figures/figure_001.jpg)" in md
