from __future__ import annotations

import contextlib
import os
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_math import normalize_ocr_math_text


_RENDER_LOCKS: dict[tuple[str, int], threading.Lock] = {}
_RENDER_LOCKS_LOCK = threading.Lock()


def _get_render_lock(page_cache_dir: Path, page_num: int) -> threading.Lock:
    key = (str(page_cache_dir), page_num)
    with _RENDER_LOCKS_LOCK:
        if key not in _RENDER_LOCKS:
            _RENDER_LOCKS[key] = threading.Lock()
        return _RENDER_LOCKS[key]


def render_figure_object_markdown(figure: dict[str, Any]) -> str:
    caption = figure.get("caption", "")
    image_relpath = figure.get("image_relpath", "")

    # Extract figure number for the title
    figure_id = figure.get("figure_id", "")
    if figure_id.startswith("unresolved_cluster_") or figure_id.startswith("cluster_"):
        label = "Unresolved Figure Candidate"
    elif figure_id and not figure_id.startswith("orphan_"):
        m = re.search(r"\d+", figure_id)
        num = str(int(m.group())) if m else figure_id
        label = f"Figure {num}"
    else:
        label = "Orphan Media"

    was_cropped = figure.get("was_cropped", True)
    parts = [f"# {label}", ""]
    if was_cropped and image_relpath:
        parts.append(f"![](../../{image_relpath})")
    parts.append("")
    if caption:
        parts.append("## Legend")
        parts.append(normalize_ocr_math_text(caption))
    if figure.get("page"):
        parts.append("")
        parts.append(f"*Page {figure['page']}*")
    parts.append("")
    parts.append("---")

    return "\n".join(parts)


def render_table_object_markdown(table: dict[str, Any]) -> str:
    caption = table.get("caption", "")
    image_relpath = table.get("image_relpath", "")

    formal_num = table.get("formal_table_number")
    if formal_num is not None:
        label = f"Table {formal_num}"
    else:
        table_id_raw = table.get("table_id", "unknown")
        m = re.search(r"\d+", table_id_raw)
        table_id = str(int(m.group())) if m else table_id_raw
        label = f"Table {table_id}"

    parts = [f"# {label}", "", f"![](../../{image_relpath})", ""]
    if caption:
        parts.append("## Caption")
        parts.append(normalize_ocr_math_text(caption))
    note_texts = [normalize_ocr_math_text(t) for t in table.get("note_texts", []) if t]
    if note_texts:
        parts.append("")
        parts.append("## Notes")
        parts.extend(note_texts)
    if table.get("page"):
        parts.append("")
        parts.append(f"*Page {table['page']}*")
    parts.append("")
    parts.append("---")

    return "\n".join(parts)


def _write_object_markdown(md: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(md.strip() + "\n", encoding="utf-8")


def _find_cached_page_image(page_cache_dir: Path | None, page_num: int) -> Path | None:
    if page_cache_dir is None:
        return None
    for suffix in (".jpg", ".png"):
        candidate = page_cache_dir / f"page_{page_num:03d}{suffix}"
        if candidate.exists():
            return candidate
    return None




def _resolve_object_crop_pdf_path(
    source_pdf_path: Path | None,
    ocr_meta: dict,
) -> Path | None:
    """Resolve the PDF path for object crops.

    Priority:
        1. source_pdf_path (resolved by Phase 1 rebuild pipeline)
        2. ocr_meta['source_pdf'] (legacy fallback from full OCR run)
    """
    if source_pdf_path is not None and source_pdf_path.exists():
        return source_pdf_path
    src = ocr_meta.get("source_pdf")
    if src:
        candidate = Path(str(src))
        if candidate.exists():
            return candidate
    return None
class PageRenderContext:
    """In-memory page image cache for a single rebuild session.

    Each unique page is rendered at most once via get_pixmap, converted to
    a PIL Image, and reused across all crop tasks on that page. No full-page
    JPG is written to disk.

    Thread-safe for serialized page rendering (lock-guarded) and read-only
    PIL crop reuse across threads.
    """
    def __init__(self, pdf_doc):
        self._doc = pdf_doc
        self._images: dict[int, Image.Image] = {}
        self._lock = threading.Lock()

    def get_page_image(self, page_num: int, page_width: int, page_height: int):
        """Return a PIL Image for the given 1-indexed page number.

        Renders the page at the OCR/page dimensions on first access,
        returns cached image on subsequent calls.
        """
        from PIL import Image as PILImage

        cached = self._images.get(page_num)
        if cached is not None:
            return cached

        with self._lock:
            cached = self._images.get(page_num)
            if cached is not None:
                return cached

            if self._doc is None or page_num < 1 or page_num > len(self._doc):
                return None
            try:
                import fitz
            except ImportError:
                return None

            try:
                page = self._doc[page_num - 1]
                rect = page.rect
                zoom_x = (page_width / rect.width) if page_width > 0 else 2.0
                zoom_y = (page_height / rect.height) if page_height > 0 else 2.0
                mat = fitz.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
                img = PILImage.frombytes("RGB", (pix.width, pix.height), pix.samples)
                self._images[page_num] = img
                return img
            except Exception:
                return None


def _crop_asset_from_pdf(
    pdf_path: Path | None,
    page_num: int,
    bbox: list[float],
    dst: Path,
    *,
    page_width: int = 0,
    page_height: int = 0,
    page_cache_dir: Path | None = None,
    pdf_doc: Any | None = None,
    pdf_doc_provider: Callable[[], Any | None] | None = None,
    rotation_deg: int = 0,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = True,
) -> bool:
    """Crop asset from PDF, with in-memory or disk-cache or direct path.
    Priority:
        1. In-memory PageRenderContext (when dims valid, no rotation)
        2. Disk page cache (when use_disk_page_cache=True, has cache, no rotation)
        3. Direct PDF clip + render fallback
    """
    if dst.exists():
        with contextlib.suppress(Exception):
            dst.unlink()

    # ── 1. In-memory PageRenderContext path ──
    if (
        page_render_context is not None
        and page_width > 0
        and page_height > 0
        and not rotation_deg
    ):
        img = page_render_context.get_page_image(page_num, page_width, page_height)
        if img is not None:
            try:
                x1, y1, x2, y2 = (int(v) for v in bbox)
                if x2 <= x1 or y2 <= y1:
                    return False
                crop = img.crop((x1, y1, x2, y2))
                dst.parent.mkdir(parents=True, exist_ok=True)
                crop.save(dst)
                return True
            except Exception:
                return False
        # fall through if render failed

    # ── 2. Disk page cache path (only when use_disk_page_cache=True) ──
    if use_disk_page_cache and page_cache_dir is not None and not rotation_deg:
        cached_page_image = _find_cached_page_image(page_cache_dir, page_num)
        if cached_page_image is not None:
            try:
                from paperforge.worker.ocr import crop_block_asset
            except ImportError:
                return False
            ok = crop_block_asset(cached_page_image, [int(v) for v in bbox], dst)
            return ok

    # ── 3. Direct PDF clip + render fallback ──
    created_doc = None
    doc = pdf_doc
    if doc is None and pdf_doc_provider is not None:
        doc = pdf_doc_provider()
        if doc is None:
            return False
    if doc is None:
        if pdf_path is None or not pdf_path.exists():
            return False
        try:
            import fitz
        except ImportError:
            return False
        created_doc = fitz.open(str(pdf_path))
        doc = created_doc

    try:
        # Only render+save full page to disk cache when use_disk_page_cache
        if (
            use_disk_page_cache
            and page_width > 0
            and page_height > 0
            and page_cache_dir is not None
            and not rotation_deg
        ):
            lock = _get_render_lock(page_cache_dir, page_num)
            with lock:
                cached_page_image = _find_cached_page_image(page_cache_dir, page_num)
                if cached_page_image is not None:
                    try:
                        from paperforge.worker.ocr import crop_block_asset
                    except ImportError:
                        return False
                    ok = crop_block_asset(cached_page_image, [int(v) for v in bbox], dst)
                    return ok
                try:
                    from paperforge.worker.ocr import crop_block_asset, render_pdf_page_cached
                except ImportError:
                    return False
                try:
                    page_image_path = page_cache_dir / f"page_{page_num:03d}.jpg"
                    rendered = render_pdf_page_cached(
                        doc, page_num,
                        target_width=page_width, target_height=page_height,
                        destination=page_image_path,
                    )
                    if not rendered:
                        return False
                    ok = crop_block_asset(rendered, [int(v) for v in bbox], dst)
                    return ok
                except Exception:
                    return False

        try:
            import fitz
        except ImportError:
            return False
        try:
            page = doc[page_num - 1]
            pdf_rect = page.rect
            sx = max(1.0, page_width / pdf_rect.width) if page_width > 0 else 2.0
            sy = max(1.0, page_height / pdf_rect.height) if page_height > 0 else 2.0
            rect = fitz.Rect(bbox[0] / sx, bbox[1] / sy, bbox[2] / sx, bbox[3] / sy)
            zoom = 4.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if rotation_deg:
                from PIL import Image as PILImage
                import io
                img = PILImage.open(io.BytesIO(pix.tobytes("png")))
                img = img.rotate(rotation_deg, expand=True, resample=PILImage.Resampling.LANCZOS)
                img.save(str(dst))
            else:
                pix.save(str(dst))
            return True
        except Exception:
            return False
    finally:
        if created_doc is not None:
            doc.close()


def _write_figure_object_task(
    data: dict[str, Any],
    *,
    pdf_path: Path | None,
    page_cache_dir: Path | None,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = False,
    asset_dir: Path,
    render_dir: Path,
) -> None:
    """Extract crop and write markdown for one figure/cluster object."""
    fig_id = data["fig_id"]
    page = data["page"]
    page_width = data["page_width"]
    page_height = data["page_height"]
    crop_bbox = data["crop_bbox"]
    rotation_deg = data.get("rotation_deg", 0)
    caption = data.get("caption", "")
    asset_path_rel = data["asset_path_rel"]
    asset_path_abs = asset_dir / f"{fig_id}.jpg"

    was_cropped = False
    if crop_bbox and all(v > 0 for v in crop_bbox):
        was_cropped = _crop_asset_from_pdf(
            pdf_path, page, crop_bbox, asset_path_abs,
            page_width=page_width, page_height=page_height,
            page_cache_dir=page_cache_dir,
            pdf_doc=None, pdf_doc_provider=None,
            rotation_deg=rotation_deg,
            page_render_context=page_render_context,
            use_disk_page_cache=use_disk_page_cache,
        )

    if not was_cropped:
        for asset_info in data.get("matched_assets", []):
            bbox = asset_info.get("bbox", [0, 0, 0, 0])
            if pdf_path and bbox and all(v > 0 for v in bbox):
                if _crop_asset_from_pdf(
                    pdf_path, page, bbox, asset_path_abs,
                    page_width=page_width, page_height=page_height,
                    page_cache_dir=page_cache_dir,
                    pdf_doc=None, pdf_doc_provider=None,
                    rotation_deg=rotation_deg,
                    page_render_context=page_render_context,
                    use_disk_page_cache=use_disk_page_cache,
                ):
                    was_cropped = True
                    break

    md = render_figure_object_markdown({
        "figure_id": fig_id,
        "page": page,
        "caption": caption,
        "image_relpath": asset_path_rel,
        "confidence": data.get("confidence", 0.5),
        "was_cropped": was_cropped,
    })

    _write_object_markdown(md, render_dir / f"{fig_id}.md")
def _write_table_object_task(
    data: dict[str, Any],
    *,
    pdf_path: Path | None,
    page_cache_dir: Path | None,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = False,
    asset_dir: Path,
    render_dir: Path,
) -> None:
    """Extract crop and write markdown for one table object."""
    tbl_id = data["tbl_id"]
    page = data["page"]
    page_width = data["page_width"]
    page_height = data["page_height"]
    crop_bbox = data["crop_bbox"]
    rotation_deg = data.get("rotation_deg", 0)
    caption = data.get("caption", "")
    asset_path_rel = data["asset_path_rel"]
    asset_path_abs = asset_dir / f"{tbl_id}.jpg"

    was_cropped = False
    if data.get("has_asset") and pdf_path and crop_bbox and all(v > 0 for v in crop_bbox):
        was_cropped = _crop_asset_from_pdf(
            pdf_path, page, crop_bbox, asset_path_abs,
            page_width=page_width, page_height=page_height,
            page_cache_dir=page_cache_dir,
            pdf_doc=None, pdf_doc_provider=None,
            rotation_deg=rotation_deg,
            page_render_context=page_render_context,
            use_disk_page_cache=use_disk_page_cache,
        )

    md = render_table_object_markdown({
        "table_id": tbl_id,
        "page": page,
        "caption": caption,
        "image_relpath": asset_path_rel,
        "confidence": 0.85 if was_cropped else 0.4,
        "formal_table_number": data.get("formal_table_number"),
        "note_texts": data.get("note_texts", []),
        "note_match_reason": data.get("note_match_reason", ""),
    })
    _write_object_markdown(md, render_dir / f"{tbl_id}.md")


def _write_orphan_object_task(
    data: dict[str, Any],
    *,
    pdf_path: Path | None,
    page_cache_dir: Path | None,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = False,
    asset_dir: Path,
    render_dir: Path,
) -> None:
    """Extract crop and write markdown for one orphan object."""
    orphan_id = data["orphan_id"]
    page = data["page"]
    page_width = data["page_width"]
    page_height = data["page_height"]
    bbox = data["bbox"]
    asset_path_rel = data["asset_path_rel"]
    asset_path_abs = asset_dir / f"{orphan_id}.jpg"

    if pdf_path and bbox and all(v > 0 for v in bbox):
        _crop_asset_from_pdf(
            pdf_path, page, bbox, asset_path_abs,
            page_width=page_width, page_height=page_height,
            page_cache_dir=page_cache_dir,
            pdf_doc=None, pdf_doc_provider=None,
            page_render_context=page_render_context,
            use_disk_page_cache=use_disk_page_cache,
        )

    md = render_figure_object_markdown({
        "figure_id": orphan_id,
        "page": page,
        "caption": "",
        "image_relpath": asset_path_rel,
        "confidence": 0.3,
    })
    _write_object_markdown(md, render_dir / f"{orphan_id}.md")


def extract_and_write_objects(
    pdf_path: Path | None,
    figure_inventory: dict[str, Any],
    table_inventory: dict[str, Any],
    asset_root: Path,
    render_root: Path,
    *,
    page_dimensions_by_page: dict[int, tuple[int, int]] | None = None,
    structured_blocks: list[dict] | None = None,
    use_disk_page_cache: bool = True,
) -> None:
    """Extract figure/table asset crops from PDF and write object markdown.

    When use_disk_page_cache=False (rebuild mode), no pages/page_XXX.jpg
    files are created or read — all rendering goes through an in-memory
    PageRenderContext for determinism.
    """
    # Validation-first figure matching may retain held figures in inventory,
    # but object emission remains limited to matched figures and unresolved
    # media clusters until figure evidence is sufficient.
    figures_asset_dir = asset_root / "figures"
    tables_asset_dir = asset_root / "tables"
    orphans_asset_dir = asset_root / "orphans"
    figures_render_dir = render_root / "figures"
    tables_render_dir = render_root / "tables"
    page_cache_dir = (asset_root.parent / "pages") if use_disk_page_cache else None
    for d in (
        figures_asset_dir,
        tables_asset_dir,
        orphans_asset_dir,
        figures_render_dir,
        tables_render_dir,
        *(page_cache_dir is not None and [page_cache_dir] or []),
    ):
        d.mkdir(parents=True, exist_ok=True)

    for stale_dir, pattern in (
        (figures_asset_dir, "*.jpg"),
        (tables_asset_dir, "*.jpg"),
        (orphans_asset_dir, "*.jpg"),
        (figures_render_dir, "*.md"),
        (tables_render_dir, "*.md"),
    ):
        for stale in stale_dir.glob(pattern):
            with contextlib.suppress(Exception):
                stale.unlink()

    if page_dimensions_by_page is None:
        page_dimensions_by_page = {}

    def _page_dims(page_num: int) -> tuple[int, int]:
        return page_dimensions_by_page.get(page_num, (0, 0))

    # ---- Serial phase: build task list with stable IDs ----
    tasks: list[tuple[str, dict[str, Any]]] = []

    # Matched figures
    for i, match in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = match.get("figure_id", f"figure_{i + 1:03d}")
        caption_text = match.get("text", "")
        page = match.get("page", 0)
        page_width, page_height = _page_dims(page)
        rotation_deg = int(match.get("rotation_correction_deg", 0) or 0)

        crop_bbox = match.get("cluster_bbox") or [0, 0, 0, 0]
        if not (len(crop_bbox) == 4 and all(v > 0 for v in crop_bbox)):
            asset_bboxes = [
                a.get("bbox", [0, 0, 0, 0])
                for a in match.get("matched_assets", [])
                if len(a.get("bbox") or []) >= 4 and all(v > 0 for v in a.get("bbox", [0, 0, 0, 0]))
            ]
            if asset_bboxes:
                crop_bbox = [
                    min(b[0] for b in asset_bboxes),
                    min(b[1] for b in asset_bboxes),
                    max(b[2] for b in asset_bboxes),
                    max(b[3] for b in asset_bboxes),
                ]

        if structured_blocks and len(crop_bbox) == 4 and all(v > 0 for v in crop_bbox):
            for blk in structured_blocks:
                if blk.get("role") != "figure_inner_text":
                    continue
                if str(blk.get("_object_owner_id", "")) != str(fig_id):
                    continue
                if int(blk.get("page", 0) or 0) != int(page or 0):
                    continue
                bb = blk.get("bbox") or [0, 0, 0, 0]
                if len(bb) < 4 or not all(v > 0 for v in bb):
                    continue
                crop_bbox = [
                    min(crop_bbox[0], bb[0]),
                    min(crop_bbox[1], bb[1]),
                    max(crop_bbox[2], bb[2]),
                    max(crop_bbox[3], bb[3]),
                ]

        tasks.append((
            "figure",
            {
                "fig_id": fig_id,
                "page": page,
                "page_width": page_width,
                "page_height": page_height,
                "crop_bbox": crop_bbox,
                "rotation_deg": rotation_deg,
                "matched_assets": match.get("matched_assets", []),
                "caption": caption_text,
                "asset_path_rel": f"assets/figures/{fig_id}.jpg",
                "confidence": match.get("confidence", 0.5),
            },
        ))

    # Unresolved figure clusters
    for i, cluster in enumerate(figure_inventory.get("unresolved_clusters", [])):
        cluster_id = cluster.get("cluster_id") or f"unresolved_cluster_{i + 1:03d}"
        page = cluster.get("page", 0)
        page_width, page_height = _page_dims(page)
        bbox = cluster.get("cluster_bbox", [0, 0, 0, 0])

        tasks.append((
            "figure",
            {
                "fig_id": cluster_id,
                "page": page,
                "page_width": page_width,
                "page_height": page_height,
                "crop_bbox": bbox,
                "rotation_deg": 0,
                "matched_assets": [],
                "caption": "",
                "asset_path_rel": f"assets/figures/{cluster_id}.jpg",
                "confidence": 0.45,
            },
        ))

    # Pre-allocate orphan IDs (stable ordering across figure + table orphans)
    num_figure_orphans = len(figure_inventory.get("unmatched_assets", []))
    num_table_orphans = len(table_inventory.get("unmatched_assets", []))
    orphan_index = 0

    # Figure unmatched assets as orphans
    for asset in figure_inventory.get("unmatched_assets", []):
        orphan_index += 1
        orphan_id = f"orphan_{orphan_index:03d}"
        page = asset.get("page", 0)
        page_width, page_height = _page_dims(page)
        bbox = asset.get("bbox", [0, 0, 0, 0])

        tasks.append((
            "orphan",
            {
                "orphan_id": orphan_id,
                "page": page,
                "page_width": page_width,
                "page_height": page_height,
                "bbox": bbox,
                "asset_path_rel": f"assets/orphans/{orphan_id}.jpg",
            },
        ))

    # Tables
    for i, table in enumerate(table_inventory.get("tables", [])):
        tbl_id = f"table_{i + 1:03d}"
        caption_text = table.get("caption_text", "")
        page = table.get("page", 0)
        page_width, page_height = _page_dims(page)
        asset_bbox = table.get("asset_bbox", [0, 0, 0, 0])
        crop_bbox = table.get("render_bbox") or asset_bbox
        rotation_deg = table.get("render_rotation_deg", 0) or 0

        tasks.append((
            "table",
            {
                "tbl_id": tbl_id,
                "page": page,
                "page_width": page_width,
                "page_height": page_height,
                "crop_bbox": crop_bbox,
                "rotation_deg": rotation_deg,
                "caption": caption_text,
                "has_asset": table.get("has_asset", False),
                "asset_path_rel": f"assets/tables/{tbl_id}.jpg",
                "formal_table_number": table.get("formal_table_number") or table.get("table_number"),
                "note_texts": table.get("note_texts", []),
                "note_match_reason": table.get("note_match_reason", ""),
            },
        ))

    # Table unmatched assets as orphans (continue from figure orphan index)
    for asset in table_inventory.get("unmatched_assets", []):
        orphan_index += 1
        orphan_id = f"orphan_{orphan_index:03d}"
        page = asset.get("page", 0)
        page_width, page_height = _page_dims(page)
        bbox = asset.get("bbox", [0, 0, 0, 0])

        tasks.append((
            "orphan",
            {
                "orphan_id": orphan_id,
                "page": page,
                "page_width": page_width,
                "page_height": page_height,
                "bbox": bbox,
                "asset_path_rel": f"assets/orphans/{orphan_id}.jpg",
            },
        ))

    # ---- Parallel phase: dispatch crops and markdown writes ----
    from PIL import Image as PILImage

    doc = None
    page_render_ctx = None
    if pdf_path and pdf_path.exists():
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            page_render_ctx = PageRenderContext(doc)
        except Exception:
            pass

    max_workers = min(2, os.cpu_count() or 4)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for task_type, data in tasks:
                if task_type == "figure":
                    futures.append(executor.submit(
                        _write_figure_object_task,
                        data,
                        pdf_path=pdf_path,
                        page_cache_dir=page_cache_dir,
                        page_render_context=page_render_ctx,
                        use_disk_page_cache=use_disk_page_cache,
                        asset_dir=figures_asset_dir,
                        render_dir=figures_render_dir,
                    ))
                elif task_type == "table":
                    futures.append(executor.submit(
                        _write_table_object_task,
                        data,
                        pdf_path=pdf_path,
                        page_cache_dir=page_cache_dir,
                        page_render_context=page_render_ctx,
                        use_disk_page_cache=use_disk_page_cache,
                        asset_dir=tables_asset_dir,
                        render_dir=tables_render_dir,
                    ))
                elif task_type == "orphan":
                    futures.append(executor.submit(
                        _write_orphan_object_task,
                        data,
                        pdf_path=pdf_path,
                        page_cache_dir=page_cache_dir,
                        page_render_context=page_render_ctx,
                        use_disk_page_cache=use_disk_page_cache,
                        asset_dir=orphans_asset_dir,
                        render_dir=figures_render_dir,
                    ))

            for future in as_completed(futures):
                future.result()
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
