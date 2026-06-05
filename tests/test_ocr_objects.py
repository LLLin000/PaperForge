from __future__ import annotations

from pathlib import Path



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
    assert "## Legend" in md
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
    assert "## Caption" in md
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


def test_crop_asset_uses_ocr_page_coordinates_when_dimensions_provided(tmp_path: Path) -> None:
    import fitz
    from PIL import Image

    from paperforge.worker.ocr_objects import _crop_asset_from_pdf

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.draw_rect(fitz.Rect(25, 25, 50, 50), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    dst = tmp_path / "crop.jpg"
    ok = _crop_asset_from_pdf(
        pdf_path,
        1,
        [50, 50, 100, 100],
        dst,
        page_width=600,
        page_height=800,
        page_cache_dir=tmp_path / "pages",
    )

    assert ok is True
    with Image.open(dst) as img:
        assert img.size == (50, 50)


def test_crop_asset_prefers_cached_page_image_when_available(tmp_path: Path) -> None:
    from PIL import Image

    from paperforge.worker.ocr_objects import _crop_asset_from_pdf

    page_cache_dir = tmp_path / "pages"
    page_cache_dir.mkdir()
    page_image = page_cache_dir / "page_001.jpg"
    Image.new("RGB", (600, 800), "white").save(page_image)

    dst = tmp_path / "crop.jpg"
    ok = _crop_asset_from_pdf(
        tmp_path / "missing.pdf",
        1,
        [50, 50, 100, 100],
        dst,
        page_cache_dir=page_cache_dir,
    )

    assert ok is True
    with Image.open(dst) as img:
        assert img.size == (50, 50)
