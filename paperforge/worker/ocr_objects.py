from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

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
    label = figure.get("display_label")
    if not label:
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
                import pymupdf
            except ImportError:
                return None

            try:
                page = self._doc[page_num - 1]
                rect = page.rect
                zoom_x = (page_width / rect.width) if page_width > 0 else 2.0
                zoom_y = (page_height / rect.height) if page_height > 0 else 2.0
                mat = pymupdf.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB, alpha=False)
                img = PILImage.frombytes("RGB", (pix.width, pix.height), pix.samples)
                self._images[page_num] = img
                return img
            except Exception:
                return None

@dataclass(frozen=True)
class CropResult:
    """Structured crop outcome; bool callers retain the old success contract."""

    success: bool
    stage: str
    reason: str

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "stage": self.stage,
            "reason": self.reason,
        }



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
    return_result: bool = False,
) -> bool | CropResult:
    """Crop an asset while retaining the legacy bool return by default.

    ``return_result=True`` is used by object materialization to persist the
    existing seam's failure stage/reason without changing crop behavior.
    """

    def finish(result: CropResult) -> bool | CropResult:
        return result if return_result else result.success

    try:
        numeric_bbox = tuple(int(value) for value in bbox[:4])
    except (TypeError, ValueError):
        return finish(CropResult(False, "input", "bbox_invalid"))
    if len(numeric_bbox) != 4 or numeric_bbox[2] <= numeric_bbox[0] or numeric_bbox[3] <= numeric_bbox[1]:
        return finish(CropResult(False, "input", "bbox_invalid"))

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
                crop = img.crop(numeric_bbox)
                dst.parent.mkdir(parents=True, exist_ok=True)
                crop.save(dst)
                return finish(CropResult(True, "materialize", "success"))
            except Exception:
                return finish(CropResult(False, "crop", "crop_write_failed"))
        # fall through if page rendering failed

    # ── 1b. Out-of-range page fallback ──
    # Rebuild mode renders from the PDF so it stays deterministic, but an OCR
    # page can exceed the PDF page count (a supplement replaced the main file).
    # In that case an existing cached page image is better evidence than a
    # silently missing asset.
    if not use_disk_page_cache and page_cache_dir is not None and not rotation_deg:
        cached_page_image = _find_cached_page_image(page_cache_dir, page_num)
        if cached_page_image is not None:
            try:
                from paperforge.worker.ocr import crop_block_asset
            except ImportError:
                return finish(CropResult(False, "crop", "crop_dependency_missing"))
            try:
                ok = crop_block_asset(cached_page_image, list(numeric_bbox), dst)
            except Exception:
                return finish(CropResult(False, "crop", "crop_failed"))
            return finish(
                CropResult(bool(ok), "materialize" if ok else "crop", "success" if ok else "crop_failed")
            )

    # ── 2. Disk page cache path (only when use_disk_page_cache=True) ──
    if use_disk_page_cache and page_cache_dir is not None and not rotation_deg:
        cached_page_image = _find_cached_page_image(page_cache_dir, page_num)
        if cached_page_image is not None:
            try:
                from paperforge.worker.ocr import crop_block_asset
            except ImportError:
                return finish(CropResult(False, "crop", "crop_dependency_missing"))
            try:
                ok = crop_block_asset(cached_page_image, list(numeric_bbox), dst)
            except Exception:
                return finish(CropResult(False, "crop", "crop_failed"))
            return finish(
                CropResult(bool(ok), "materialize" if ok else "crop", "success" if ok else "crop_failed")
            )

    # ── 3. Direct PDF clip + render fallback ──
    created_doc = None
    doc = pdf_doc
    if doc is None and pdf_doc_provider is not None:
        try:
            doc = pdf_doc_provider()
        except Exception:
            return finish(CropResult(False, "pdf_open", "pdf_provider_failed"))
        if doc is None:
            return finish(CropResult(False, "pdf_open", "pdf_not_available"))
    if doc is None:
        if pdf_path is None:
            return finish(CropResult(False, "pdf_open", "pdf_not_available"))
        if not pdf_path.exists():
            return finish(CropResult(False, "pdf_open", "pdf_not_found"))
        try:
            import pymupdf
        except ImportError:
            return finish(CropResult(False, "pdf_open", "pdf_dependency_missing"))
        try:
            created_doc = pymupdf.open(str(pdf_path))
        except Exception:
            return finish(CropResult(False, "pdf_open", "pdf_open_failed"))
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
                        return finish(CropResult(False, "crop", "crop_dependency_missing"))
                    try:
                        ok = crop_block_asset(cached_page_image, list(numeric_bbox), dst)
                    except Exception:
                        return finish(CropResult(False, "crop", "crop_failed"))
                    return finish(
                        CropResult(bool(ok), "materialize" if ok else "crop", "success" if ok else "crop_failed")
                    )
                try:
                    from paperforge.worker.ocr import crop_block_asset, render_pdf_page_cached
                except ImportError:
                    return finish(CropResult(False, "page_render", "page_render_dependency_missing"))
                try:
                    page_image_path = page_cache_dir / f"page_{page_num:03d}.jpg"
                    rendered = render_pdf_page_cached(
                        doc,
                        page_num,
                        target_width=page_width,
                        target_height=page_height,
                        destination=page_image_path,
                    )
                    if not rendered:
                        return finish(CropResult(False, "page_render", "page_render_failed"))
                    ok = crop_block_asset(rendered, list(numeric_bbox), dst)
                    return finish(
                        CropResult(bool(ok), "materialize" if ok else "crop", "success" if ok else "crop_failed")
                    )
                except Exception:
                    return finish(CropResult(False, "page_render", "page_render_failed"))

        try:
            import pymupdf
        except ImportError:
            return finish(CropResult(False, "crop", "crop_dependency_missing"))
        try:
            if page_num < 1 or page_num > len(doc):
                return finish(CropResult(False, "crop", "page_out_of_range"))
            page = doc[page_num - 1]
            pdf_rect = page.rect
            sx = max(1.0, page_width / pdf_rect.width) if page_width > 0 else 2.0
            sy = max(1.0, page_height / pdf_rect.height) if page_height > 0 else 2.0
            rect = pymupdf.Rect(
                numeric_bbox[0] / sx,
                numeric_bbox[1] / sy,
                numeric_bbox[2] / sx,
                numeric_bbox[3] / sy,
            )
            zoom = 4.0
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if rotation_deg:
                import io

                from PIL import Image as PILImage

                img = PILImage.open(io.BytesIO(pix.tobytes("png")))
                img = img.rotate(rotation_deg, expand=True, resample=PILImage.Resampling.LANCZOS)
                img.save(str(dst))
            else:
                pix.save(str(dst))
            return finish(CropResult(True, "materialize", "success"))
        except Exception:
            return finish(CropResult(False, "crop", "crop_failed"))
    finally:
        if created_doc is not None:
            doc.close()


def _coerce_crop_result(value: bool | CropResult) -> CropResult:
    if isinstance(value, CropResult):
        return value
    return CropResult(bool(value), "materialize" if value else "crop", "success" if value else "unknown")


def _materialization_record(
    *,
    kind: str,
    object_id: str,
    asset_path: str,
    render_path: str,
    pdf_path: Path | None,
    attempts: list[CropResult],
    no_attempt_reason: str,
) -> dict[str, Any]:
    result = attempts[-1] if attempts else CropResult(False, "input", no_attempt_reason)
    return {
        "object_id": object_id,
        "kind": kind,
        "status": "materialized" if result.success else "failed",
        "stage": result.stage,
        "reason": result.reason,
        "pdf_input": "available" if pdf_path is not None and pdf_path.is_file() else "missing",
        "asset_path": asset_path,
        "render_path": render_path,
        "attempts": [attempt.to_dict() for attempt in attempts],
    }


def _write_figure_object_task(
    data: dict[str, Any],
    *,
    pdf_path: Path | None,
    page_cache_dir: Path | None,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = False,
    asset_dir: Path,
    render_dir: Path,
) -> dict[str, Any]:
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
    attempts: list[CropResult] = []
    was_cropped = False

    def attempt(bbox: list[float]) -> bool:
        nonlocal was_cropped
        if not bbox or not all(value > 0 for value in bbox):
            return False
        result = _coerce_crop_result(
            _crop_asset_from_pdf(
                pdf_path,
                page,
                bbox,
                asset_path_abs,
                page_width=page_width,
                page_height=page_height,
                page_cache_dir=page_cache_dir,
                pdf_doc=None,
                pdf_doc_provider=None,
                rotation_deg=rotation_deg,
                page_render_context=page_render_context,
                use_disk_page_cache=use_disk_page_cache,
                return_result=True,
            )
        )
        attempts.append(result)
        was_cropped = result.success
        return was_cropped

    if not attempt(crop_bbox):
        for asset_info in data.get("matched_assets", []):
            if attempt(asset_info.get("bbox", [0, 0, 0, 0])):
                break

    md = render_figure_object_markdown({
        "figure_id": fig_id,
        "display_label": data.get("display_label"),
        "page": page,
        "caption": caption,
        "image_relpath": asset_path_rel,
        "confidence": data.get("confidence", 0.5),
        "was_cropped": was_cropped,
    })
    _write_object_markdown(md, render_dir / f"{fig_id}.md")
    return _materialization_record(
        kind="figure",
        object_id=fig_id,
        asset_path=asset_path_rel,
        render_path=f"render/figures/{fig_id}.md",
        pdf_path=pdf_path,
        attempts=attempts,
        no_attempt_reason="bbox_missing",
    )
def _write_table_object_task(
    data: dict[str, Any],
    *,
    pdf_path: Path | None,
    page_cache_dir: Path | None,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = False,
    asset_dir: Path,
    render_dir: Path,
) -> dict[str, Any]:
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
    attempts: list[CropResult] = []
    was_cropped = False

    if data.get("has_asset") and crop_bbox and all(value > 0 for value in crop_bbox):
        result = _coerce_crop_result(
            _crop_asset_from_pdf(
                pdf_path,
                page,
                crop_bbox,
                asset_path_abs,
                page_width=page_width,
                page_height=page_height,
                page_cache_dir=page_cache_dir,
                pdf_doc=None,
                pdf_doc_provider=None,
                rotation_deg=rotation_deg,
                page_render_context=page_render_context,
                use_disk_page_cache=use_disk_page_cache,
                return_result=True,
            )
        )
        attempts.append(result)
        was_cropped = result.success

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
    return _materialization_record(
        kind="table",
        object_id=tbl_id,
        asset_path=asset_path_rel,
        render_path=f"render/tables/{tbl_id}.md",
        pdf_path=pdf_path,
        attempts=attempts,
        no_attempt_reason="source_asset_unavailable",
    )


def _write_orphan_object_task(
    data: dict[str, Any],
    *,
    pdf_path: Path | None,
    page_cache_dir: Path | None,
    page_render_context: PageRenderContext | None = None,
    use_disk_page_cache: bool = False,
    asset_dir: Path,
    render_dir: Path,
) -> dict[str, Any]:
    """Extract crop and write markdown for one orphan object."""
    orphan_id = data["orphan_id"]
    page = data["page"]
    page_width = data["page_width"]
    page_height = data["page_height"]
    bbox = data["bbox"]
    asset_path_rel = data["asset_path_rel"]
    asset_path_abs = asset_dir / f"{orphan_id}.jpg"
    attempts: list[CropResult] = []

    if bbox and all(value > 0 for value in bbox):
        attempts.append(
            _coerce_crop_result(
                _crop_asset_from_pdf(
                    pdf_path,
                    page,
                    bbox,
                    asset_path_abs,
                    page_width=page_width,
                    page_height=page_height,
                    page_cache_dir=page_cache_dir,
                    pdf_doc=None,
                    pdf_doc_provider=None,
                    page_render_context=page_render_context,
                    use_disk_page_cache=use_disk_page_cache,
                    return_result=True,
                )
            )
        )

    md = render_figure_object_markdown({
        "figure_id": orphan_id,
        "page": page,
        "caption": "",
        "image_relpath": asset_path_rel,
        "confidence": 0.3,
    })
    _write_object_markdown(md, render_dir / f"{orphan_id}.md")
    return _materialization_record(
        kind="orphan",
        object_id=orphan_id,
        asset_path=asset_path_rel,
        render_path=f"render/figures/{orphan_id}.md",
        pdf_path=pdf_path,
        attempts=attempts,
        no_attempt_reason="bbox_missing",
    )

def _write_materialization_provenance(render_root: Path, records: list[dict[str, Any]]) -> None:
    status_counts: dict[str, int] = {}
    stage_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for record in records:
        for field, counts in (
            ("status", status_counts),
            ("stage", stage_counts),
            ("reason", reason_counts),
        ):
            value = str(record.get(field) or "unknown")
            counts[value] = counts.get(value, 0) + 1
    payload = {
        "schema_version": 1,
        "objects": sorted(records, key=lambda item: (item.get("kind", ""), item.get("object_id", ""))),
        "summary": {
            "objects": len(records),
            "status": status_counts,
            "stage": stage_counts,
            "reason": reason_counts,
        },
    }
    try:
        (render_root / "materialization.provenance.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        # Provenance is additive; preserve the existing render behavior if
        # the diagnostic sidecar cannot be written.
        pass



class MaterializationError(RuntimeError):
    """Materialization failed; the existing object artifacts are unchanged."""


class MaterializationCollisionError(MaterializationError):
    """Two objects would write the same path; nothing is written or removed."""


class MaterializationCommitError(MaterializationError):
    """The staged commit failed and the previous artifacts were restored."""


_MANAGED_ASSET_DIRS = ("figures", "tables", "orphans")
_MANAGED_RENDER_DIRS = ("figures", "tables")


def _journal_path(paper_root: Path) -> Path:
    return paper_root / ".materialization-journal.json"


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        import shutil

        with contextlib.suppress(OSError):
            shutil.rmtree(path)
    else:
        with contextlib.suppress(OSError):
            path.unlink()


def _recover_materialization_journal(paper_root: Path) -> None:
    """Restore the previous artifacts if a commit was interrupted.

    The journal is written before any target is touched. A target is either the
    old directory (backup missing), the new one (backup present) or missing
    (backup present); restoring every backup reverses the interrupted commit.
    """
    journal_path = _journal_path(paper_root)
    if not journal_path.is_file():
        return
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        with contextlib.suppress(OSError):
            journal_path.unlink()
        return
    status = str(journal.get("status") or "")
    stage_root = Path(str(journal.get("stage_root") or ""))
    backup_root = Path(str(journal.get("backup_root") or ""))
    if status == "committing":
        for entry in reversed(journal.get("targets") or []):
            target = Path(str(entry.get("target") or ""))
            backup = Path(str(entry.get("backup") or ""))
            if backup.exists():
                _remove_path(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                with contextlib.suppress(OSError):
                    backup.rename(target)
    with contextlib.suppress(OSError):
        journal_path.unlink()
    _remove_path(stage_root)
    _remove_path(backup_root)


def _commit_staged_objects(
    *,
    paper_root: Path,
    stage_root: Path,
    staged_targets: list[tuple[Path, Path]],
    provenance: tuple[Path, Path] | None,
) -> None:
    """Swap staged directories/files into place; roll back on any failure."""
    import uuid

    token = uuid.uuid4().hex[:12]
    backup_root = paper_root / f".materialization-backup-{token}"
    targets = [
        {"target": str(target), "backup": str(backup_root / str(index))}
        for index, (target, _staged) in enumerate(staged_targets)
    ]
    if provenance is not None:
        targets.append(
            {"target": str(provenance[0]), "backup": str(backup_root / "provenance")}
        )
    journal = _journal_path(paper_root)
    payload = {
        "schema_version": 1,
        "token": token,
        "status": "committing",
        "stage_root": str(stage_root),
        "backup_root": str(backup_root),
        "targets": targets,
    }
    paper_root.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir()
    _write_json_atomic(journal, payload)
    moved: list[tuple[Path, Path]] = []
    try:
        pairs = list(staged_targets)
        if provenance is not None:
            pairs.append(provenance)
        for index, (target, staged) in enumerate(pairs):
            backup = backup_root / (str(index) if index < len(staged_targets) else "provenance")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.rename(backup)
            moved.append((target, backup))
            if not staged.exists():
                raise FileNotFoundError(f"staged artifact missing: {staged}")
            staged.rename(target)
        payload["status"] = "committed"
        _write_json_atomic(journal, payload)
    except Exception as exc:  # noqa: BLE001 — roll back every swap
        for target, backup in reversed(moved):
            try:
                if target.exists():
                    _remove_path(target)
                if backup.exists():
                    backup.rename(target)
            except OSError:
                pass
        with contextlib.suppress(OSError):
            journal.unlink()
        _remove_path(stage_root)
        _remove_path(backup_root)
        raise MaterializationCommitError(f"materialization commit rolled back: {exc}") from exc
    with contextlib.suppress(OSError):
        journal.unlink()
    _remove_path(backup_root)
    _remove_path(stage_root)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _build_object_tasks(
    figure_inventory: dict[str, Any],
    table_inventory: dict[str, Any],
    page_dimensions_by_page: dict[int, tuple[int, int]],
    structured_blocks: list[dict] | None = None,
) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, Any]]]:
    """Build the task list without touching any file, extending figure crops to owned inner text."""
    structured_blocks = structured_blocks or []
    collisions: list[dict[str, Any]] = []
    tasks: list[tuple[str, dict[str, Any]]] = []
    scheduled_ids: set[str] = set()

    def _claim(object_id: str, paths: list[str], legend: Any) -> bool:
        if object_id in scheduled_ids:
            collisions.append(
                {
                    "type": "identity_collision",
                    "status": "HARD_FAILURE",
                    "figure_id": object_id,
                    "artifact_paths": paths,
                    "legend_block_id": legend,
                }
            )
            return False
        scheduled_ids.add(object_id)
        return True

    def _page_dims(page_num: int) -> tuple[int, int]:
        return page_dimensions_by_page.get(page_num, (0, 0))

    for i, match in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = str(match.get("figure_id") or f"figure_{i + 1:03d}")
        if not _claim(
            fig_id,
            [f"assets/figures/{fig_id}.jpg", f"render/figures/{fig_id}.md"],
            match.get("legend_block_id"),
        ):
            continue
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
        owned_text_bboxes = [
            bbox
            for block in structured_blocks
            if str(block.get("_object_owner_id") or "") == fig_id
            and block.get("_object_owner_family") == "figure"
            and block.get("_object_owner_role") == "inner_text"
            and int(block.get("page", 0) or 0) == int(page or 0)
            and len(bbox := block.get("bbox") or []) >= 4
            and all(value > 0 for value in bbox[:4])
        ]
        if owned_text_bboxes and len(crop_bbox) == 4 and all(value > 0 for value in crop_bbox):
            bboxes = [crop_bbox, *owned_text_bboxes]
            crop_bbox = [
                min(bbox[0] for bbox in bboxes),
                min(bbox[1] for bbox in bboxes),
                max(bbox[2] for bbox in bboxes),
                max(bbox[3] for bbox in bboxes),
            ]
        tasks.append(
            (
                "figure",
                {
                    "fig_id": fig_id,
                    "page": page,
                    "page_width": page_width,
                    "page_height": page_height,
                    "crop_bbox": crop_bbox,
                    "rotation_deg": rotation_deg,
                    "matched_assets": match.get("matched_assets", []),
                    "display_label": match.get("display_label"),
                    "caption": caption_text,
                    "asset_path_rel": f"assets/figures/{fig_id}.jpg",
                    "confidence": match.get("confidence", 0.5),
                },
            )
        )

    for i, cluster in enumerate(figure_inventory.get("unresolved_clusters", [])):
        cluster_id = str(cluster.get("cluster_id") or f"unresolved_cluster_{i + 1:03d}")
        if not _claim(
            cluster_id,
            [f"assets/figures/{cluster_id}.jpg", f"render/figures/{cluster_id}.md"],
            None,
        ):
            continue
        page = cluster.get("page", 0)
        page_width, page_height = _page_dims(page)
        tasks.append(
            (
                "figure",
                {
                    "fig_id": cluster_id,
                    "page": page,
                    "page_width": page_width,
                    "page_height": page_height,
                    "crop_bbox": cluster.get("cluster_bbox", [0, 0, 0, 0]),
                    "rotation_deg": 0,
                    "matched_assets": [],
                    "caption": "",
                    "asset_path_rel": f"assets/figures/{cluster_id}.jpg",
                    "confidence": 0.45,
                },
            )
        )

    orphan_index = 0

    def _add_orphan(asset: dict[str, Any]) -> None:
        nonlocal orphan_index
        orphan_index += 1
        orphan_id = f"orphan_{orphan_index:03d}"
        page = asset.get("page", 0)
        page_width, page_height = _page_dims(page)
        tasks.append(
            (
                "orphan",
                {
                    "orphan_id": orphan_id,
                    "page": page,
                    "page_width": page_width,
                    "page_height": page_height,
                    "bbox": asset.get("bbox", [0, 0, 0, 0]),
                    "asset_path_rel": f"assets/orphans/{orphan_id}.jpg",
                },
            )
        )

    for asset in figure_inventory.get("unmatched_assets", []):
        _add_orphan(asset)

    for i, table in enumerate(table_inventory.get("tables", [])):
        tbl_id = f"table_{i + 1:03d}"
        page = table.get("page", 0)
        page_width, page_height = _page_dims(page)
        crop_bbox = table.get("render_bbox") or table.get("asset_bbox", [0, 0, 0, 0])
        tasks.append(
            (
                "table",
                {
                    "tbl_id": tbl_id,
                    "page": page,
                    "page_width": page_width,
                    "page_height": page_height,
                    "crop_bbox": crop_bbox,
                    "rotation_deg": table.get("render_rotation_deg", 0) or 0,
                    "caption": table.get("caption_text", ""),
                    "has_asset": table.get("has_asset", False),
                    "asset_path_rel": f"assets/tables/{tbl_id}.jpg",
                    "formal_table_number": table.get("formal_table_number") or table.get("table_number"),
                    "note_texts": table.get("note_texts", []),
                    "note_match_reason": table.get("note_match_reason", ""),
                },
            )
        )

    for asset in table_inventory.get("unmatched_assets", []):
        _add_orphan(asset)

    return tasks, collisions


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
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Materialize figure/table objects transactionally.

    Collision or write failures abort before any target is replaced; staged
    outputs are committed only after the whole manifest validates. ``dry_run``
    returns the manifest without touching the filesystem.
    """
    figure_inventory = figure_inventory if isinstance(figure_inventory, dict) else {}
    table_inventory = table_inventory if isinstance(table_inventory, dict) else {}
    paper_root = asset_root.parent
    if not dry_run:
        _recover_materialization_journal(paper_root)

    page_dimensions_by_page = page_dimensions_by_page or {}
    tasks, collisions = _build_object_tasks(
        figure_inventory, table_inventory, page_dimensions_by_page, structured_blocks
    )
    if collisions:
        figure_inventory.setdefault("identity_collisions", []).extend(collisions)
        details = collisions[0]
        raise MaterializationCollisionError(
            f"duplicate object artifact path for {details['figure_id']}: {details['artifact_paths']}"
        )

    figure_ids = {str(data["fig_id"]) for task_type, data in tasks if task_type == "figure"}
    table_ids = {str(data["tbl_id"]) for task_type, data in tasks if task_type == "table"}
    orphan_ids = {str(data["orphan_id"]) for task_type, data in tasks if task_type == "orphan"}
    manifest = {
        "figures": sorted(figure_ids),
        "tables": sorted(table_ids),
        "orphans": sorted(orphan_ids),
        "assets": [str(asset_root / "figures" / f"{oid}.jpg") for oid in sorted(figure_ids)]
        + [str(asset_root / "tables" / f"{oid}.jpg") for oid in sorted(table_ids)]
        + [str(asset_root / "orphans" / f"{oid}.jpg") for oid in sorted(orphan_ids)],
        "render": [str(render_root / "figures" / f"{oid}.md") for oid in sorted(figure_ids | orphan_ids)]
        + [str(render_root / "tables" / f"{oid}.md") for oid in sorted(table_ids)],
    }
    all_targets = manifest["assets"] + manifest["render"]
    if len(set(all_targets)) != len(all_targets):
        raise MaterializationCollisionError("manifest contains duplicate target paths")
    if dry_run:
        return manifest

    stage_root = Path(tempfile.mkdtemp(prefix=".materialization-stage-", dir=paper_root))
    try:
        stage_assets = stage_root / "assets"
        stage_render = stage_root / "render"
        for name in _MANAGED_ASSET_DIRS:
            (stage_assets / name).mkdir(parents=True, exist_ok=True)
        for name in _MANAGED_RENDER_DIRS:
            (stage_render / name).mkdir(parents=True, exist_ok=True)
        page_cache_dir = asset_root.parent / "pages"
        if use_disk_page_cache:
            page_cache_dir.mkdir(parents=True, exist_ok=True)

        doc = None
        page_render_ctx = None
        if pdf_path and pdf_path.exists():
            try:
                import pymupdf

                doc = pymupdf.open(str(pdf_path))
                page_render_ctx = PageRenderContext(doc)
            except Exception:
                pass
        max_workers = min(2, os.cpu_count() or 4)
        records: list[dict[str, Any]] = []
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for task_type, data in tasks:
                    if task_type == "figure":
                        futures.append(
                            executor.submit(
                                _write_figure_object_task,
                                data,
                                pdf_path=pdf_path,
                                page_cache_dir=page_cache_dir,
                                page_render_context=page_render_ctx,
                                use_disk_page_cache=use_disk_page_cache,
                                asset_dir=stage_assets / "figures",
                                render_dir=stage_render / "figures",
                            )
                        )
                    elif task_type == "table":
                        futures.append(
                            executor.submit(
                                _write_table_object_task,
                                data,
                                pdf_path=pdf_path,
                                page_cache_dir=page_cache_dir,
                                page_render_context=page_render_ctx,
                                use_disk_page_cache=use_disk_page_cache,
                                asset_dir=stage_assets / "tables",
                                render_dir=stage_render / "tables",
                            )
                        )
                    elif task_type == "orphan":
                        futures.append(
                            executor.submit(
                                _write_orphan_object_task,
                                data,
                                pdf_path=pdf_path,
                                page_cache_dir=page_cache_dir,
                                page_render_context=page_render_ctx,
                                use_disk_page_cache=use_disk_page_cache,
                                asset_dir=stage_assets / "orphans",
                                render_dir=stage_render / "figures",
                            )
                        )
                for future in as_completed(futures):
                    record = future.result()
                    if isinstance(record, dict):
                        records.append(record)
        finally:
            if doc is not None:
                with contextlib.suppress(Exception):
                    doc.close()

        for staged in (stage_assets, stage_render):
            for path in staged.rglob("*"):
                if path.is_file() and path.stat().st_size == 0:
                    raise MaterializationError(f"staged artifact is empty: {path}")
        staged_render_ids = {path.stem for path in (stage_render / "figures").glob("*.md")} | {
            path.stem for path in (stage_render / "tables").glob("*.md")
        }
        missing_render = (figure_ids | table_ids | orphan_ids) - staged_render_ids
        if missing_render:
            raise MaterializationError(f"staged markdown missing for: {sorted(missing_render)}")

        _write_materialization_provenance(stage_render, records)
        provenance_stage = stage_render / "materialization.provenance.json"
        provenance_target = render_root / "materialization.provenance.json"

        staged_targets: list[tuple[Path, Path]] = [
            (asset_root / "figures", stage_assets / "figures"),
            (asset_root / "tables", stage_assets / "tables"),
            (asset_root / "orphans", stage_assets / "orphans"),
            (render_root / "figures", stage_render / "figures"),
            (render_root / "tables", stage_render / "tables"),
        ]
        _commit_staged_objects(
            paper_root=paper_root,
            stage_root=stage_root,
            staged_targets=staged_targets,
            provenance=(provenance_target, provenance_stage) if provenance_stage.is_file() else None,
        )
    except MaterializationError:
        _remove_path(stage_root)
        raise
    except Exception as exc:  # noqa: BLE001 — nothing was committed
        _remove_path(stage_root)
        raise MaterializationError(f"object materialization failed: {exc}") from exc
    return None
