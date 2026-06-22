from __future__ import annotations

from pathlib import Path
from typing import Any


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


def test_render_figure_markdown_with_image_when_cropped() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    md = render_figure_object_markdown({
        "figure_id": "figure_001",
        "page": 4,
        "caption": "Figure 1. Example.",
        "image_relpath": "assets/figures/figure_001.jpg",
        "confidence": 0.91,
        "was_cropped": True,
    })

    assert "![](../../assets/figures/figure_001.jpg)" in md


def test_render_figure_markdown_without_image_when_not_cropped() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    md = render_figure_object_markdown({
        "figure_id": "figure_001",
        "page": 4,
        "caption": "Figure 1. Example.",
        "image_relpath": "assets/figures/figure_001.jpg",
        "confidence": 0.91,
        "was_cropped": False,
    })

    assert "![](" not in md
    assert "![](../../assets/figures/figure_001.jpg)" not in md


def test_legend_only_matched_figure_does_not_use_unmatched_assets(tmp_path: Path) -> None:
    from paperforge.worker.ocr_objects import extract_and_write_objects

    render_root = tmp_path / "render"
    asset_root = tmp_path / "assets"

    figure_inventory: dict[str, Any] = {
        "matched_figures": [
            {
                "text": "Figure 1. A legend-only figure.",
                "page": 3,
                "confidence": 0.85,
                "cluster_bbox": None,
                "matched_assets": [],
            }
        ],
        "unmatched_assets": [
            {"bbox": [100, 100, 200, 200], "page": 1},
            {"bbox": [300, 300, 400, 400], "page": 1},
        ],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 1,
        "unresolved_clusters": [],
    }

    extract_and_write_objects(
        pdf_path=None,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=asset_root,
        render_root=render_root,
    )

    render_files = sorted((render_root / "figures").glob("*.md"))
    assert len(render_files) == 3, (
        "One matched figure note + two orphan notes from unmatched_assets"
    )
    figure_note = render_root / "figures" / "figure_001.md"
    assert figure_note.exists()
    content = figure_note.read_text()
    assert "![](" not in content, (
        "Legend-only figure must not contain any image reference"
    )
    # Verify orphan notes still get image paths
    orphan_contents = (render_root / "figures" / "orphan_001.md").read_text()
    assert "![](../../assets/orphans/orphan_001.jpg)" in orphan_contents


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


def test_unresolved_cluster_object_emission(tmp_path: Path) -> None:
    from paperforge.worker.ocr_objects import extract_and_write_objects

    render_root = tmp_path / "render"
    asset_root = tmp_path / "assets"

    figure_inventory: dict[str, Any] = {
        "matched_figures": [],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 0,
        "unresolved_clusters": [
            {
                "cluster_id": "unresolved_cluster_001",
                "page": 9,
                "cluster_bbox": [363, 237, 1075, 1016],
                "media_block_ids": ["p9_b2", "p9_b3", "p9_b4", "p9_b5", "p9_b6", "p9_b7"],
            }
        ],
    }

    extract_and_write_objects(
        pdf_path=None,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=asset_root,
        render_root=render_root,
    )

    render_files = sorted((render_root / "figures").glob("*.md"))
    assert len(render_files) == 1, (
        "Unresolved cluster should produce exactly one object note"
    )
    content = render_files[0].read_text()
    assert "# Figure 4" not in content, (
        "Cluster without a valid legend must not be titled with a figure number"
    )
    assert "unresolved_cluster_001" in render_files[0].stem, (
        "Object note should be identified by its cluster ID"
    )
    assert "unresolved_cluster_001.jpg" in content, (
        "Markdown must reference the whole-cluster crop image, not individual panel crops"
    )
    assert (render_root / "figures" / "unresolved_cluster_001.md").exists()
    assert not (render_root / "figures" / "cluster_001.md").exists()


def test_held_figures_do_not_emit_object_notes(tmp_path: Path) -> None:
    from paperforge.worker.ocr_objects import extract_and_write_objects

    render_root = tmp_path / "render"
    asset_root = tmp_path / "assets"

    figure_inventory: dict[str, Any] = {
        "matched_figures": [],
        "held_figures": [
            {
                "figure_id": "held_figure_001",
                "legend_block_id": "p10_b1",
                "page": 10,
                "text": "Figure 1",
                "figure_number": 1,
                "hold_reason": "insufficient_legend_evidence",
            }
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 0,
        "unresolved_clusters": [],
    }

    extract_and_write_objects(
        pdf_path=None,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=asset_root,
        render_root=render_root,
    )

    render_files = sorted((render_root / "figures").glob("*.md"))
    assert render_files == []


def test_held_tables_do_not_emit_object_notes(tmp_path: Path) -> None:
    from paperforge.worker.ocr_objects import extract_and_write_objects

    render_root = tmp_path / "render"
    asset_root = tmp_path / "assets"

    table_inventory: dict[str, Any] = {
        "tables": [],
        "held_tables": [
            {
                "table_id": "held_table_001",
                "caption_block_id": "p12_b1",
                "page": 12,
                "caption_text": "Table 2.",
                "table_number": 2,
                "hold_reason": "insufficient_caption_evidence",
            }
        ],
        "unmatched_captions": [],
        "unmatched_assets": [],
        "official_table_count": 0,
    }

    extract_and_write_objects(
        pdf_path=None,
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        asset_root=asset_root,
        render_root=render_root,
    )

    render_files = sorted((render_root / "tables").glob("*.md"))
    assert render_files == []


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


def test_figure_legend_math_normalized() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown
    md = render_figure_object_markdown({
        "figure_id": "figure_001",
        "caption": "Expression of $ ^{7} $ mRNA",
        "page": 1,
        "was_cropped": True,
        "image_relpath": "figures/figure_001.jpg",
    })
    assert "$^{7}$" in md
    assert "Expression of" in md


def test_table_object_markdown_renders_owned_notes() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown

    md = render_table_object_markdown({
        "table_id": "table_001",
        "page": 5,
        "caption": "Table 1. Results.",
        "image_relpath": "assets/tables/table_001.jpg",
        "note_texts": ["* p < 0.05", "Data are mean \u00b1 SD."],
    })

    assert "## Notes" in md
    assert "* p < 0.05" in md
    assert "Data are mean \u00b1 SD." in md


def test_table_object_markdown_renders_note_band_texts_in_notes_section() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown

    md = render_table_object_markdown(
        {
            "table_id": "table_001",
            "page": 5,
            "caption": "Table 1. Results.",
            "image_relpath": "assets/tables/table_001.jpg",
            "note_texts": ["* p < 0.05", "Data are mean \u00b1 SD."],
            "note_match_reason": "note_band_geometry_match",
        }
    )

    assert "## Notes" in md
    assert "* p < 0.05" in md
    assert "Data are mean \u00b1 SD." in md


def test_table_caption_math_normalized() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown
    md = render_table_object_markdown({
        "table_id": "table_001",
        "formal_table_number": 1,
        "caption": "IC$ _{50} $ values ($ \\\\mu $M)",
        "image_relpath": "tables/table_001.jpg",
        "page": 1,
    })
    assert "$_{50}$" in md
    assert "$\\\\mu$M" in md


# === Phase 1: cache-first and shared-PDF guardrails ===


def test_crop_asset_uses_cached_page_without_opening_pdf(tmp_path: Path, monkeypatch) -> None:
    from PIL import Image

    from paperforge.worker.ocr_objects import _crop_asset_from_pdf

    page_cache_dir = tmp_path / "pages"
    page_cache_dir.mkdir()
    Image.new("RGB", (600, 800), "white").save(page_cache_dir / "page_001.jpg")

    called = {"count": 0}

    def _boom(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("fitz.open should not be called on cache hit")

    monkeypatch.setattr("fitz.open", _boom)

    dst = tmp_path / "crop.jpg"
    ok = _crop_asset_from_pdf(
        None,
        1,
        [50, 50, 100, 100],
        dst,
        page_cache_dir=page_cache_dir,
    )

    assert ok is True
    assert called["count"] == 0


def test_extract_objects_opens_pdf_once_across_multiple_cache_miss_pages(tmp_path: Path, monkeypatch) -> None:
    import fitz

    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for _ in range(3):
        page = doc.new_page(width=300, height=400)
        page.draw_rect(fitz.Rect(25, 25, 75, 75), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "text": "Figure 1.",
                "page": 1,
                "cluster_bbox": [50, 50, 150, 150],
                "matched_assets": [],
            },
            {
                "figure_id": "figure_002",
                "text": "Figure 2.",
                "page": 2,
                "cluster_bbox": [160, 50, 260, 150],
                "matched_assets": [],
            },
            {
                "figure_id": "figure_003",
                "text": "Figure 3.",
                "page": 3,
                "cluster_bbox": [80, 80, 200, 200],
                "matched_assets": [],
            },
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 3,
        "unresolved_clusters": [],
    }

    open_count = {"count": 0}
    real_open = fitz.open

    def _counting_open(*args, **kwargs):
        open_count["count"] += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr("fitz.open", _counting_open)

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800), 2: (600, 800), 3: (600, 800)},
    )

    assert open_count["count"] == 1


def test_extract_objects_renders_same_page_once_for_multiple_crops(tmp_path: Path, monkeypatch) -> None:
    import fitz

    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.draw_rect(fitz.Rect(25, 25, 75, 75), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    figure_inventory = {
        "matched_figures": [
            {"figure_id": "figure_001", "text": "Figure 1.", "page": 1, "cluster_bbox": [50, 50, 150, 150], "matched_assets": []},
            {"figure_id": "figure_002", "text": "Figure 2.", "page": 1, "cluster_bbox": [160, 50, 260, 150], "matched_assets": []},
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 2,
        "unresolved_clusters": [],
    }

    render_calls = {"count": 0}

    from paperforge.worker import ocr as ocr_module
    real_render = ocr_module.render_pdf_page_cached

    def _counting_render(*args, **kwargs):
        render_calls["count"] += 1
        return real_render(*args, **kwargs)

    monkeypatch.setattr(ocr_module, "render_pdf_page_cached", _counting_render)

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800)},
    )

    assert render_calls["count"] == 1


def test_extract_objects_cache_hit_does_not_eager_open_shared_pdf(tmp_path: Path, monkeypatch) -> None:
    import fitz
    from PIL import Image

    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.draw_rect(fitz.Rect(25, 25, 75, 75), color=(1, 0, 0), fill=(1, 0, 0))
    doc.save(pdf_path)
    doc.close()

    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    Image.new("RGB", (600, 800), "white").save(pages_dir / "page_001.jpg")

    def _boom(*args, **kwargs):
        raise AssertionError("fitz.open should not be called when page cache already exists")

    monkeypatch.setattr("fitz.open", _boom)

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "text": "Figure 1.",
                "page": 1,
                "cluster_bbox": [50, 50, 150, 150],
                "matched_assets": [],
            }
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 1,
        "unresolved_clusters": [],
    }

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800)},
    )

    assert (tmp_path / "assets" / "figures" / "figure_001.jpg").exists()


def test_extract_objects_pdf_open_failure_still_writes_markdown(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_objects import extract_and_write_objects

    pdf_path = tmp_path / "broken.pdf"
    pdf_path.touch()

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "text": "Figure 1. Example.",
                "page": 1,
                "cluster_bbox": [50, 50, 150, 150],
                "matched_assets": [],
            }
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 1,
        "unresolved_clusters": [],
    }

    def _boom(*args, **kwargs):
        raise RuntimeError("cannot open pdf")

    monkeypatch.setattr("fitz.open", _boom)

    extract_and_write_objects(
        pdf_path=pdf_path,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=tmp_path / "assets",
        render_root=tmp_path / "render",
        page_dimensions_by_page={1: (600, 800)},
    )

    note = tmp_path / "render" / "figures" / "figure_001.md"
    assert note.exists()


# === figure legend completeness integration (Task 8) ===


def test_figure_inventory_completeness_fields_present() -> None:
    """Completeness metadata is present even for empty inventory."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory([])
    c = inventory["figure_legend_completeness"]
    assert "total" in c
    assert "accounted_for" in c
    assert "gap_count" in c
    assert "details" in c


def test_extract_and_write_objects_with_held_figures_and_completeness(tmp_path: Path) -> None:
    """Completeness data coexists with held figures in object extraction."""
    from paperforge.worker.ocr_objects import extract_and_write_objects

    render_root = tmp_path / "render"
    asset_root = tmp_path / "assets"

    figure_inventory: dict[str, Any] = {
        "matched_figures": [],
        "held_figures": [
            {
                "figure_id": "held_figure_001",
                "legend_block_id": "p10_b1",
                "page": 10,
                "text": "Figure 1",
                "figure_number": 1,
                "hold_reason": "insufficient_legend_evidence",
            }
        ],
        "unmatched_assets": [],
        "rejected_legends": [],
        "figure_legends": [],
        "figure_assets": [],
        "official_figure_count": 0,
        "unresolved_clusters": [],
        "figure_legend_completeness": {
            "total": 1,
            "accounted_for": 1,
            "gap_count": 0,
            "details": [{"block_id": "p10_b1", "figure_number": 1, "status": "held", "page": 10}],
        },
    }

    extract_and_write_objects(
        pdf_path=None,
        figure_inventory=figure_inventory,
        table_inventory={"tables": [], "unmatched_assets": []},
        asset_root=asset_root,
        render_root=render_root,
    )

    render_files = sorted((render_root / "figures").glob("*.md"))
    assert render_files == []
