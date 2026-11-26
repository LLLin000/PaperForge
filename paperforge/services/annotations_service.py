"""Zotero-style non-destructive sidecar PDF annotation service.

Canonical per-paper storage lives in ``<workspace>/annotations.jsonl`` (with cropped
area figures in ``<workspace>/assets/<KEY>_ann_<id8>.jpg``). Source PDFs are NEVER
mutated so ``pdf_sha256`` and OCR/provenance hashes remain intact.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

from paperforge.config import paperforge_paths
from paperforge.core.io import read_json, read_jsonl
from paperforge.core.stat_cache import cached_sha256_hex
from paperforge.lineage import workspace_dir_for_key
from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path
from paperforge.memory.permanent import append_reading_note
from paperforge.memory.schema import ensure_schema
from paperforge.worker.asset_index import read_index

logger = logging.getLogger(__name__)

VALID_KINDS = frozenset(
    {
        "highlight",
        "underline",
        "strikethrough",
        "area",
        "note",
        "textbox",
        "shape",
        "ink",
        "margin",
    }
)
VALID_INTENTS = frozenset({"evidence", "question", "method", "quote", "general"})
VALID_COLORS = frozenset(
    {"yellow", "green", "blue", "pink", "red", "purple", "ink", "gray", "transparent"}
)
VALID_AUTHORS = frozenset({"user", "agent"})


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return cached_sha256_hex(path)


_COMPACT_MIN_LINES = 100


def _maybe_compact_jsonl_locked(jsonl_path: Path, state: dict[str, dict[str, Any]]) -> bool:
    """Compact tombstoned ``annotations.jsonl`` logs under ``FileLock`` once log bloat exceeds 2x active."""
    if not jsonl_path.exists():
        return False
    raw_lines = [line for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(raw_lines) < _COMPACT_MIN_LINES or len(raw_lines) <= 2 * len(state):
        return False
    ordered = sorted(
        state.values(),
        key=lambda rec: (str(rec.get("created_at") or ""), str(rec.get("ann_id") or "")),
    )
    payload = "".join(
        json.dumps({"op": "add", "ann_id": rec["ann_id"], "record": rec}, ensure_ascii=False) + "\n"
        for rec in ordered
        if rec.get("ann_id")
    )
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=jsonl_path.parent,
            prefix=".annotations.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, jsonl_path)
        return True
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _normalize_rect(raw: list[float] | tuple[float, ...]) -> list[float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError("Each rect must be [x0, y0, x1, y1]")
    x0, y0, x1, y1 = [max(0.0, min(1.0, float(v))) for v in raw]
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return [round(x0, 5), round(y0, 5), round(x1, 5), round(y1, 5)]


def _normalize_rects(rects: list[list[float]] | None) -> list[list[float]]:
    if not rects:
        return []
    return [_normalize_rect(r) for r in rects]


def _normalize_style(raw: dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("style must be a JSON object")
    out: dict[str, Any] = {}
    if "shape_type" in raw and raw["shape_type"] is not None:
        st = str(raw["shape_type"]).strip().lower()
        if st not in {"rect", "ellipse", "arrow", "line"}:
            raise ValueError(f"Unsupported shape_type {st!r}")
        out["shape_type"] = st
    for color_key in ("stroke_color", "fill_color"):
        if color_key in raw and raw[color_key] is not None:
            out[color_key] = str(raw[color_key]).strip()
    if "stroke_width" in raw and raw["stroke_width"] is not None:
        out["stroke_width"] = round(max(0.5, min(16.0, float(raw["stroke_width"]))), 2)
    if "font_size" in raw and raw["font_size"] is not None:
        out["font_size"] = int(max(8, min(48, round(float(raw["font_size"])))))
    if "opacity" in raw and raw["opacity"] is not None:
        out["opacity"] = round(max(0.05, min(1.0, float(raw["opacity"]))), 3)
    if "points" in raw and raw["points"] is not None:
        pts_raw = raw["points"]
        if not isinstance(pts_raw, list):
            raise ValueError("style.points must be a list of [x, y] pairs")
        norm_pts: list[list[float]] = []
        for pt in pts_raw:
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise ValueError("Each point in style.points must be [x, y]")
            px = round(max(0.0, min(1.0, float(pt[0]))), 5)
            py = round(max(0.0, min(1.0, float(pt[1]))), 5)
            norm_pts.append([px, py])
        out["points"] = norm_pts
    return out


def _resolve_pdf_from_item(
    vault: Path, paths: dict[str, Path], paper_key: str, item: dict[str, Any] | None
) -> tuple[Path | None, str, bool, str]:
    """Return ``(pdf_abs_path, pdf_vault_rel, is_vault_relative, raw_locator)``."""
    vault_root = vault.resolve()
    zotero_dir = paths.get("zotero_dir")
    zotero_resolved = zotero_dir.resolve() if zotero_dir else None

    candidates: list[str] = []
    if item:
        raw_pdf = str(item.get("pdf_path") or "").strip()
        if raw_pdf:
            candidates.append(raw_pdf)

    meta_path = paths["ocr"] / paper_key / "meta.json"
    if meta_path.exists():
        try:
            meta = read_json(meta_path)
            src_pdf = str(meta.get("source_pdf") or "").strip()
            if src_pdf:
                candidates.append(src_pdf)
        except Exception:
            pass

    for raw in candidates:
        locator = raw[2:-2] if raw.startswith("[[") and raw.endswith("]]") else raw
        resolved: Path | None = None
        if locator.startswith("storage:"):
            if zotero_resolved is not None:
                rel = locator[len("storage:") :].lstrip("/")
                cand = (zotero_resolved / "storage" / rel).resolve()
                if cand.is_relative_to(zotero_resolved):
                    resolved = cand
        else:
            p = Path(locator)
            cand = p.resolve() if p.is_absolute() else (vault_root / locator).resolve()
            if cand.is_relative_to(vault_root) or (
                zotero_resolved is not None and cand.is_relative_to(zotero_resolved)
            ):
                resolved = cand

        if resolved is not None and resolved.is_file() and resolved.suffix.lower() == ".pdf":
            is_rel = resolved.is_relative_to(vault_root)
            vault_rel = str(resolved.relative_to(vault_root)).replace("\\", "/") if is_rel else ""
            return resolved, vault_rel, is_rel, locator

    return None, "", False, ""


def _resolve_paper_location(
    vault: Path, paper_key: str
) -> tuple[dict[str, Any], Path]:
    """Resolve index metadata + workspace directory for *paper_key*."""
    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    idx = read_index(vault_root)
    items = idx.get("items", []) if isinstance(idx, dict) else (idx or [])
    matched = [it for it in items if isinstance(it, dict) and it.get("zotero_key") == paper_key]
    item = matched[0] if matched else {}

    ws_dir: Path | None = None
    if item.get("paper_root"):
        ws_dir = (vault_root / str(item["paper_root"]).rstrip("/")).resolve()
    else:
        ws_dir = workspace_dir_for_key(vault_root, paper_key)

    if ws_dir is None:
        if not item:
            raise ValueError(f"Unknown paper key: {paper_key}")
        domain = str(item.get("domain") or "General")
        ws_dir = paths["literature"] / domain / f"{paper_key} - {paper_key}"

    return item, ws_dir


def _annotations_file_for_workspace(ws_dir: Path) -> Path:
    return ws_dir / "annotations.jsonl"


def _replay_jsonl_events(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    """Replay append-only events (add/update/delete) into active annotation dict by ann_id."""
    if not jsonl_path.exists():
        return {}
    state: dict[str, dict[str, Any]] = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        op = ev.get("op", "add")
        ann_id = str(ev.get("ann_id") or "")
        if not ann_id:
            continue
        if op == "add":
            rec = dict(ev.get("record") or ev)
            rec.pop("op", None)
            state[ann_id] = rec
        elif op == "update":
            if ann_id in state:
                patch = dict(ev.get("patch") or {})
                state[ann_id].update(patch)
                if "updated_at" in ev:
                    state[ann_id]["updated_at"] = ev["updated_at"]
        elif op == "delete":
            state.pop(ann_id, None)
    return state


def read_active_annotations_for_workspace(ws_dir: Path) -> list[dict[str, Any]]:
    """Read active annotations from one workspace ``annotations.jsonl`` without PDF I/O."""
    jsonl_path = _annotations_file_for_workspace(ws_dir)
    if not jsonl_path.exists():
        return []
    lock = FileLock(str(jsonl_path) + ".lock", timeout=10)
    with lock:
        active = list(_replay_jsonl_events(jsonl_path).values())
    active.sort(
        key=lambda a: (
            int(a.get("page", 1) or 1),
            float((a.get("rects") or [[0, 0, 0, 0]])[0][1]),
            float((a.get("rects") or [[0, 0, 0, 0]])[0][0]),
            str(a.get("created_at") or ""),
        )
    )
    return active


def _tree_block_to_section_path(tree: dict[str, Any]) -> dict[str, str]:
    """Map block_id -> hierarchical section title path (e.g. 'Methods > Participants')."""
    mapping: dict[str, str] = {}

    def _walk(nodes: list[dict[str, Any]], ancestors: list[str]) -> None:
        for node in nodes:
            title = str(node.get("title") or node.get("section_title") or "").strip()
            trail = [*ancestors, title] if title else ancestors
            path_str = " > ".join(trail)
            if path_str:
                for bid in node.get("own_block_ids", []) or []:
                    mapping[str(bid)] = path_str
            _walk(node.get("children", []) or [], trail)
            if path_str:
                for bid in node.get("subtree_block_ids", []) or []:
                    mapping.setdefault(str(bid), path_str)

    _walk(tree.get("nodes", []) or [], [])
    return mapping


def _bbox_to_norm(bbox: list[float], pw: float, ph: float) -> list[float] | None:
    if not bbox or len(bbox) < 4:
        return None
    x0, y0, x1, y1 = [float(v) for v in bbox[:4]]
    if max(x0, y0, x1, y1) <= 1.0:
        return [x0, y0, x1, y1]
    if pw <= 0 or ph <= 0:
        return None
    return [x0 / pw, y0 / ph, x1 / pw, y1 / ph]


def _rect_iou_and_overlap(a: list[float], b: list[float]) -> tuple[float, float]:
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0, 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(1e-9, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(1e-9, (b[2] - b[0]) * (b[3] - b[1]))
    iou = inter / max(1e-9, area_a + area_b - inter)
    frac_a = inter / area_a
    return iou, frac_a


def _bind_ocr_structure(
    paths: dict[str, Path],
    paper_key: str,
    page: int,
    rects: list[list[float]],
    pdf_page_size: tuple[float, float] | None = None,
) -> dict[str, str]:
    """Bind annotation ``(page, rects)`` against V3 OCR blocks, tree, and figure inventory."""
    out = {"block_id": "", "section_path": "", "figure_id": ""}
    if not rects:
        return out
    ocr_dir = paths["ocr"] / paper_key
    if not ocr_dir.exists():
        return out

    structured_path = ocr_dir / "structure" / "blocks.structured.jsonl"
    tree_path = ocr_dir / "index" / "structure-tree.json"
    fig_path = ocr_dir / "structure" / "figure_inventory.json"

    block_to_section: dict[str, str] = {}
    if tree_path.exists():
        try:
            block_to_section = _tree_block_to_section_path(read_json(tree_path))
        except Exception:
            block_to_section = {}

    target = rects[0]
    default_pw, default_ph = pdf_page_size if pdf_page_size else (0.0, 0.0)
    page_blocks: list[dict[str, Any]] = []
    if structured_path.exists():
        try:
            for b in read_jsonl(structured_path):
                if int(b.get("page") or 0) == page:
                    page_blocks.append(b)
        except Exception:
            page_blocks = []

    best_score = -1.0
    best_block: dict[str, Any] | None = None
    inferred_pw = default_pw
    inferred_ph = default_ph
    for b in page_blocks:
        pw = float(b.get("page_width") or 0)
        ph = float(b.get("page_height") or 0)
        if pw > 0 and ph > 0:
            inferred_pw, inferred_ph = pw, ph
            break

    for b in page_blocks:
        pw = float(b.get("page_width") or inferred_pw or 0)
        ph = float(b.get("page_height") or inferred_ph or 0)
        norm = _bbox_to_norm(b.get("bbox") or [], pw, ph)
        if norm is None:
            continue
        iou, frac_a = _rect_iou_and_overlap(target, norm)
        score = frac_a * 2.0 + iou
        if score > 0 and score > best_score:
            best_score = score
            best_block = b

    if best_block is not None:
        bid = str(best_block.get("block_id") or "")
        out["block_id"] = bid
        out["section_path"] = (
            block_to_section.get(bid)
            or str(best_block.get("section_path") or best_block.get("section_title") or "")
        )

    if fig_path.exists():
        try:
            fig_inv = read_json(fig_path)
            best_fig_overlap = 0.0
            for fig in fig_inv.get("matched_figures", []) or []:
                if int(fig.get("page") or 0) != page:
                    continue
                bbox = fig.get("cluster_bbox")
                norm_fig = _bbox_to_norm(bbox or [], inferred_pw, inferred_ph)
                if norm_fig is None:
                    continue
                _, frac_a = _rect_iou_and_overlap(target, norm_fig)
                if frac_a > best_fig_overlap:
                    best_fig_overlap = frac_a
                    out["figure_id"] = str(fig.get("figure_id") or "")
            if not out["figure_id"] and out["block_id"]:
                for fig in fig_inv.get("matched_figures", []) or []:
                    if int(fig.get("page") or 0) != page:
                        continue
                    owned = {str(x) for x in (fig.get("associated_text_block_ids") or [])}
                    if out["block_id"] in owned or out["block_id"] == str(fig.get("caption_block_id") or ""):
                        out["figure_id"] = str(fig.get("figure_id") or "")
                        break
        except Exception:
            pass

    return out


def _sync_sqlite_annotation(vault: Path, record: dict[str, Any] | None, delete_id: str | None = None) -> None:
    """Best-effort sync into ``paperforge.db`` ``paper_annotations`` if the DB exists."""
    try:
        db_path = get_memory_db_path(vault)
    except FileNotFoundError:
        return
    if not db_path.exists():
        return
    with WriterLock(vault):
        conn = get_connection(db_path)
        try:
            ensure_schema(conn)
            if delete_id:
                conn.execute("DELETE FROM paper_annotations WHERE ann_id = ?", (delete_id,))
            elif record is not None:
                paper_row = conn.execute(
                    "SELECT 1 FROM papers WHERE zotero_key = ?",
                    (record["paper_id"],),
                ).fetchone()
                if paper_row is None:
                    return
                conn.execute(
                    """INSERT OR REPLACE INTO paper_annotations (
                        ann_id, paper_id, page, kind, color, intent, author, lens,
                        grounding_tier, exact_text, comment, section_path, block_id,
                        figure_id, rects_json, crop_asset_rel, embed_wikilink,
                        tags_json, style_json, pdf_sha256, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record["ann_id"],
                        record["paper_id"],
                        int(record["page"]),
                        record.get("kind", "highlight"),
                        record.get("color", "yellow"),
                        record.get("intent", "general"),
                        record.get("author", "user"),
                        record.get("lens", ""),
                        record.get("grounding_tier", "manual"),
                        record.get("exact_text", ""),
                        record.get("comment", ""),
                        record.get("section_path", ""),
                        record.get("block_id", ""),
                        record.get("figure_id", ""),
                        json.dumps(record.get("rects", [])),
                        record.get("crop_asset_rel", ""),
                        record.get("embed_wikilink", ""),
                        json.dumps(record.get("tags", []), ensure_ascii=False),
                        json.dumps(record.get("style") or {}, ensure_ascii=False),
                        record.get("pdf_sha256", ""),
                        record.get("created_at", ""),
                        record.get("updated_at", ""),
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def _attach_live_provenance(anns: list[dict[str, Any]], current_sha: str) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for ann in anns:
        copy = dict(ann)
        stored_sha = str(copy.get("pdf_sha256") or "")
        if not current_sha or not stored_sha:
            copy["provenance_status"] = "unknown"
        elif stored_sha == current_sha:
            copy["provenance_status"] = "verified"
        else:
            copy["provenance_status"] = "changed"
        enriched.append(copy)
    return enriched


def get_paper_pdf_context(vault: Path, paper_key: str) -> dict[str, Any]:
    """Return canonical PDF path info, SHA-256, page count, note path, and annotations."""
    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    item, ws_dir = _resolve_paper_location(vault_root, paper_key)
    pdf_abs, pdf_vault_rel, is_vault_rel, raw_locator = _resolve_pdf_from_item(
        vault_root, paths, paper_key, item
    )

    page_count = 0
    pdf_sha = ""
    if pdf_abs is not None and pdf_abs.exists():
        pdf_sha = _sha256_file(pdf_abs)
        import pymupdf

        with pymupdf.open(str(pdf_abs)) as doc:
            page_count = len(doc)

    anns = _attach_live_provenance(read_active_annotations_for_workspace(ws_dir), pdf_sha)
    ws_rel = (
        str(ws_dir.relative_to(vault_root)).replace("\\", "/")
        if ws_dir.resolve().is_relative_to(vault_root)
        else ""
    )
    note_rel = str(item.get("main_note_path") or item.get("note_path") or "")
    if not note_rel and ws_rel:
        note_rel = f"{ws_rel}/{paper_key}.md"

    return {
        "paper_id": paper_key,
        "title": str(item.get("title") or paper_key),
        "pdf_abs_path": str(pdf_abs) if pdf_abs else "",
        "pdf_vault_rel": pdf_vault_rel,
        "pdf_locator": raw_locator,
        "is_vault_relative": is_vault_rel,
        "pdf_sha256": pdf_sha,
        "page_count": page_count,
        "workspace_rel": ws_rel,
        "note_rel_path": note_rel,
        "annotations": anns,
    }


def list_annotations(vault: Path, paper_key: str) -> list[dict[str, Any]]:
    """Return all active annotations for *paper_key* with live provenance checks."""
    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    item, ws_dir = _resolve_paper_location(vault_root, paper_key)
    pdf_abs, _, _, _ = _resolve_pdf_from_item(vault_root, paths, paper_key, item)
    current_sha = _sha256_file(pdf_abs) if (pdf_abs and pdf_abs.exists()) else ""
    return _attach_live_provenance(read_active_annotations_for_workspace(ws_dir), current_sha)


def _bump_seq_safe(vault: Path, reason: str, key: str) -> None:
    try:
        from paperforge.services.state_signal import bump_state_seq

        bump_state_seq(vault, reason=reason, changed_keys=[key])
    except Exception:
        pass


def add_annotation(
    vault: Path,
    paper_key: str,
    *,
    page: int,
    rects: list[list[float]],
    kind: str = "highlight",
    color: str = "yellow",
    intent: str = "general",
    author: str = "user",
    lens: str = "",
    grounding_tier: str = "manual",
    exact_text: str = "",
    comment: str = "",
    tags: list[str] | None = None,
    style: dict[str, Any] | None = None,
    section_hint: str = "",
    figure_hint: str = "",
    batch_id: str = "",
) -> dict[str, Any]:
    """Create a non-destructive sidecar PDF annotation with optional area crop & OCR binding."""
    if not isinstance(page, int) or page < 1:
        raise ValueError("page must be an integer >= 1")
    if kind not in VALID_KINDS:
        raise ValueError(f"Unsupported kind {kind!r}; expected one of {sorted(VALID_KINDS)}")
    if intent not in VALID_INTENTS:
        raise ValueError(f"Unsupported intent {intent!r}; expected one of {sorted(VALID_INTENTS)}")
    if color not in VALID_COLORS:
        raise ValueError(f"Unsupported color {color!r}; expected one of {sorted(VALID_COLORS)}")
    if author not in VALID_AUTHORS:
        raise ValueError(f"Unsupported author {author!r}; expected one of {sorted(VALID_AUTHORS)}")

    norm_rects = _normalize_rects(rects)
    if not norm_rects:
        raise ValueError("rects must contain at least one [x0, y0, x1, y1] box")
    norm_style = _normalize_style(style)

    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    item, ws_dir = _resolve_paper_location(vault_root, paper_key)
    ws_dir.mkdir(parents=True, exist_ok=True)
    pdf_abs, _, _, _ = _resolve_pdf_from_item(vault_root, paths, paper_key, item)

    ann_id = f"ann_{secrets.token_hex(6)}"
    now = _utcnow_iso()
    pdf_sha = ""
    page_size: tuple[float, float] | None = None
    crop_asset_rel = ""
    embed_wikilink = ""

    if pdf_abs is not None and pdf_abs.exists():
        pdf_sha = _sha256_file(pdf_abs)
        import pymupdf

        with pymupdf.open(str(pdf_abs)) as doc:
            if page > len(doc):
                raise ValueError(f"page {page} exceeds PDF page count {len(doc)}")
            pdf_page = doc[page - 1]
            pr = pdf_page.rect
            page_size = (float(pr.width), float(pr.height))
            if kind == "area":
                r = norm_rects[0]
                clip = pymupdf.Rect(
                    pr.x0 + r[0] * pr.width,
                    pr.y0 + r[1] * pr.height,
                    pr.x0 + r[2] * pr.width,
                    pr.y0 + r[3] * pr.height,
                )
                assets_dir = ws_dir / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                img_name = f"{paper_key}_{ann_id[:12]}.jpg"
                img_path = assets_dir / img_name
                pix = pdf_page.get_pixmap(clip=clip, dpi=200)
                pix.save(str(img_path))
                crop_asset_rel = str(img_path.relative_to(vault_root)).replace("\\", "/")
                embed_wikilink = f"![[{img_name}]]"

    ocr_binding = _bind_ocr_structure(paths, paper_key, page, norm_rects, pdf_page_size=page_size)
    record: dict[str, Any] = {
        "ann_id": ann_id,
        "paper_id": paper_key,
        "page": page,
        "kind": kind,
        "color": color,
        "intent": intent,
        "author": author,
        "lens": str(lens or ""),
        "grounding_tier": str(grounding_tier or "manual"),
        "exact_text": exact_text,
        "comment": comment,
        "tags": list(tags or []),
        "rects": norm_rects,
        "style": norm_style,
        "section_path": ocr_binding["section_path"] or str(section_hint or ""),
        "block_id": ocr_binding["block_id"],
        "figure_id": ocr_binding["figure_id"] or str(figure_hint or ""),
        "crop_asset_rel": crop_asset_rel,
        "embed_wikilink": embed_wikilink,
        "pdf_sha256": pdf_sha,
        "created_at": now,
        "updated_at": now,
    }
    if batch_id:
        record["batch_id"] = str(batch_id)

    jsonl_path = _annotations_file_for_workspace(ws_dir)
    lock = FileLock(str(jsonl_path) + ".lock", timeout=10)
    with lock:
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"op": "add", "ann_id": ann_id, "record": record}, ensure_ascii=False) + "\n")

    _sync_sqlite_annotation(vault_root, record)
    _bump_seq_safe(vault_root, "annotations.add", paper_key)
    record["provenance_status"] = "verified" if pdf_sha else "unknown"
    return record


def update_annotation(
    vault: Path,
    paper_key: str,
    ann_id: str,
    *,
    color: str | None = None,
    intent: str | None = None,
    comment: str | None = None,
    tags: list[str] | None = None,
    style: dict[str, Any] | None = None,
    rects: list[list[float]] | None = None,
) -> dict[str, Any]:
    if color is not None and color not in VALID_COLORS:
        raise ValueError(f"Unsupported color {color!r}")
    if intent is not None and intent not in VALID_INTENTS:
        raise ValueError(f"Unsupported intent {intent!r}")
    norm_style = _normalize_style(style) if style is not None else None
    norm_rects = _normalize_rects(rects) if rects is not None else None
    if rects is not None and not norm_rects:
        raise ValueError("rects must contain at least one [x0, y0, x1, y1] box")

    vault_root = Path(vault).expanduser().resolve()
    _, ws_dir = _resolve_paper_location(vault_root, paper_key)
    jsonl_path = _annotations_file_for_workspace(ws_dir)
    patch: dict[str, Any] = {}
    if color is not None:
        patch["color"] = color
    if intent is not None:
        patch["intent"] = intent
    if comment is not None:
        patch["comment"] = comment
    if tags is not None:
        patch["tags"] = list(tags)
    if norm_rects is not None:
        patch["rects"] = norm_rects

    now = _utcnow_iso()
    lock = FileLock(str(jsonl_path) + ".lock", timeout=10)
    with lock:
        state = _replay_jsonl_events(jsonl_path)
        if ann_id not in state:
            raise ValueError(f"Annotation not found: {ann_id}")
        if norm_style is not None:
            merged_style = dict(state[ann_id].get("style") or {})
            merged_style.update(norm_style)
            patch["style"] = merged_style
        state[ann_id].update(patch)
        state[ann_id]["updated_at"] = now
        updated_rec = dict(state[ann_id])
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"op": "update", "ann_id": ann_id, "patch": patch, "updated_at": now},
                    ensure_ascii=False,
                )
                + "\n"
            )
        _maybe_compact_jsonl_locked(jsonl_path, state)

    _sync_sqlite_annotation(vault_root, updated_rec)
    _bump_seq_safe(vault_root, "annotations.update", paper_key)
    paths = paperforge_paths(vault_root)
    item, _ = _resolve_paper_location(vault_root, paper_key)
    pdf_abs, _, _, _ = _resolve_pdf_from_item(vault_root, paths, paper_key, item)
    current_sha = _sha256_file(pdf_abs) if (pdf_abs and pdf_abs.exists()) else ""
    return _attach_live_provenance([updated_rec], current_sha)[0]


def delete_annotation(vault: Path, paper_key: str, ann_id: str) -> dict[str, Any]:
    vault_root = Path(vault).expanduser().resolve()
    _, ws_dir = _resolve_paper_location(vault_root, paper_key)
    jsonl_path = _annotations_file_for_workspace(ws_dir)
    now = _utcnow_iso()
    lock = FileLock(str(jsonl_path) + ".lock", timeout=10)
    with lock:
        state = _replay_jsonl_events(jsonl_path)
        if ann_id not in state:
            raise ValueError(f"Annotation not found: {ann_id}")
        state.pop(ann_id, None)
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps({"op": "delete", "ann_id": ann_id, "updated_at": now}, ensure_ascii=False) + "\n"
            )
        _maybe_compact_jsonl_locked(jsonl_path, state)
    _sync_sqlite_annotation(vault_root, None, delete_id=ann_id)
    _bump_seq_safe(vault_root, "annotations.delete", paper_key)
    return {"deleted": True, "ann_id": ann_id, "paper_id": paper_key}


def agent_mark_annotation(
    vault: Path,
    paper_key: str,
    *,
    quote: str = "",
    figure_id: str = "",
    page_hint: int | None = None,
    section_hint: str = "",
    comment: str = "",
    color: str = "purple",
    lens: str = "skeleton",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Ground a verbatim quote or figure ID on the paper's PDF and save an ``author='agent'`` mark."""
    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    item, _ws_dir = _resolve_paper_location(vault_root, paper_key)
    pdf_abs, _, _, _ = _resolve_pdf_from_item(vault_root, paths, paper_key, item)
    if pdf_abs is None or not pdf_abs.exists():
        raise ValueError(f"Canonical PDF not found for {paper_key}")

    from paperforge.services.pdf_grounding import ground_target_in_pdf

    grounded = ground_target_in_pdf(
        vault_root,
        paper_key,
        pdf_abs,
        quote=quote,
        figure_id=figure_id,
        page_hint=page_hint,
        section_hint=section_hint,
    )
    lens_to_intent = {
        "skeleton": "evidence",
        "methods": "method",
        "critique": "question",
        "custom": "evidence",
    }
    intent = lens_to_intent.get(str(lens or "").strip().lower(), "general")
    return add_annotation(
        vault_root,
        paper_key,
        page=int(grounded["page"]),
        rects=grounded["rects"],
        kind=str(grounded["kind"]),
        color=color,
        intent=intent,
        author="agent",
        lens=str(lens or "skeleton"),
        grounding_tier=str(grounded["grounding_tier"]),
        exact_text=str(grounded["matched_text"]),
        comment=str(comment or ""),
        tags=tags,
        section_hint=str(grounded.get("section_path") or section_hint),
        figure_hint=str(grounded.get("figure_id") or figure_id),
    )


def _norm_for_dedup(text: str) -> str:
    import re

    cleaned = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", str(text or "").lower())
    return " ".join(cleaned.split())


def _is_paraphrase_comment(quote: str, comment: str) -> bool:
    from difflib import SequenceMatcher

    nq = _norm_for_dedup(quote)
    nc = _norm_for_dedup(comment)
    if not nq or len(nc) < 8:
        return False
    if nc in nq:
        return True
    return SequenceMatcher(None, nq, nc).ratio() >= 0.82


def agent_apply_annotations(
    vault: Path,
    paper_key: str,
    items: list[dict[str, Any]],
    *,
    lens: str = "skeleton",
    replace_lens: bool = False,
    max_items: int = 15,
    min_comment_chars: int = 8,
    batch_id: str | None = None,
) -> dict[str, Any]:
    """Batch-ground and apply AI review annotations with OCR, dedup, anti-paraphrase, and cap guardrails."""
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")

    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    item, ws_dir = _resolve_paper_location(vault_root, paper_key)
    pdf_abs, _, _, _ = _resolve_pdf_from_item(vault_root, paths, paper_key, item)
    if pdf_abs is None or not pdf_abs.exists():
        raise ValueError(f"Canonical PDF not found for {paper_key}")

    ocr_status = str(item.get("ocr_status") or "").strip().lower()
    ocr_dir = paths["ocr"] / paper_key
    has_ocr_artifacts = (ocr_dir / "fulltext.md").is_file() or (
        ocr_dir / "structure" / "blocks.structured.jsonl"
    ).is_file()
    if ocr_status != "done" and not has_ocr_artifacts:
        raise ValueError(
            f"Paper {paper_key} OCR is not ready (ocr_status={ocr_status or 'pending'}); run OCR before AI annotation."
        )

    default_lens = str(lens or "skeleton").strip().lower() or "skeleton"
    lens_default_colors = {
        "skeleton": "purple",
        "methods": "blue",
        "critique": "red",
        "custom": "yellow",
    }
    lens_to_intent = {
        "skeleton": "evidence",
        "methods": "method",
        "critique": "question",
        "custom": "evidence",
    }
    effective_max = max(1, min(int(max_items or 15), 25))
    resolved_batch_id = str(batch_id or f"batch_{secrets.token_hex(4)}")

    replaced_count = 0
    if replace_lens:
        clr = clear_agent_annotations(vault_root, paper_key, lens=default_lens)
        replaced_count = int(clr.get("deleted_count") or 0)

    active = read_active_annotations_for_workspace(ws_dir)

    from paperforge.services.pdf_grounding import ground_target_in_pdf

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    grounding_summary: dict[str, int] = {}

    for idx, entry in enumerate(items):
        if not isinstance(entry, dict):
            rejected.append({"index": idx, "reason": "invalid_item", "detail": "item must be an object"})
            continue
        if len(created) >= effective_max:
            rejected.append(
                {
                    "index": idx,
                    "reason": "batch_limit_exceeded",
                    "detail": f"Exceeded batch cap ({effective_max})",
                }
            )
            continue

        quote = str(entry.get("quote") or "").strip()
        figure_id = str(entry.get("figure_id") or "").strip()
        comment = str(entry.get("comment") or "").strip()
        item_lens = str(entry.get("lens") or default_lens).strip().lower() or default_lens
        default_color = lens_default_colors.get(item_lens, "purple")
        color = str(entry.get("color") or default_color).strip().lower() or default_color
        page_hint = entry.get("page_hint")
        if page_hint is not None:
            page_hint = int(page_hint)
        section_hint = str(entry.get("section_hint") or "").strip()
        tags = list(entry.get("tags") or [])

        if not quote and not figure_id:
            rejected.append({"index": idx, "reason": "missing_target", "detail": "Provide quote or figure_id"})
            continue
        if len(comment) < int(min_comment_chars):
            rejected.append(
                {
                    "index": idx,
                    "reason": "comment_too_short",
                    "detail": f"Comment must be at least {min_comment_chars} characters",
                }
            )
            continue
        if quote and _is_paraphrase_comment(quote, comment):
            rejected.append(
                {
                    "index": idx,
                    "reason": "comment_paraphrases_quote",
                    "detail": "Comment appears to paraphrase the quote instead of adding analytical insight",
                }
            )
            continue

        try:
            grounded = ground_target_in_pdf(
                vault_root,
                paper_key,
                pdf_abs,
                quote=quote,
                figure_id=figure_id,
                page_hint=page_hint,
                section_hint=section_hint,
            )
        except Exception as exc:  # noqa: BLE001
            rejected.append(
                {
                    "index": idx,
                    "reason": "grounding_failed",
                    "detail": str(exc),
                }
            )
            continue

        g_page = int(grounded["page"])
        g_rects = grounded["rects"]
        g_fig = str(grounded.get("figure_id") or figure_id or "").strip()
        g_text = str(grounded.get("matched_text") or "").strip()
        norm_g_text = _norm_for_dedup(g_text)

        dup_match: dict[str, Any] | None = None
        dup_reason = ""
        for ex in active:
            if int(ex.get("page") or 0) != g_page:
                continue
            if g_fig and ex.get("author") == "agent" and str(ex.get("figure_id") or "").strip() == g_fig:
                dup_match = ex
                dup_reason = "duplicate_figure"
                break
            ex_text = _norm_for_dedup(str(ex.get("exact_text") or ""))
            if norm_g_text and ex_text and norm_g_text == ex_text:
                dup_match = ex
                dup_reason = "duplicate_target"
                break
            ex_rects = ex.get("rects") or []
            if g_rects and ex_rects:
                hit_overlap = False
                for r1 in g_rects:
                    for r2 in ex_rects:
                        iou, _ = _rect_iou_and_overlap(r1, r2)
                        if iou >= 0.60:
                            hit_overlap = True
                            break
                    if hit_overlap:
                        break
                if hit_overlap:
                    dup_match = ex
                    dup_reason = "duplicate_target"
                    break

        if dup_match is not None:
            skipped.append(
                {
                    "index": idx,
                    "reason": dup_reason,
                    "existing_ann_id": dup_match.get("ann_id", ""),
                }
            )
            continue

        tier = str(grounded["grounding_tier"])
        rec = add_annotation(
            vault_root,
            paper_key,
            page=g_page,
            rects=g_rects,
            kind=str(grounded["kind"]),
            color=color,
            intent=lens_to_intent.get(item_lens, "general"),
            author="agent",
            lens=item_lens,
            grounding_tier=tier,
            exact_text=g_text,
            comment=comment,
            tags=tags,
            section_hint=str(grounded.get("section_path") or section_hint),
            figure_hint=g_fig,
            batch_id=resolved_batch_id,
        )
        active.append(rec)
        created.append(rec)
        grounding_summary[tier] = grounding_summary.get(tier, 0) + 1

    return {
        "paper_id": paper_key,
        "batch_id": resolved_batch_id,
        "lens": default_lens,
        "replaced_count": replaced_count,
        "created_count": len(created),
        "skipped_count": len(skipped),
        "rejected_count": len(rejected),
        "grounding_summary": grounding_summary,
        "created": created,
        "skipped": skipped,
        "rejected": rejected,
    }


def adopt_agent_annotation(vault: Path, paper_key: str, ann_id: str) -> dict[str, Any]:
    """Promote an ``author='agent'`` review mark into a user-owned annotation."""
    vault_root = Path(vault).expanduser().resolve()
    _, ws_dir = _resolve_paper_location(vault_root, paper_key)
    jsonl_path = _annotations_file_for_workspace(ws_dir)
    now = _utcnow_iso()
    lock = FileLock(str(jsonl_path) + ".lock", timeout=10)
    with lock:
        state = _replay_jsonl_events(jsonl_path)
        if ann_id not in state:
            raise ValueError(f"Annotation not found: {ann_id}")
        patch = {"author": "user"}
        state[ann_id].update(patch)
        state[ann_id]["updated_at"] = now
        updated_rec = dict(state[ann_id])
        with jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"op": "update", "ann_id": ann_id, "patch": patch, "updated_at": now},
                    ensure_ascii=False,
                )
                + "\n"
            )
        _maybe_compact_jsonl_locked(jsonl_path, state)
    _sync_sqlite_annotation(vault_root, updated_rec)
    _bump_seq_safe(vault_root, "annotations.adopt", paper_key)
    paths = paperforge_paths(vault_root)
    item, _ = _resolve_paper_location(vault_root, paper_key)
    pdf_abs, _, _, _ = _resolve_pdf_from_item(vault_root, paths, paper_key, item)
    current_sha = _sha256_file(pdf_abs) if (pdf_abs and pdf_abs.exists()) else ""
    return _attach_live_provenance([updated_rec], current_sha)[0]


def clear_agent_annotations(
    vault: Path,
    paper_key: str,
    *,
    lens: str = "",
) -> dict[str, Any]:
    """Delete ``author='agent'`` marks (optionally scoped by lens); preserves user highlights."""
    vault_root = Path(vault).expanduser().resolve()
    _, ws_dir = _resolve_paper_location(vault_root, paper_key)
    jsonl_path = _annotations_file_for_workspace(ws_dir)
    if not jsonl_path.exists():
        return {"paper_id": paper_key, "deleted_count": 0, "deleted_ids": []}
    now = _utcnow_iso()
    lens_filter = str(lens or "").strip()
    deleted_ids: list[str] = []
    lock = FileLock(str(jsonl_path) + ".lock", timeout=10)
    with lock:
        state = _replay_jsonl_events(jsonl_path)
        targets = [
            aid
            for aid, rec in state.items()
            if rec.get("author") == "agent"
            and (not lens_filter or str(rec.get("lens") or "") == lens_filter)
        ]
        if targets:
            with jsonl_path.open("a", encoding="utf-8") as fh:
                for aid in targets:
                    fh.write(
                        json.dumps({"op": "delete", "ann_id": aid, "updated_at": now}, ensure_ascii=False) + "\n"
                    )
                    state.pop(aid, None)
                    deleted_ids.append(aid)
            _maybe_compact_jsonl_locked(jsonl_path, state)
    for aid in deleted_ids:
        _sync_sqlite_annotation(vault_root, None, delete_id=aid)
    if deleted_ids:
        _bump_seq_safe(vault_root, "annotations.clear_agent", paper_key)
    return {"paper_id": paper_key, "deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}


def promote_to_reading_log(
    vault: Path,
    paper_key: str,
    ann_id: str,
    *,
    usage: str = "evidence",
    project: str = "",
) -> dict[str, Any]:
    """Promote one PDF annotation into a canonical hash-bound ``reading-log.jsonl`` entry."""
    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    item, ws_dir = _resolve_paper_location(vault_root, paper_key)
    active = {a["ann_id"]: a for a in read_active_annotations_for_workspace(ws_dir)}
    ann = active.get(ann_id)
    if ann is None:
        raise ValueError(f"Annotation not found: {ann_id}")

    pdf_abs, pdf_vault_rel, is_rel, raw_locator = _resolve_pdf_from_item(
        vault_root, paths, paper_key, item
    )
    excerpt = str(ann.get("exact_text") or "").strip()
    if not excerpt:
        excerpt = str(ann.get("comment") or "").strip() or (
            f"Area annotation on page {ann['page']} ({ann.get('embed_wikilink') or ann_id})"
        )
    section = str(ann.get("section_path") or "").strip() or f"Page {ann['page']}"

    source_payload: dict[str, Any] | None = None
    src_locator = (pdf_vault_rel if is_rel and pdf_vault_rel else "") or (
        str(pdf_abs) if pdf_abs else raw_locator
    )
    if src_locator:
        basis = "recorded"
        source_payload = {
            "path": src_locator.replace("\\", "/"),
            "physical_page": int(ann["page"]),
            "basis": basis,
        }

    res = append_reading_note(
        vault_root,
        paper_id=paper_key,
        section=section,
        excerpt=excerpt,
        usage=usage,
        context=str(ann.get("embed_wikilink") or ""),
        note=str(ann.get("comment") or ""),
        project=project,
        tags=list(ann.get("tags") or []),
        agent="pdf-annotator",
        source=source_payload,
    )
    if not res.get("ok"):
        raise ValueError(str(res.get("error") or "Failed to promote annotation to reading log"))
    return {
        "promoted": True,
        "ann_id": ann_id,
        "paper_id": paper_key,
        "reading_log_id": res["id"],
        "provenance": res.get("provenance", {}),
    }


def read_ocr_diagnostic_fulltext(
    vault: Path,
    paper_key: str,
    *,
    max_chars: int = 80000,
) -> dict[str, Any]:
    """Read internal OCR markdown for read-only diagnostic preview in OCR Workspace."""
    vault_root = Path(vault).expanduser().resolve()
    paths = paperforge_paths(vault_root)
    ft_name = "full" + "text.md"
    ft_path = paths["ocr"] / paper_key / ft_name
    if not ft_path.exists():
        raise ValueError(f"OCR markdown not found for {paper_key}")
    raw = ft_path.read_text(encoding="utf-8")
    total_chars = len(raw)
    total_lines = len(raw.splitlines())
    limit = max(1000, int(max_chars or 80000))
    truncated = total_chars > limit
    content = raw[:limit] if truncated else raw
    return {
        "paper_id": paper_key,
        "content": content,
        "truncated": truncated,
        "total_lines": total_lines,
        "total_chars": total_chars,
    }
