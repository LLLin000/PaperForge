"""Write imported annotation highlights back to PaperForge fulltext markdown."""

from __future__ import annotations

import html
import json
import re
from difflib import SequenceMatcher
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from paperforge.config import paperforge_paths

_PF_MARK_RE = re.compile(
    r"<mark\b(?=[^>]*\bdata-paperforge-annotation-id=)[^>]*>(.*?)</mark>",
    re.DOTALL | re.IGNORECASE,
)
_PAGE_MARKER_RE = re.compile(r"<!--\s*page\s+([^>]+?)\s*-->", re.IGNORECASE)


def _row_get(row: Any, key: str, default: Any = "") -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, default)


def _strip_existing_marks(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return html.unescape(match.group(1))

    return _PF_MARK_RE.sub(replace, text)


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    offset_map: list[int] = []
    pending_space_offset: int | None = None
    for offset, ch in enumerate(text):
        if ch.isspace():
            if normalized and pending_space_offset is None:
                pending_space_offset = offset
            continue
        if pending_space_offset is not None:
            normalized.append(" ")
            offset_map.append(pending_space_offset)
            pending_space_offset = None
        normalized.append(ch.lower())
        offset_map.append(offset)
    return "".join(normalized).strip(), offset_map


def _compact_with_map(text: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    offset_map: list[int] = []
    in_tag = False
    for offset, ch in enumerate(text):
        if ch == "<":
            in_tag = True
            continue
        if in_tag:
            if ch == ">":
                in_tag = False
            continue
        if not ch.isalnum():
            continue
        normalized.append(ch.lower())
        offset_map.append(offset)
    return "".join(normalized), offset_map


def _find_text_span(source_text: str, selected_text: str) -> tuple[int, int] | None:
    selected = " ".join(str(selected_text or "").split())
    if not selected:
        return None

    exact = source_text.find(selected)
    if exact >= 0:
        return exact, exact + len(selected)

    source_norm, source_map = _normalize_with_map(source_text)
    selected_norm, _ = _normalize_with_map(selected)
    if not source_norm or not selected_norm:
        return None
    index = source_norm.find(selected_norm)
    if index < 0:
        return None
    end_index = index + len(selected_norm) - 1
    if index >= len(source_map) or end_index >= len(source_map):
        return None
    start = source_map[index]
    end = source_map[end_index] + 1
    if start < end:
        return start, end

    return None


def _find_compact_text_span(source_text: str, selected_text: str) -> tuple[int, int] | None:
    source_norm, source_map = _compact_with_map(source_text)
    selected_norm, _ = _compact_with_map(str(selected_text or ""))
    if not source_norm or not selected_norm:
        return None
    index = source_norm.find(selected_norm)
    if index < 0:
        return None
    end_index = index + len(selected_norm) - 1
    if index >= len(source_map) or end_index >= len(source_map):
        return None
    return source_map[index], source_map[end_index] + 1


def _find_anchored_compact_text_span(source_text: str, selected_text: str) -> tuple[int, int] | None:
    source_norm, source_map = _compact_with_map(source_text)
    selected_norm, _ = _compact_with_map(str(selected_text or ""))
    if len(source_norm) < 80 or len(selected_norm) < 80:
        return None

    anchor_len = 20
    start_anchor = selected_norm[:anchor_len]
    end_anchor = selected_norm[-anchor_len:]
    start_index = source_norm.find(start_anchor)
    if start_index < 0:
        return None
    end_index = source_norm.find(end_anchor, start_index + anchor_len)
    if end_index < 0:
        return None
    end_norm_index = end_index + anchor_len - 1
    if end_norm_index >= len(source_map):
        return None
    return source_map[start_index], source_map[end_norm_index] + 1


def _find_start_anchored_similar_span(source_text: str, selected_text: str) -> tuple[int, int] | None:
    source_norm, source_map = _compact_with_map(source_text)
    selected_raw = str(selected_text or "")
    selected_norm, _ = _compact_with_map(selected_raw)
    if len(source_norm) < 120 or len(selected_norm) < 120:
        return None

    anchor_len = 20
    start_index = source_norm.find(selected_norm[:anchor_len])
    if start_index < 0:
        return None

    expected_end = start_index + len(selected_norm)
    min_end = max(start_index + anchor_len, expected_end - 80)
    max_end = min(len(source_norm), expected_end + 80)
    best: tuple[float, int, float] | None = None
    step = 5
    for end in range(min_end, max_end + 1, step):
        candidate = source_norm[start_index:end]
        ratio = SequenceMatcher(None, selected_norm, candidate).ratio()
        length_penalty = abs(len(candidate) - len(selected_norm)) / len(selected_norm)
        score = ratio - (length_penalty * 0.5)
        if best is None or score > best[0]:
            best = (score, end, ratio)

    if best is None or best[2] < 0.86:
        return None
    end_norm_index = best[1] - 1

    tokens = re.findall(r"[A-Za-z0-9]{4,}", selected_raw)
    if tokens:
        tail_norm, _ = _compact_with_map(tokens[-1])
        search_end = min(len(source_norm), best[1] + 100)
        tail_index = source_norm.find(tail_norm, max(start_index, best[1] - 30), search_end)
        if tail_index >= 0:
            end_norm_index = max(end_norm_index, tail_index + len(tail_norm) - 1)

    raw_end = source_map[end_norm_index] + 1
    while raw_end < len(source_text) and source_text[raw_end] in ")]}":
        raw_end += 1
    return source_map[start_index], raw_end


def _page_candidates(row: Any) -> list[str]:
    candidates: list[str] = []
    page_label = str(_row_get(row, "page_label", "") or "").strip()
    if page_label:
        candidates.append(page_label)
    page_index = _row_get(row, "page_index", None)
    try:
        candidates.append(str(int(page_index) + 1))
    except (TypeError, ValueError):
        pass
    return list(dict.fromkeys(candidates))


def _page_ranges(source_text: str) -> dict[str, tuple[int, int]]:
    markers = list(_PAGE_MARKER_RE.finditer(source_text))
    ranges: dict[str, tuple[int, int]] = {}
    for idx, marker in enumerate(markers):
        label = " ".join(marker.group(1).split())
        start = marker.end()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(source_text)
        ranges[label] = (start, end)
    return ranges


def _find_row_span(source_text: str, row: Any, page_ranges: dict[str, tuple[int, int]]) -> tuple[int, int] | None:
    selected_text = _row_get(row, "selected_text", "")
    for page in _page_candidates(row):
        page_range = page_ranges.get(page)
        if page_range is None:
            continue
        page_start, page_end = page_range
        span = _find_text_span(source_text[page_start:page_end], selected_text)
        if span is not None:
            return page_start + span[0], page_start + span[1]
        span = _find_compact_text_span(source_text[page_start:page_end], selected_text)
        if span is not None:
            return page_start + span[0], page_start + span[1]
        span = _find_anchored_compact_text_span(source_text[page_start:page_end], selected_text)
        if span is not None:
            return page_start + span[0], page_start + span[1]
        span = _find_start_anchored_similar_span(source_text[page_start:page_end], selected_text)
        if span is not None:
            return page_start + span[0], page_start + span[1]
    return (
        _find_text_span(source_text, selected_text)
        or _find_compact_text_span(source_text, selected_text)
        or _find_anchored_compact_text_span(source_text, selected_text)
        or _find_start_anchored_similar_span(source_text, selected_text)
    )


def _safe_attr(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _safe_color(color: Any) -> str:
    raw = str(color or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return raw
    return "#ffd400"


def _render_mark(row: Any, inner_text: str) -> str:
    color = _safe_color(_row_get(row, "color", ""))
    return (
        '<mark class="paperforge-annotation-highlight" '
        f'data-paperforge-annotation-id="{_safe_attr(_row_get(row, "id", ""))}" '
        f'data-page-index="{_safe_attr(_row_get(row, "page_index", ""))}" '
        f'data-page-label="{_safe_attr(_row_get(row, "page_label", ""))}" '
        f'data-sort-index="{_safe_attr(_row_get(row, "sort_index", ""))}" '
        f'style="background-color: {color};">'
        f"{inner_text}"
        "</mark>"
    )


def apply_annotations_to_fulltext_file(fulltext_path: Path, rows: Iterable[Any]) -> dict[str, Any]:
    """Apply annotation rows to a fulltext.md file as colored HTML marks.

    Existing PaperForge marks are removed first, making the operation idempotent.
    The original selected text remains the only visible text inside each mark.
    """
    annotations = list(rows or [])
    clean_text = _strip_existing_marks(fulltext_path.read_text(encoding="utf-8"))
    page_ranges = _page_ranges(clean_text)
    matches: list[tuple[int, int, Any]] = []
    occupied: list[tuple[int, int]] = []
    unresolved = 0

    for row in annotations:
        span = _find_row_span(clean_text, row, page_ranges)
        if span is None:
            unresolved += 1
            continue
        start, end = span
        if any(start < used_end and used_start < end for used_start, used_end in occupied):
            unresolved += 1
            continue
        occupied.append((start, end))
        matches.append((start, end, row))

    updated = clean_text
    for start, end, row in sorted(matches, key=lambda item: item[0], reverse=True):
        updated = updated[:start] + _render_mark(row, updated[start:end]) + updated[end:]

    fulltext_path.write_text(updated, encoding="utf-8")
    return {"applied": len(matches), "unresolved": unresolved, "fulltext_path": str(fulltext_path)}


def resolve_fulltext_path(vault: Path, paper_key: str) -> Path | None:
    """Resolve the editable fulltext.md path for a paper."""
    paths = paperforge_paths(vault)
    index_path = paths["index"]
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            items = data.get("items") if isinstance(data, dict) else data
            for entry in items or []:
                if entry.get("zotero_key") != paper_key:
                    continue
                rel = entry.get("fulltext_path") or ""
                if rel:
                    candidate = vault / rel
                    if candidate.exists():
                        return candidate
        except Exception:
            pass

    literature = paths["literature"]
    if literature.exists():
        paper_key_lower = paper_key.lower()
        matches = [
            path
            for path in literature.rglob("fulltext.md")
            if paper_key_lower in str(path.relative_to(literature)).lower()
        ]
        if matches:
            return sorted(matches, key=lambda path: len(str(path)))[0]

    fallback = paths["ocr"] / paper_key / "fulltext.md"
    return fallback if fallback.exists() else None


def apply_imported_annotations_to_fulltext(
    vault: Path,
    paper_key: str,
    annotations_db_path: Path,
) -> dict[str, Any]:
    """Read active imported annotations from DB and mark the matching fulltext."""
    fulltext_path = resolve_fulltext_path(vault, paper_key)
    if fulltext_path is None:
        return {"applied": 0, "unresolved": 0, "fulltext_path": None, "error": "fulltext-not-found"}

    import sqlite3

    conn = sqlite3.connect(str(annotations_db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT id, selected_text, color, page_index, page_label, sort_index
               FROM annotations
               WHERE paper_id = ? AND deleted_at IS NULL
               ORDER BY page_index, sort_index, id""",
            (paper_key,),
        ).fetchall()
    finally:
        conn.close()

    result = apply_annotations_to_fulltext_file(fulltext_path, rows)
    result["total"] = len(rows)
    return result
