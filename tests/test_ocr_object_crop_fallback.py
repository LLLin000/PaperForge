"""Rebuild crops fall back to the page cache when the PDF page is missing."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from paperforge.worker.ocr_objects import PageRenderContext, _crop_asset_from_pdf


class _NoPage(PageRenderContext):
    def __init__(self) -> None:
        pass

    def get_page_image(self, page_num, width, height):  # noqa: ANN001
        return None


def test_missing_pdf_page_uses_the_cached_page_image(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    Image.new("RGB", (200, 200), "white").save(pages / "page_012.png")
    dst = tmp_path / "assets" / "figure.jpg"

    result = _crop_asset_from_pdf(
        None,
        page_num=12,
        bbox=[10, 10, 90, 90],
        dst=dst,
        page_width=200,
        page_height=200,
        page_cache_dir=pages,
        page_render_context=_NoPage(),
        use_disk_page_cache=False,
        return_result=True,
    )

    assert result.success is True
    assert dst.exists()
    with Image.open(dst) as image:
        assert image.size == (80, 80)


def test_without_a_cache_the_failure_is_reported(tmp_path: Path) -> None:
    result = _crop_asset_from_pdf(
        None,
        page_num=12,
        bbox=[10, 10, 90, 90],
        dst=tmp_path / "x.jpg",
        page_width=200,
        page_height=200,
        page_cache_dir=None,
        page_render_context=_NoPage(),
        use_disk_page_cache=False,
        return_result=True,
    )
    assert result.success is False
