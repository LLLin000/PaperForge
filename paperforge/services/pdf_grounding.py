"""3-stage error-tolerant PDF sentence & object grounding engine.

Maps a verbatim quote or object reference (``figure_id``/``table_id``) to exact
normalized PDF.js coordinates without letting bounding boxes drift across
pages or columns:
  1. Stage 1 — Block coarse lock in ``blocks.structured.jsonl`` (or native blocks)
  2. Stage 2a — In-block fuzzy folded character-stream alignment
  3. Stage 2b — Same-page cross-column unique rescue for merged dual-column blocks
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


def _norm_rect_for_pdfjs(rect: Any, page: Any) -> list[float]:
    pr = page.rect
    w = max(1e-6, float(pr.width))
    h = max(1e-6, float(pr.height))
    return [
        round(_clamp01((float(rect.x0) - float(pr.x0)) / w), 4),
        round(_clamp01((float(rect.y0) - float(pr.y0)) / h), 4),
        round(_clamp01((float(rect.x1) - float(pr.x0)) / w), 4),
        round(_clamp01((float(rect.y1) - float(pr.y0)) / h), 4),
    ]


def _extract_pdf_chars_in_rect(rawdict: dict[str, Any], rect: Any | None) -> list[tuple[str, Any, str]]:
    import pymupdf

    chars_out: list[tuple[str, Any, str]] = []
    for blk in rawdict.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                for ch in sp.get("chars", []):
                    cb = ch.get("bbox")
                    if not cb or len(cb) < 4:
                        continue
                    r = pymupdf.Rect(cb)
                    if rect is not None:
                        cx = (r.x0 + r.x1) / 2.0
                        cy = (r.y0 + r.y1) / 2.0
                        if not (rect.x0 <= cx <= rect.x1 and rect.y0 <= cy <= rect.y1):
                            continue
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

    sm = difflib.SequenceMatcher(None, q_norm, s_str, autojunk=False)
    blocks = sm.get_matching_blocks()
    matched_len = sum(m.size for m in blocks if m.size >= 3)
    score = matched_len / max(1, len(q_norm))
    valid = [m for m in blocks if m.size >= 4]
    if valid and score >= min_fuzzy_score:
        c_start = idx_map[valid[0].b]
        c_end = idx_map[valid[-1].b + valid[-1].size - 1]
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
    rects = [_norm_rect_for_pdfjs(lr, page) for _, lr in lines]
    recovered = "".join(c[2] for c in hit_chars).strip()
    return rects, recovered


def _rects_look_distorted(rects: list[list[float]], char_count: int) -> bool:
    """Detect degenerate PDF text layers where a highlight stretches implausibly wide or tall."""
    if not rects:
        return True
    for x0, y0, x1, y1 in rects:
        w = x1 - x0
        h = y1 - y0
        if h > 0.14 or (w > 0.86 and char_count < 18):
            return True
    return False


def _resolve_object_target(ocr_dir: Path, pdf_path: Path, figure_id: str) -> dict[str, Any]:
    import pymupdf

    target_norm = figure_id.strip().lower().replace(" ", "_")
    candidates: list[dict[str, Any]] = []
    for fname, list_key in (
        ("figure_inventory.json", "matched_figures"),
        ("table_inventory.json", "matched_tables"),
    ):
        inv_path = ocr_dir / "structure" / fname
        if not inv_path.exists():
            continue
        inv = read_json(inv_path)
        entries = inv.get(list_key) or inv.get("tables") or inv.get("figures") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            eid = str(entry.get("figure_id") or entry.get("table_id") or entry.get("id") or "").strip().lower()
            elabel = str(entry.get("label") or entry.get("object_label") or "").strip().lower().replace(" ", "_")
            if eid == target_norm or elabel == target_norm:
                candidates.append(entry)

    if not candidates:
        raise ValueError(f"Object not found in OCR inventory: {figure_id}")

    obj = candidates[0]
    page_no = int(obj.get("page") or 1)
    bbox = obj.get("cluster_bbox") or obj.get("crop_bbox") or obj.get("bbox")
    if not bbox or len(bbox) < 4:
        raise ValueError(f"Object {figure_id} has no bounding box on page {page_no}")

    pw = float(obj.get("page_width") or 0.0)
    ph = float(obj.get("page_height") or 0.0)
    with pymupdf.open(str(pdf_path)) as doc:
        if page_no < 1 or page_no > len(doc):
            raise ValueError(f"Object page {page_no} out of range for PDF ({len(doc)} pages)")
        pr = doc[page_no - 1].rect
        if pw <= 0 or ph <= 0:
            pw, ph = float(pr.width), float(pr.height)
    norm_bbox = [
        round(_clamp01(float(bbox[0]) / pw), 4),
        round(_clamp01(float(bbox[1]) / ph), 4),
        round(_clamp01(float(bbox[2]) / pw), 4),
        round(_clamp01(float(bbox[3]) / ph), 4),
    ]
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
    with pymupdf.open(str(pdf_path)) as doc:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pr = page.rect
            for blk in page.get_text("blocks"):
                if len(blk) >= 5 and str(blk[4] or "").strip():
                    native_blocks.append(
                        {
                            "page": page_idx + 1,
                            "bbox": [float(blk[0]), float(blk[1]), float(blk[2]), float(blk[3])],
                            "page_width": float(pr.width),
                            "page_height": float(pr.height),
                            "text": str(blk[4]),
                            "block_id": "",
                            "section_path": "",
                        }
                    )
    return native_blocks


def ground_target_in_pdf(
    vault: Path,
    paper_key: str,
    pdf_path: Path,
    *,
    quote: str = "",
    figure_id: str = "",
    page_hint: int | None = None,
    section_hint: str = "",
) -> dict[str, Any]:
    """Ground a quote or figure/table ID inside *pdf_path* with 3-stage error tolerance."""
    from paperforge.config import paperforge_paths

    paths = paperforge_paths(Path(vault).expanduser().resolve())
    ocr_dir = paths["ocr"] / paper_key

    if figure_id.strip() and not quote.strip():
        return _resolve_object_target(ocr_dir, pdf_path, figure_id.strip())

    clean_quote = str(quote or "").strip()
    if not clean_quote:
        raise ValueError("Either --quote or --figure-id must be provided")

    q_norm = _fold_text(clean_quote)
    q_tokens = _text_tokens(clean_quote)
    if not q_norm or not q_tokens:
        raise ValueError("Quote does not contain matchable text")

    blocks = _collect_candidate_blocks(ocr_dir, pdf_path)
    best_blk: dict[str, Any] | None = None
    best_rank = -1.0
    best_raw_score = 0.0

    sec_hint_low = section_hint.strip().lower()
    for blk in blocks:
        txt = str(blk.get("text") or "")
        b_norm = _fold_text(txt)
        if q_norm in b_norm:
            raw_score = 1.0
        else:
            b_tokens = _text_tokens(txt)
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

    if best_blk is None or best_raw_score < 0.55:
        raise ValueError(
            "Quote could not be grounded in source text; pass a verbatim sentence from the paper."
        )

    import pymupdf

    page_no = int(best_blk.get("page") or 1)
    bbox = best_blk["bbox"]
    sec_path = str(best_blk.get("section_path") or best_blk.get("section_title") or "")

    with pymupdf.open(str(pdf_path)) as doc:
        if page_no < 1 or page_no > len(doc):
            raise ValueError(f"Grounded block page {page_no} exceeds PDF page count {len(doc)}")
        page = doc[page_no - 1]
        pr = page.rect
        pw = float(best_blk.get("page_width") or pr.width or 1.0)
        ph = float(best_blk.get("page_height") or pr.height or 1.0)
        sx = float(pr.width) / pw if pw > 0 else 1.0
        sy = float(pr.height) / ph if ph > 0 else 1.0
        pad = 6.0
        blk_rect = pymupdf.Rect(
            float(bbox[0]) * sx - pad,
            float(bbox[1]) * sy - pad,
            float(bbox[2]) * sx + pad,
            float(bbox[3]) * sy + pad,
        )

        rawdict = page.get_text("rawdict")
        # Stage 2a: strict in-block char stream alignment
        blk_chars = _extract_pdf_chars_in_rect(rawdict, blk_rect)
        hit_chars, align_score = _align_folded_quote(
            blk_chars,
            q_norm,
            require_unique=False,
            min_fuzzy_score=0.72,
        )
        if hit_chars:
            rects, recovered = _cluster_chars_to_rects(hit_chars, page)
            if not _rects_look_distorted(rects, len(q_norm)):
                return {
                    "page": page_no,
                    "rects": rects,
                    "kind": "highlight",
                    "grounding_tier": "exact_sentence",
                    "matched_text": clean_quote or recovered,
                    "section_path": sec_path,
                    "figure_id": figure_id.strip(),
                    "confidence": round(min(1.0, align_score), 3),
                }

        # Stage 2b: same-page unique cross-column rescue
        if len(q_norm) >= 35:
            page_chars = _extract_pdf_chars_in_rect(rawdict, None)
            hit_page, cross_score = _align_folded_quote(
                page_chars,
                q_norm,
                require_unique=True,
                min_fuzzy_score=0.86,
            )
            if hit_page:
                rects, recovered = _cluster_chars_to_rects(hit_page, page)
                if not _rects_look_distorted(rects, len(q_norm)):
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

        # Stage 3: honest left-margin bracket fallback along the grounded block
        bx0 = _clamp01(float(bbox[0]) * sx / max(1e-6, float(pr.width)))
        by0 = _clamp01(float(bbox[1]) * sy / max(1e-6, float(pr.height)))
        by1 = _clamp01(float(bbox[3]) * sy / max(1e-6, float(pr.height)))
        if by1 <= by0:
            by1 = _clamp01(by0 + 0.03)
        margin_x0 = max(0.01, bx0 - 0.018)
        margin_x1 = max(margin_x0 + 0.008, bx0 - 0.006)
        return {
            "page": page_no,
            "rects": [[round(margin_x0, 4), round(by0, 4), round(margin_x1, 4), round(by1, 4)]],
            "kind": "margin",
            "grounding_tier": "margin_fallback",
            "matched_text": clean_quote,
            "section_path": sec_path,
            "figure_id": figure_id.strip(),
            "confidence": round(best_raw_score, 3),
        }
