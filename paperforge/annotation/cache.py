"""Annotation JSON cache for Obsidian plugin (no sql.js required).

Writes a flat JSON file that the plugin reads directly via fs.readFileSync,
following the same snapshot pattern as memory-runtime-state.json.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


CACHE_FILENAME = "annotation-cache.json"

CACHE_QUERY = """
SELECT
    id, paper_id, zotero_key, zotero_attachment_key,
    type, page_index, page_label,
    selected_text, comment, color, sort_index,
    tags_json, position_json, sync_state, is_readonly
FROM annotations
WHERE deleted_at IS NULL
ORDER BY paper_id, sort_index
"""


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    pos = row["position_json"]
    if isinstance(pos, str):
        try:
            pos = json.loads(pos)
        except (json.JSONDecodeError, TypeError):
            pos = None
    tags = row["tags_json"]
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return {
        "id": row["id"],
        "paper_id": row["paper_id"],
        "zotero_key": row["zotero_key"] or "",
        "zotero_attachment_key": row["zotero_attachment_key"] or "",
        "type": row["type"],
        "page_index": row["page_index"],
        "page_label": row["page_label"] or "",
        "selected_text": row["selected_text"] or "",
        "comment": row["comment"] or "",
        "color": row["color"] or "#ffd400",
        "sort_index": row["sort_index"] or "",
        "tags": tags,
        "position": pos,
        "sync_state": row["sync_state"],
        "is_readonly": bool(row["is_readonly"]),
    }


def _load_pdf_page_sizes(vault_path: Path, attachment_key: str) -> dict[int, tuple[float, float]]:
    if not attachment_key:
        return {}
    storage_dir = vault_path / "System" / "Zotero" / "storage" / attachment_key
    if not storage_dir.exists():
        return {}
    pdf_files = sorted(storage_dir.glob("*.pdf"))
    if not pdf_files:
        return {}
    if PdfReader is None:
        return {}
    try:
        reader = PdfReader(str(pdf_files[0]))
    except Exception:
        return {}
    sizes: dict[int, tuple[float, float]] = {}
    for idx, page in enumerate(reader.pages):
        try:
            box = page.mediabox
            sizes[idx] = (float(box.width), float(box.height))
        except Exception:
            continue
    return sizes


def build_cache(conn: sqlite3.Connection, vault_path: Path | str) -> dict[str, Any]:
    """Read all non-deleted annotations and group by paper_id."""
    vault = Path(str(vault_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(CACHE_QUERY).fetchall()
    by_paper: dict[str, list[dict[str, Any]]] = {}
    attachment_page_sizes: dict[str, dict[int, tuple[float, float]]] = {}
    for r in rows:
        d = _row_to_dict(r)
        attachment_key = d["zotero_attachment_key"]
        if attachment_key and attachment_key not in attachment_page_sizes:
            attachment_page_sizes[attachment_key] = _load_pdf_page_sizes(vault, attachment_key)
        page_sizes = attachment_page_sizes.get(attachment_key, {})
        page_size = page_sizes.get(int(d.get("page_index") or 0))
        if page_size:
            d["page_width"] = page_size[0]
            d["page_height"] = page_size[1]
        pid = d["paper_id"]
        if pid not in by_paper:
            by_paper[pid] = []
        by_paper[pid].append(d)
    return {
        "v": 1,
        "ts": _now(),
        "total": len(rows),
        "papers": list(by_paper.keys()),
        "by_paper": by_paper,
    }


def write_cache(conn: sqlite3.Connection, vault_path: Path | str) -> str | None:
    """Write annotation cache JSON to the vault's indexes directory.

    Returns the cache file path on success, None if the directory is missing.
    """
    vault = Path(str(vault_path))
    indexes_dir = vault / "System" / "PaperForge" / "indexes"
    if not indexes_dir.exists():
        return None
    cache_path = indexes_dir / CACHE_FILENAME
    data = build_cache(conn, vault)
    cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(cache_path)
