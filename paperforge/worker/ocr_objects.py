from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def render_figure_object_markdown(figure: dict[str, Any]) -> str:
    caption = figure.get("caption", "")
    image_relpath = figure.get("image_relpath", "")

    # Extract figure number for the title
    figure_id = figure.get("figure_id", "")
    if figure_id and not figure_id.startswith("orphan_"):
        m = re.search(r'\d+', figure_id)
        num = str(int(m.group())) if m else figure_id
        label = f"Figure {num}"
    else:
        label = "Orphan Media"

    parts = [f"# {label}", "", f"![](../../{image_relpath})", ""]
    if caption:
        parts.append("**Legend:**")
        parts.append(caption)
    if figure.get("page"):
        parts.append("")
        parts.append(f"*Page {figure['page']}*")
    parts.append("")
    parts.append("---")

    return "\n".join(parts)


def render_table_object_markdown(table: dict[str, Any]) -> str:
    caption = table.get("caption", "")
    image_relpath = table.get("image_relpath", "")

    table_id_raw = table.get("table_id", "unknown")
    m = re.search(r'\d+', table_id_raw)
    table_id = str(int(m.group())) if m else table_id_raw
    label = f"Table {table_id}"

    parts = [f"# {label}", "", f"![](../../{image_relpath})", ""]
    if caption:
        parts.append("**Legend:**")
        parts.append(caption)
    if table.get("page"):
        parts.append("")
        parts.append(f"*Page {table['page']}*")
    parts.append("")
    parts.append("---")

    return "\n".join(parts)


def _write_object_markdown(md: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(md.strip() + "\n", encoding="utf-8")


def _crop_asset_from_pdf(
    pdf_path: Path,
    page_num: int,
    bbox: list[float],
    dst: Path,
) -> bool:
    """Crop a region from a PDF page and save as JPEG.

    Args:
        pdf_path: Path to the PDF file.
        page_num: 1-based page number.
        bbox: [x1, y1, x2, y2] bounding box in PDF coordinates.
        dst: Output path for the JPEG file.

    Returns:
        True if crop succeeded, False otherwise.
    """
    try:
        import fitz
    except ImportError:
        return False

    if not pdf_path.exists():
        return False

    try:
        doc = fitz.open(str(pdf_path))
        page = doc[page_num - 1]
        rect = fitz.Rect(*bbox)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
        dst.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(dst))
        doc.close()
        return True
    except Exception:
        return False


def extract_and_write_objects(
    pdf_path: Path | None,
    figure_inventory: dict[str, Any],
    table_inventory: dict[str, Any],
    asset_root: Path,
    render_root: Path,
) -> None:
    """Extract figure/table asset crops from PDF and write object markdown.

    Args:
        pdf_path: Path to the source PDF (may be None).
        figure_inventory: The figure inventory dict.
        table_inventory: The table inventory dict.
        asset_root: Root directory for assets (e.g., <ocr_root>/assets/).
        render_root: Root directory for render objects (e.g., <ocr_root>/render/).
    """
    figures_asset_dir = asset_root / "figures"
    tables_asset_dir = asset_root / "tables"
    orphans_asset_dir = asset_root / "orphans"
    figures_render_dir = render_root / "figures"
    tables_render_dir = render_root / "tables"

    for d in (figures_asset_dir, tables_asset_dir, orphans_asset_dir,
              figures_render_dir, tables_render_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Process matched figures
    for i, match in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = f"figure_{i + 1:03d}"
        caption_text = match.get("text", "")
        page = match.get("page", 0)
        asset_path_rel = f"assets/figures/{fig_id}.jpg"
        asset_path_abs = figures_asset_dir / f"{fig_id}.jpg"

        was_cropped = False
        for asset_info in match.get("matched_assets", []):
            bbox = asset_info.get("bbox", [0, 0, 0, 0])
            if pdf_path and bbox and all(v > 0 for v in bbox):
                if _crop_asset_from_pdf(pdf_path, page, bbox, asset_path_abs):
                    was_cropped = True
                    break

        if not was_cropped:
            for asset in figure_inventory.get("unmatched_assets", []):
                bbox = asset.get("bbox", [0, 0, 0, 0])
                asset_page = asset.get("page", 0)
                if pdf_path and bbox and all(v > 0 for v in bbox):
                    if _crop_asset_from_pdf(pdf_path, asset_page, bbox, asset_path_abs):
                        was_cropped = True
                        break

        md = render_figure_object_markdown({
            "figure_id": fig_id,
            "page": page,
            "caption": caption_text,
            "image_relpath": asset_path_rel,
            "confidence": match.get("confidence", 0.5),
        })
        _write_object_markdown(md, figures_render_dir / f"{fig_id}.md")

    # Process unmatched assets as orphans
    orphan_count = 0
    for asset in figure_inventory.get("unmatched_assets", []):
        orphan_count += 1
        orphan_id = f"orphan_{orphan_count:03d}"
        bbox = asset.get("bbox", [0, 0, 0, 0])
        page = asset.get("page", 0)
        asset_path_rel = f"assets/orphans/{orphan_id}.jpg"
        asset_path_abs = orphans_asset_dir / f"{orphan_id}.jpg"

        was_cropped = False
        if pdf_path and bbox and all(v > 0 for v in bbox):
            was_cropped = _crop_asset_from_pdf(pdf_path, page, bbox, asset_path_abs)

        md = render_figure_object_markdown({
            "figure_id": orphan_id,
            "page": page,
            "caption": "",
            "image_relpath": asset_path_rel,
            "confidence": 0.3,
        })
        _write_object_markdown(md, figures_render_dir / f"{orphan_id}.md")

    # Process tables
    for i, table in enumerate(table_inventory.get("tables", [])):
        tbl_id = f"table_{i + 1:03d}"
        caption_text = table.get("caption_text", "")
        page = table.get("page", 0)
        asset_bbox = table.get("asset_bbox", [0, 0, 0, 0])
        asset_path_rel = f"assets/tables/{tbl_id}.jpg"
        asset_path_abs = tables_asset_dir / f"{tbl_id}.jpg"

        was_cropped = False
        if table.get("has_asset") and pdf_path and asset_bbox and all(v > 0 for v in asset_bbox):
            was_cropped = _crop_asset_from_pdf(pdf_path, page, asset_bbox, asset_path_abs)

        md = render_table_object_markdown({
            "table_id": tbl_id,
            "page": page,
            "caption": caption_text,
            "image_relpath": asset_path_rel,
            "confidence": 0.85 if was_cropped else 0.4,
        })
        _write_object_markdown(md, tables_render_dir / f"{tbl_id}.md")

    # Process unmatched table assets as orphans
    for asset in table_inventory.get("unmatched_assets", []):
        orphan_count += 1
        orphan_id = f"orphan_{orphan_count:03d}"
        bbox = asset.get("bbox", [0, 0, 0, 0])
        page = asset.get("page", 0)
        asset_path_rel = f"assets/orphans/{orphan_id}.jpg"
        asset_path_abs = orphans_asset_dir / f"{orphan_id}.jpg"

        if pdf_path and bbox and all(v > 0 for v in bbox):
            _crop_asset_from_pdf(pdf_path, page, bbox, asset_path_abs)

        md = render_figure_object_markdown({
            "figure_id": orphan_id,
            "page": page,
            "caption": "",
            "image_relpath": asset_path_rel,
            "confidence": 0.3,
        })
        _write_object_markdown(md, figures_render_dir / f"{orphan_id}.md")
