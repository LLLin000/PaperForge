"""3-stage error-tolerant PDF sentence & object grounding engine.

Maps a verbatim quote or object reference (``figure_id``/``table_id``) to exact
normalized PDF.js coordinates without letting bounding boxes drift across
pages or columns:
  1. Stage 1 — Block coarse lock in ``blocks.structured.jsonl`` (or native blocks)
  2. Stage 2a — In-block fuzzy folded character-stream alignment
  3. Stage 2b — Same-page cross-column / adjacent-block unique rescue
  4. Stage 3 — Honest left-margin bracket fallback for scanned/formula blocks
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path
from typing import Any

from paperforge.core.io import read_json, read_jsonl

_LATEX_WRAP_RE = re.compile(r"\$([^$]+)\$")
_WORD_RE = re.compile(r"[a-z0-9]{2,}")
_FIG_ID_RE = re.compile(r"^(?:fig(?:ure)?|f)[_\-\s.]*([a-z]?\d+[a-z]?)$", re.IGNORECASE)
_TBL_ID_RE = re.compile(r"^(?:tab(?:le)?|tbl|t)[_\-\s.]*([a-z]?\d+[a-z]?)$", re.IGNORECASE)


def _fold_char(ch: str) -> str:
    if ch in ("\u00ad", "\u200b", "\ufeff"):
        return ""
    s = unicodedata.normalize("NFKC", ch).lower()
    s = (
        s.replace("μ", "u")
        .replace("µ", "u")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
    )
    return "".join(c for c in s if c.isalnum())


def _fold_text(text: str) -> str:
    cleaned = _LATEX_WRAP_RE.sub(r"\1", str(text or ""))
    return "".join(_fold_char(c) for c in cleaned)


def _text_tokens(text: str) -> set[str]:
    norm = unicodedata.normalize("NFKC", _LATEX_WRAP_RE.sub(r"\1", str(text or ""))).lower()
    words = set(_WORD_RE.findall(norm))
    cjk = "".join(c for c in norm if "\u4e00" <= c <= "\u9fff")
    for i in range(max(0, len(cjk) - 1)):
        words.add(cjk[i : i + 2])
    if len(cjk) == 1:
        words.add(cjk)
    return words


def _clamp01(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def _page_rotation(page: Any) -> int:
    return int(getattr(page, "rotation", 0) or 0) % 360


def _to_visual_rect(rect: Any, page: Any) -> Any:
    """Map a PyMuPDF raw/unrotated CropBox rect into visual ``page.rect`` coordinates."""
    if _page_rotation(page) != 0:
        rot_mat = getattr(page, "rotation_matrix", None)
        if rot_mat is not None:
            return rect * rot_mat
    return rect


def _to_raw_rect(rect: Any, page: Any) -> Any:
    """Map a visual ``page.rect`` rect back into unrotated ``rawdict`` coordinates."""
    if _page_rotation(page) != 0:
        derot_mat = getattr(page, "derotation_matrix", None)
        if derot_mat is not None:
            return rect * derot_mat
    return rect


def _norm_rect_for_pdfjs(rect: Any, page: Any) -> list[float]:
    pr = page.rect
    w = max(1e-6, float(pr.width))
    h = max(1e-6, float(pr.height))
    x0 = _clamp01((float(rect.x0) - float(pr.x0)) / w)
    y0 = _clamp01((float(rect.y0) - float(pr.y0)) / h)
    x1 = _clamp01((float(rect.x1) - float(pr.x0)) / w)
    y1 = _clamp01((float(rect.y1) - float(pr.y0)) / h)
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]


class PdfGroundingContext:
    """Reusable per-batch PDF and OCR artifact cache for ``ground_target_in_pdf``."""

    def __init__(self, vault: Path, paper_key: str, pdf_path: Path) -> None:
        self.vault = Path(vault).expanduser().resolve()
        self.paper_key = paper_key
        self.pdf_path = Path(pdf_path)
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(self.vault)
        self.ocr_dir = paths["ocr"] / paper_key
        self._doc: Any = None
        self._blocks: list[dict[str, Any]] | None = None
        self._rawdicts: dict[int, dict[str, Any]] = {}
        self._page_chars: dict[int, list[tuple[str, Any, str]]] = {}
        self._native_blocks_by_page: dict[int, list[tuple[Any, ...]]] = {}
        self._inventories: dict[str, dict[str, Any]] | None = None

    @property
    def doc(self) -> Any:
        if self._doc is None:
            import pymupdf

            self._doc = pymupdf.open(str(self.pdf_path))
        return self._doc

    def close(self) -> None:
        if self._doc is not None:
            try:
                self._doc.close()
            finally:
                self._doc = None

    def __enter__(self) -> PdfGroundingContext:
        _ = self.doc
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def get_blocks(self) -> list[dict[str, Any]]:
        if self._blocks is None:
            self._blocks = _collect_candidate_blocks(self.ocr_dir, self.pdf_path, doc=self.doc)
        return self._blocks

    def get_rawdict(self, page_no: int) -> dict[str, Any]:
        if page_no not in self._rawdicts:
            self._rawdicts[page_no] = self.doc[page_no - 1].get_text("rawdict")
        return self._rawdicts[page_no]

    def get_page_chars(self, page_no: int) -> list[tuple[str, Any, str]]:
        if page_no not in self._page_chars:
            self._page_chars[page_no] = _extract_pdf_chars_in_rect(self.get_rawdict(page_no), None)
        return self._page_chars[page_no]

    def get_native_page_blocks(self, page_no: int) -> list[tuple[Any, ...]]:
        if page_no not in self._native_blocks_by_page:
            self._native_blocks_by_page[page_no] = list(self.doc[page_no - 1].get_text("blocks"))
        return self._native_blocks_by_page[page_no]

    def get_inventories(self) -> dict[str, dict[str, Any]]:
        if self._inventories is None:
            loaded: dict[str, dict[str, Any]] = {}
            for fname in ("figure_inventory.json", "table_inventory.json"):
                inv_path = self.ocr_dir / "structure" / fname
                if inv_path.exists():
                    try:
                        loaded[fname] = read_json(inv_path)
                    except Exception:
                        pass
            self._inventories = loaded
        return self._inventories


def _extract_pdf_chars_in_rect(
    rawdict: dict[str, Any],
    rect: Any | None,
) -> list[tuple[str, Any, str]]:
    return _extract_pdf_chars_in_rects(rawdict, [rect] if rect is not None else None)


def _extract_pdf_chars_in_rects(
    rawdict: dict[str, Any],
    rects: list[Any] | None,
) -> list[tuple[str, Any, str]]:
    import pymupdf

    chars_out: list[tuple[str, Any, str]] = []
    seen_coords: set[tuple[int, int, int, int]] = set()
    target_rects = rects if rects is not None else [None]

    for target in target_rects:
        for b_idx, blk in enumerate(rawdict.get("blocks", [])):
            if blk.get("type") != 0:
                continue
            for l_idx, ln in enumerate(blk.get("lines", [])):
                for s_idx, sp in enumerate(ln.get("spans", [])):
                    for c_idx, ch in enumerate(sp.get("chars", [])):
                        cb = ch.get("bbox")
                        if not cb or len(cb) < 4:
                            continue
                        r = pymupdf.Rect(cb)
                        if target is not None:
                            cx = (r.x0 + r.x1) / 2.0
                            cy = (r.y0 + r.y1) / 2.0
                            if not (target.x0 <= cx <= target.x1 and target.y0 <= cy <= target.y1):
                                continue
                        key = (b_idx, l_idx, s_idx, c_idx)
                        if key in seen_coords:
                            continue
                        seen_coords.add(key)
                        chars_out.append((_fold_char(str(ch.get("c") or "")), r, str(ch.get("c") or "")))
    return chars_out


def _align_folded_quote(
    pdf_chars: list[tuple[str, Any, str]],
    q_norm: str,
    *,
    require_unique: bool,
    min_fuzzy_score: float,
) -> tuple[list[tuple[str, Any, str]] | None, float]:
    stream: list[str] = []
    idx_map: list[int] = []
    for idx_c, (fc, _r, _raw) in enumerate(pdf_chars):
        for sub_c in fc:
            stream.append(sub_c)
            idx_map.append(idx_c)
    s_str = "".join(stream)
    if not s_str or not q_norm:
        return None, 0.0

    pos = s_str.find(q_norm)
    if pos != -1:
        if require_unique and s_str.find(q_norm, pos + 1) != -1:
            return None, 0.0
        c_start = idx_map[pos]
        c_end = idx_map[pos + len(q_norm) - 1]
        return pdf_chars[c_start : c_end + 1], 1.0

    if min_fuzzy_score > 1.0:
        return None, 0.0

    sm = difflib.SequenceMatcher(None, q_norm, s_str, autojunk=False)
    blocks = sm.get_matching_blocks()
    valid = [m for m in blocks if m.size >= 4]
    if not valid:
        matched_len = sum(m.size for m in blocks if m.size >= 3)
        return None, matched_len / max(1, len(q_norm))

    max_span = max(int(len(q_norm) * 1.45), len(q_norm) + 16)
    best_slice: list[Any] | None = None
    best_matched = 0
    best_span = 0
    for i in range(len(valid)):
        win_start = valid[i].b
        acc = 0
        for j in range(i, len(valid)):
            win_end = valid[j].b + valid[j].size - 1
            span_len = win_end - win_start + 1
            if span_len > max_span:
                break
            acc += valid[j].size
            if acc > best_matched or (acc == best_matched and span_len < best_span):
                best_matched = acc
                best_span = span_len
                best_slice = valid[i : j + 1]

    if not best_slice:
        matched_len = sum(m.size for m in blocks if m.size >= 3)
        return None, matched_len / max(1, len(q_norm))

    b_start = best_slice[0].b
    b_end = best_slice[-1].b + best_slice[-1].size - 1
    span_len = b_end - b_start + 1
    inner_matched = sum(
        m.size for m in blocks if m.size >= 3 and b_start <= m.b and (m.b + m.size - 1) <= b_end
    )
    score = inner_matched / max(1, len(q_norm))
    density = inner_matched / max(1, span_len)

    if span_len <= max_span and score >= min_fuzzy_score and density >= 0.55:
        if require_unique:
            for seg in (s_str[:b_start], s_str[b_end + 1 :]):
                if len(seg) >= max(4, int(len(q_norm) * 0.7)):
                    seg_sm = difflib.SequenceMatcher(None, q_norm, seg, autojunk=False)
                    seg_matched = sum(m.size for m in seg_sm.get_matching_blocks() if m.size >= 3)
                    if seg_matched / max(1, len(q_norm)) >= max(0.75, min_fuzzy_score * 0.92):
                        return None, 0.0
        c_start = idx_map[b_start]
        c_end = idx_map[b_end]
        if c_end >= c_start:
            return pdf_chars[c_start : c_end + 1], score
    return None, score


def _cluster_chars_to_rects(
    hit_chars: list[tuple[str, Any, str]],
    page: Any,
) -> tuple[list[list[float]], str]:
    import pymupdf

    lines: list[list[Any]] = []
    for fc, r, _raw in hit_chars:
        rw = float(r.width)
        rh = float(r.height)
        # Skip aberrant ultra-wide invisible whitespace chars that bloat highlight boxes
        if not fc and rw > max(18.0, rh * 2.5):
            continue
        cy = (float(r.y0) + float(r.y1)) / 2.0
        if lines:
            prev_cy, prev_rect = lines[-1]
            same_y = abs(prev_cy - cy) <= max(4.0, rh * 0.6)
            # Refuse to bridge two-column gutters or large horizontal jumps
            gap_limit = max(20.0, rh * 2.4)
            contiguous_x = (
                float(r.x0) - float(prev_rect.x1) <= gap_limit
                and float(r.x0) >= float(prev_rect.x0) - rh
            )
            if same_y and contiguous_x:
                lines[-1][1] |= r
                continue
        lines.append([cy, pymupdf.Rect(r)])
    rects = [_norm_rect_for_pdfjs(_to_visual_rect(lr, page), page) for _, lr in lines]
    recovered = "".join(c[2] for c in hit_chars).strip()
    return rects, recovered


def _rects_look_distorted(
    rects: list[list[float]],
    char_count: int,
    *,
    page: Any | None = None,
) -> bool:
    """Detect degenerate PDF text layers where a highlight stretches implausibly wide or tall."""
    if not rects:
        return True
    rotated_90 = (_page_rotation(page) % 180 == 90) if page is not None else False
    for x0, y0, x1, y1 in rects:
        w = x1 - x0
        h = y1 - y0
        thickness = w if rotated_90 else h
        span = h if rotated_90 else w
        if thickness > 0.14 or (span > 0.86 and char_count < 18):
            return True
    return False


def _parse_object_id(figure_id: str) -> tuple[str, str] | None:
    raw = figure_id.strip()
    m_fig = _FIG_ID_RE.match(raw)
    if m_fig:
        num = re.sub(r"^0+(?=\d)", "", m_fig.group(1).lower())
        return ("figure", num)
    m_tbl = _TBL_ID_RE.match(raw)
    if m_tbl:
        num = re.sub(r"^0+(?=\d)", "", m_tbl.group(1).lower())
        return ("table", num)
    return None


def _resolve_native_caption_object(
    doc: Any,
    figure_id: str,
    *,
    page_hint: int | None = None,
    ctx: PdfGroundingContext | None = None,
) -> dict[str, Any] | None:
    """Search native PyMuPDF text blocks for ``Figure N`` / ``Fig. N`` / ``Table N`` captions."""
    import pymupdf

    parsed = _parse_object_id(figure_id)
    if parsed is None:
        return None
    obj_kind, num = parsed
    num_pat = rf"0*{re.escape(num)}"
    if obj_kind == "figure":
        prefix = r"(?:figure|fig\.?)"
    else:
        prefix = r"(?:table|tbl\.?)"

    re_tier1 = re.compile(rf"^\s*{prefix}\s*{num_pat}\b\s*[:.\-–—|]", re.IGNORECASE)
    re_tier2 = re.compile(
        rf"(?im)^\s*{prefix}\s*{num_pat}\b(?:\s*[:.\-–—|]|\s+[A-Z0-9(\[]|\s*$)"
    )
    re_tier3 = re.compile(rf"(?im)^\s*{prefix}\s*{num_pat}\b")

    best: tuple[float, int, Any, str] | None = None  # (score, page_no, raw_blk, text)
    for page_idx in range(len(doc)):
        page_no = page_idx + 1
        blks = (
            ctx.get_native_page_blocks(page_no)
            if ctx is not None
            else list(doc[page_idx].get_text("blocks"))
        )
        for blk in blks:
            if len(blk) < 5:
                continue
            if len(blk) >= 7 and int(blk[6] or 0) != 0:
                continue
            txt = str(blk[4] or "").strip()
            if not txt:
                continue
            if re_tier1.match(txt):
                score = 3.0
            elif re_tier2.search(txt):
                score = 2.0
            elif re_tier3.search(txt) and len(txt) <= 450:
                score = 1.0
            else:
                continue
            if page_hint is not None and page_no == int(page_hint):
                score += 0.25
            if best is None or score > best[0]:
                best = (score, page_no, blk, txt)

    if best is None:
        return None

    cap_score, page_no, cap_blk, cap_txt = best
    page = doc[page_no - 1]
    cap_raw = pymupdf.Rect(cap_blk[:4])
    raw_bounds = _to_raw_rect(page.rect, page)
    raw_w = max(1e-6, float(raw_bounds.width))
    raw_h = max(1e-6, float(raw_bounds.height))

    # Collect image blocks and vector drawings in raw (unrotated) space to expand
    # the caption bbox to encompass an immediately adjacent figure/table graphic.
    graphic_rects: list[Any] = []
    try:
        rawdict = ctx.get_rawdict(page_no) if ctx is not None else page.get_text("rawdict")
        for b in rawdict.get("blocks", []):
            if b.get("type") == 1 and b.get("bbox") and len(b["bbox"]) >= 4:
                graphic_rects.append(pymupdf.Rect(b["bbox"]))
    except Exception:
        pass
    try:
        for d in page.get_drawings():
            dr = d.get("rect")
            if dr is not None:
                graphic_rects.append(pymupdf.Rect(dr))
    except Exception:
        pass

    # Collect other text block rects on the matched page (NOT the last loop page)
    # so we never merge a graphic across an intervening text block.
    page_blks = (
        ctx.get_native_page_blocks(page_no)
        if ctx is not None
        else list(page.get_text("blocks"))
    )
    other_text_rects: list[Any] = []
    for ob in page_blks:
        if len(ob) < 5 or (len(ob) >= 7 and int(ob[6] or 0) != 0):
            continue
        if ob is cap_blk or not str(ob[4] or "").strip():
            continue
        or_rect = pymupdf.Rect(ob[:4])
        if or_rect != cap_raw:
            other_text_rects.append(or_rect)

    def _has_intervening_text(gr_rect: Any) -> bool:
        y_top = min(float(gr_rect.y1), float(cap_raw.y1))
        y_bot = max(float(gr_rect.y0), float(cap_raw.y0))
        if y_bot <= y_top:
            return False
        x_left = min(float(gr_rect.x0), float(cap_raw.x0))
        x_right = max(float(gr_rect.x1), float(cap_raw.x1))
        for tr in other_text_rects:
            if float(tr.y0) >= y_top - 4.0 and float(tr.y1) <= y_bot + 4.0:
                if min(float(tr.x1), x_right) > max(float(tr.x0), x_left):
                    return True
        return False

    above_graphic: Any = None
    below_graphic: Any = None
    max_gap = min(raw_h * 0.15, 90.0)
    for gr in graphic_rects:
        gw = float(gr.width)
        gh = float(gr.height)
        if gw < 18.0 or gh < 18.0:
            continue
        if gw > raw_w * 0.92 and gh > raw_h * 0.92:
            continue
        # Must overlap horizontally with the caption (same column / span)
        h_overlap = min(float(gr.x1), float(cap_raw.x1) + 25.0) - max(
            float(gr.x0), float(cap_raw.x0) - 25.0
        )
        if h_overlap <= 0:
            continue
        above_gap = float(cap_raw.y0) - float(gr.y1)
        below_gap = float(gr.y0) - float(cap_raw.y1)
        above = float(gr.y1) <= float(cap_raw.y0) + 18.0 and above_gap <= max_gap
        below = float(gr.y0) >= float(cap_raw.y1) - 18.0 and below_gap <= max_gap
        if not ((obj_kind == "figure" and (above or below)) or (obj_kind == "table" and below)):
            continue
        if _has_intervening_text(gr):
            continue
        if above:
            above_graphic = gr if above_graphic is None else (above_graphic | gr)
        elif below:
            below_graphic = gr if below_graphic is None else (below_graphic | gr)

    if obj_kind == "figure":
        # Standard figure captions sit below their figure; never pull in a lower stacked figure
        # when graphics above the caption already bound this figure.
        merged_graphic = above_graphic if above_graphic is not None else below_graphic
    else:
        merged_graphic = below_graphic

    target_raw = cap_raw | merged_graphic if merged_graphic is not None else cap_raw
    target_vis = _to_visual_rect(target_raw, page)
    norm_bbox = _norm_rect_for_pdfjs(target_vis, page)
    return {
        "page": page_no,
        "rects": [norm_bbox],
        "kind": "area",
        "grounding_tier": "exact_object",
        "matched_text": " ".join(cap_txt.split()),
        "section_path": "",
        "figure_id": figure_id,
        "confidence": 0.9 if cap_score >= 2.0 else 0.75,
    }


def _resolve_object_target(
    ocr_dir: Path,
    pdf_path: Path,
    figure_id: str,
    *,
    doc: Any | None = None,
    page_hint: int | None = None,
    ctx: PdfGroundingContext | None = None,
) -> dict[str, Any]:
    import pymupdf

    target_norm = figure_id.strip().lower().replace(" ", "_")
    target_parsed = _parse_object_id(figure_id)
    candidates: list[dict[str, Any]] = []
    inventories = (
        ctx.get_inventories()
        if ctx is not None
        else {
            fname: read_json(ocr_dir / "structure" / fname)
            for fname in ("figure_inventory.json", "table_inventory.json")
            if (ocr_dir / "structure" / fname).exists()
        }
    )

    for fname, list_key in (
        ("figure_inventory.json", "matched_figures"),
        ("table_inventory.json", "matched_tables"),
    ):
        inv = inventories.get(fname)
        if not inv:
            continue
        entries = inv.get(list_key) or inv.get("tables") or inv.get("figures") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            eid = str(entry.get("figure_id") or entry.get("table_id") or entry.get("id") or "").strip().lower()
            elabel = str(entry.get("label") or entry.get("object_label") or "").strip().lower().replace(" ", "_")
            if eid == target_norm or elabel == target_norm:
                candidates.append(entry)
                continue
            if target_parsed is not None:
                e_parsed = _parse_object_id(eid) or _parse_object_id(elabel)
                if e_parsed == target_parsed:
                    candidates.append(entry)

    own_doc = doc is None
    active_doc = doc if doc is not None else pymupdf.open(str(pdf_path))
    try:
        if not candidates:
            native_hit = _resolve_native_caption_object(
                active_doc, figure_id, page_hint=page_hint, ctx=ctx
            )
            if native_hit is not None:
                return native_hit
            raise ValueError(
                f"Object {figure_id!r} not found in OCR inventory or native PDF captions; "
                "pass a verbatim quote from the caption or run OCR."
            )

        obj = candidates[0]
        page_no = int(obj.get("page") or 1)
        bbox = obj.get("cluster_bbox") or obj.get("crop_bbox") or obj.get("bbox")
        if not bbox or len(bbox) < 4:
            raise ValueError(f"Object {figure_id} has no bounding box on page {page_no}")
        if page_no < 1 or page_no > len(active_doc):
            raise ValueError(f"Object page {page_no} out of range for PDF ({len(active_doc)} pages)")

        page = active_doc[page_no - 1]
        pr = page.rect
        pw = float(obj.get("page_width") or 0.0)
        ph = float(obj.get("page_height") or 0.0)
        if pw > 0 and ph > 0:
            x0 = _clamp01(float(bbox[0]) / pw)
            y0 = _clamp01(float(bbox[1]) / ph)
            x1 = _clamp01(float(bbox[2]) / pw)
            y1 = _clamp01(float(bbox[3]) / ph)
            if x1 < x0:
                x0, x1 = x1, x0
            if y1 < y0:
                y0, y1 = y1, y0
            norm_bbox = [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]
        else:
            norm_bbox = _norm_rect_for_pdfjs(
                pymupdf.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                page,
            )
    finally:
        if own_doc:
            active_doc.close()

    return {
        "page": page_no,
        "rects": [norm_bbox],
        "kind": "area",
        "grounding_tier": "exact_object",
        "matched_text": str(obj.get("caption_text") or obj.get("caption") or figure_id),
        "section_path": str(obj.get("section_path") or ""),
        "figure_id": str(obj.get("figure_id") or obj.get("table_id") or figure_id),
        "confidence": 1.0,
    }


def _collect_candidate_blocks(
    ocr_dir: Path,
    pdf_path: Path,
    *,
    doc: Any | None = None,
) -> list[dict[str, Any]]:
    structured_path = ocr_dir / "structure" / "blocks.structured.jsonl"
    if structured_path.exists():
        blocks: list[dict[str, Any]] = []
        for b in read_jsonl(structured_path):
            if b.get("text") and b.get("bbox"):
                blocks.append(b)
        if blocks:
            return blocks

    import pymupdf

    native_blocks: list[dict[str, Any]] = []
    own_doc = doc is None
    active_doc = doc if doc is not None else pymupdf.open(str(pdf_path))
    try:
        for page_idx in range(len(active_doc)):
            page = active_doc[page_idx]
            pr = page.rect
            for blk in page.get_text("blocks"):
                if len(blk) < 5:
                    continue
                if len(blk) >= 7 and int(blk[6] or 0) != 0:
                    continue
                txt = str(blk[4] or "")
                if not txt.strip():
                    continue
                r_vis = _to_visual_rect(pymupdf.Rect(blk[:4]), page)
                native_blocks.append(
                    {
                        "page": page_idx + 1,
                        "bbox": [
                            float(r_vis.x0) - float(pr.x0),
                            float(r_vis.y0) - float(pr.y0),
                            float(r_vis.x1) - float(pr.x0),
                            float(r_vis.y1) - float(pr.y0),
                        ],
                        "page_width": float(pr.width),
                        "page_height": float(pr.height),
                        "text": txt,
                        "block_id": "",
                        "section_path": "",
                    }
                )
    finally:
        if own_doc:
            active_doc.close()
    return native_blocks


def _score_block_or_pair(
    blocks: list[dict[str, Any]],
    q_norm: str,
    q_tokens: set[str],
    *,
    page_hint: int | None,
    section_hint: str,
) -> tuple[dict[str, Any] | None, float, float]:
    best_blk: dict[str, Any] | None = None
    best_rank = -1.0
    best_raw_score = 0.0

    sec_hint_low = section_hint.strip().lower()
    single_norms: list[str] = []
    single_tokens: list[set[str]] = []

    for blk in blocks:
        txt = str(blk.get("text") or "")
        b_norm = _fold_text(txt)
        b_tokens = _text_tokens(txt)
        single_norms.append(b_norm)
        single_tokens.append(b_tokens)
        if q_norm in b_norm:
            raw_score = 1.0
        else:
            if not b_tokens:
                continue
            raw_score = len(q_tokens & b_tokens) / max(1, len(q_tokens))
        rank = raw_score
        if page_hint is not None and int(blk.get("page") or 0) == int(page_hint):
            rank += 0.12
        if sec_hint_low:
            sec_str = str(blk.get("section_path") or blk.get("section_title") or "").lower()
            if sec_hint_low in sec_str:
                rank += 0.06
        if rank > best_rank:
            best_rank = rank
            best_raw_score = raw_score
            best_blk = blk

    # Adjacent same-page block pair rescue (e.g., quote spanning column break or paragraph break)
    if best_raw_score < 1.0 and len(blocks) >= 2:
        for idx in range(len(blocks) - 1):
            b1 = blocks[idx]
            b2 = blocks[idx + 1]
            p1 = int(b1.get("page") or 0)
            p2 = int(b2.get("page") or 0)
            if p1 <= 0 or p1 != p2:
                continue
            t1 = single_tokens[idx]
            t2 = single_tokens[idx + 1]
            if not (q_tokens & t1) or not (q_tokens & t2):
                # Also allow boundary splice if folded suffix+prefix contains q_norm
                comb_norm = single_norms[idx] + single_norms[idx + 1]
                if q_norm not in comb_norm:
                    continue
            else:
                comb_norm = single_norms[idx] + single_norms[idx + 1]

            if q_norm in comb_norm:
                pair_raw = 1.0
            else:
                pair_raw = len(q_tokens & (t1 | t2)) / max(1, len(q_tokens))
            pair_rank = pair_raw
            if page_hint is not None and p1 == int(page_hint):
                pair_rank += 0.12
            if sec_hint_low:
                sec_str = (
                    str(b1.get("section_path") or b1.get("section_title") or "")
                    + " "
                    + str(b2.get("section_path") or b2.get("section_title") or "")
                ).lower()
                if sec_hint_low in sec_str:
                    pair_rank += 0.06
            if pair_rank > best_rank + 0.01 or (best_raw_score < 0.55 and pair_raw >= 0.55 and pair_rank > best_rank):
                best_rank = pair_rank
                best_raw_score = pair_raw
                best_blk = {
                    "page": p1,
                    "bbox": b1["bbox"],
                    "page_width": b1.get("page_width"),
                    "page_height": b1.get("page_height"),
                    "section_path": b1.get("section_path") or b2.get("section_path") or "",
                    "section_title": b1.get("section_title") or b2.get("section_title") or "",
                    "_pair_blocks": [b1, b2],
                }

    return best_blk, best_rank, best_raw_score


def _margin_fallback_result(
    *,
    page_no: int,
    rects: list[list[float]],
    clean_quote: str,
    sec_path: str,
    figure_id: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "page": page_no,
        "rects": rects,
        "kind": "margin",
        "grounding_tier": "margin_fallback",
        "matched_text": clean_quote,
        "section_path": sec_path,
        "figure_id": figure_id,
        "confidence": round(confidence, 3),
    }


def ground_target_in_pdf(
    vault: Path,
    paper_key: str,
    pdf_path: Path,
    *,
    quote: str = "",
    figure_id: str = "",
    page_hint: int | None = None,
    section_hint: str = "",
    ctx: PdfGroundingContext | None = None,
) -> dict[str, Any]:
    """Ground a quote or figure/table ID inside *pdf_path* with 3-stage error tolerance."""
    own_ctx = ctx is None
    active_ctx = ctx if ctx is not None else PdfGroundingContext(vault, paper_key, pdf_path)

    try:
        if figure_id.strip() and not quote.strip():
            return _resolve_object_target(
                active_ctx.ocr_dir,
                pdf_path,
                figure_id.strip(),
                doc=active_ctx.doc,
                page_hint=page_hint,
                ctx=active_ctx,
            )

        clean_quote = str(quote or "").strip()
        if not clean_quote:
            raise ValueError("Either --quote or --figure-id must be provided")

        q_norm = _fold_text(clean_quote)
        q_tokens = _text_tokens(clean_quote)
        if not q_norm or not q_tokens:
            raise ValueError("Quote does not contain matchable text")

        doc = active_ctx.doc
        blocks = active_ctx.get_blocks()

        # Pure scanned PDF without OCR artifacts or extractable native text
        if not blocks:
            if page_hint is not None:
                ph_int = int(page_hint)
                if ph_int < 1 or ph_int > len(doc):
                    raise ValueError(f"page_hint {ph_int} out of range for PDF ({len(doc)} pages)")
                return _margin_fallback_result(
                    page_no=ph_int,
                    rects=[[0.015, 0.12, 0.025, 0.22]],
                    clean_quote=clean_quote,
                    sec_path=section_hint,
                    figure_id=figure_id.strip(),
                    confidence=0.2,
                )
            raise ValueError(
                "PDF has no extractable text layer and no OCR artifacts (likely a scanned image PDF). "
                "Run OCR first or pass page_hint to place a margin annotation."
            )

        best_blk, _best_rank, best_raw_score = _score_block_or_pair(
            blocks,
            q_norm,
            q_tokens,
            page_hint=page_hint,
            section_hint=section_hint,
        )

        # If Stage 1 fell short on a hinted page, check if hinted page is scanned-only
        # or if the exact folded quote uniquely exists on that hinted page.
        if best_blk is None or best_raw_score < 0.55:
            if page_hint is not None:
                ph_int = int(page_hint)
                if 1 <= ph_int <= len(doc):
                    page_chars = active_ctx.get_page_chars(ph_int)
                    if not page_chars and not any(int(b.get("page") or 0) == ph_int for b in blocks):
                        return _margin_fallback_result(
                            page_no=ph_int,
                            rects=[[0.015, 0.12, 0.025, 0.22]],
                            clean_quote=clean_quote,
                            sec_path=section_hint,
                            figure_id=figure_id.strip(),
                            confidence=0.2,
                        )
                    min_cross = 0.86 if len(q_norm) >= 35 else (0.92 if len(q_norm) >= 16 else 1.0)
                    hit_hint, hint_score = _align_folded_quote(
                        page_chars,
                        q_norm,
                        require_unique=True,
                        min_fuzzy_score=min_cross,
                    )
                    if hit_hint:
                        page = doc[ph_int - 1]
                        rects, recovered = _cluster_chars_to_rects(hit_hint, page)
                        if not _rects_look_distorted(rects, len(q_norm), page=page):
                            return {
                                "page": ph_int,
                                "rects": rects,
                                "kind": "highlight",
                                "grounding_tier": "exact_cross_column",
                                "matched_text": clean_quote or recovered,
                                "section_path": section_hint,
                                "figure_id": figure_id.strip(),
                                "confidence": round(min(1.0, hint_score), 3),
                            }
            raise ValueError(
                "Quote could not be grounded in source text; pass a verbatim sentence from the paper."
            )

        import pymupdf

        page_no = int(best_blk.get("page") or 1)
        if page_no < 1 or page_no > len(doc):
            raise ValueError(f"Grounded block page {page_no} exceeds PDF page count {len(doc)}")
        page = doc[page_no - 1]
        pr = page.rect
        sec_path = str(best_blk.get("section_path") or best_blk.get("section_title") or "")

        component_blocks = best_blk.get("_pair_blocks") or [best_blk]
        pad = 6.0
        raw_search_rects: list[Any] = []
        for cb in component_blocks:
            cb_bbox = cb["bbox"]
            cb_pw = float(cb.get("page_width") or pr.width or 1.0)
            cb_ph = float(cb.get("page_height") or pr.height or 1.0)
            cb_sx = float(pr.width) / cb_pw if cb_pw > 0 else 1.0
            cb_sy = float(pr.height) / cb_ph if cb_ph > 0 else 1.0
            vis_rect = pymupdf.Rect(
                float(pr.x0) + float(cb_bbox[0]) * cb_sx - pad,
                float(pr.y0) + float(cb_bbox[1]) * cb_sy - pad,
                float(pr.x0) + float(cb_bbox[2]) * cb_sx + pad,
                float(pr.y0) + float(cb_bbox[3]) * cb_sy + pad,
            )
            raw_search_rects.append(_to_raw_rect(vis_rect, page))

        rawdict = active_ctx.get_rawdict(page_no)
        # Stage 2a: strict in-block (or adjacent-pair) char stream alignment
        blk_chars = _extract_pdf_chars_in_rects(rawdict, raw_search_rects)
        hit_chars, align_score = _align_folded_quote(
            blk_chars,
            q_norm,
            require_unique=False,
            min_fuzzy_score=0.72,
        )
        if hit_chars:
            rects, recovered = _cluster_chars_to_rects(hit_chars, page)
            if not _rects_look_distorted(rects, len(q_norm), page=page):
                tier = "exact_cross_column" if len(component_blocks) > 1 and len(rects) > 1 else "exact_sentence"
                return {
                    "page": page_no,
                    "rects": rects,
                    "kind": "highlight",
                    "grounding_tier": tier,
                    "matched_text": clean_quote or recovered,
                    "section_path": sec_path,
                    "figure_id": figure_id.strip(),
                    "confidence": round(min(1.0, align_score), 3),
                }

        # Stage 2b: same-page unique cross-column rescue (now includes < 35 chars when unique!)
        page_chars = active_ctx.get_page_chars(page_no)
        min_cross = 0.86 if len(q_norm) >= 35 else (0.92 if len(q_norm) >= 16 else 1.0)
        hit_page, cross_score = _align_folded_quote(
            page_chars,
            q_norm,
            require_unique=True,
            min_fuzzy_score=min_cross,
        )
        if hit_page:
            rects, recovered = _cluster_chars_to_rects(hit_page, page)
            if not _rects_look_distorted(rects, len(q_norm), page=page):
                return {
                    "page": page_no,
                    "rects": rects,
                    "kind": "highlight",
                    "grounding_tier": "exact_cross_column",
                    "matched_text": clean_quote or recovered,
                    "section_path": sec_path,
                    "figure_id": figure_id.strip(),
                    "confidence": round(min(1.0, cross_score), 3),
                }

        # Stage 3: honest left-margin bracket fallback along the grounded anchor block
        anchor_blk = component_blocks[0]
        abbox = anchor_blk["bbox"]
        apw = float(anchor_blk.get("page_width") or pr.width or 1.0)
        aph = float(anchor_blk.get("page_height") or pr.height or 1.0)
        asx = float(pr.width) / apw if apw > 0 else 1.0
        asy = float(pr.height) / aph if aph > 0 else 1.0
        vis_anchor = pymupdf.Rect(
            float(pr.x0) + float(abbox[0]) * asx,
            float(pr.y0) + float(abbox[1]) * asy,
            float(pr.x0) + float(abbox[2]) * asx,
            float(pr.y0) + float(abbox[3]) * asy,
        )
        bx0, by0, _bx1, by1 = _norm_rect_for_pdfjs(vis_anchor, page)
        if by1 <= by0:
            by1 = _clamp01(by0 + 0.03)
        margin_x0 = max(0.01, bx0 - 0.018)
        margin_x1 = max(margin_x0 + 0.008, bx0 - 0.006)
        return _margin_fallback_result(
            page_no=page_no,
            rects=[[round(margin_x0, 4), round(by0, 4), round(margin_x1, 4), round(by1, 4)]],
            clean_quote=clean_quote,
            sec_path=sec_path,
            figure_id=figure_id.strip(),
            confidence=best_raw_score,
        )
    finally:
        if own_ctx:
            active_ctx.close()
