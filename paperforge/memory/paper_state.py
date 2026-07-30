from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path

from paperforge.memory._columns import PAPER_COLUMNS, build_paper_row

logger = logging.getLogger(__name__)

ASSET_FIELDS: list[tuple[str, str]] = [
    ("pdf", "pdf_path"),
    ("formal_note", "note_path"),
    ("main_note", "main_note_path"),
    ("ocr_fulltext", "fulltext_path"),
    ("ocr_meta", "ocr_json_path"),
    ("deep_reading", "main_note_path"),
    ("ai_dir", "ai_path"),
]

ALIAS_TYPES = ["zotero_key", "citation_key", "title", "doi"]


def _paper_state_hash(entry: dict, generated_at: str) -> str:
    """SHA256 of the full materialized papers row (excluding updated_at).

    Covers every column in the papers table: title, authors, year, DOI,
    journal, domain, ocr_status, lifecycle, all paths, etc. Any metadata
    change automatically changes the hash — no manual field list to curate.
    """
    row = build_paper_row(entry, generated_at="")
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_paper_state(
    conn: sqlite3.Connection,
    *,
    vault: Path,
    entry: dict,
    generated_at: str,
) -> str:
    """Upsert a single paper's state into papers/aliases/assets/meta.

    Executes SQL only — no commit/rollback/close.  Returns the computed
    ``paper_state_hash`` so the caller can verify or log it.

    The papers row uses ``INSERT … ON CONFLICT(zotero_key) DO UPDATE``,
    which preserves the existing rowid and lets the ``papers_au`` AFTER
    UPDATE trigger keep the FTS index in sync automatically.

    Aliases and assets are deleted-then-reinserted per-paper (no bulk path).
    """
    key = entry.get("zotero_key", "")
    if not key:
        raise ValueError("entry must have a zotero_key")

    # ── 1. Papers row ────────────────────────────────────────────────
    cols = ", ".join(PAPER_COLUMNS)
    placeholders = ", ".join([f":{c}" for c in PAPER_COLUMNS])
    update_set = ", ".join(f"{c}=excluded.{c}" for c in PAPER_COLUMNS if c != "zotero_key")
    paper_values = build_paper_row(entry, generated_at)
    conn.execute(
        f"INSERT INTO papers ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(zotero_key) DO UPDATE SET {update_set}",
        paper_values,
    )

    # ── 2. Aliases ───────────────────────────────────────────────────
    conn.execute("DELETE FROM paper_aliases WHERE paper_id=?", (key,))
    for alias_type in ALIAS_TYPES:
        raw_val = entry.get(alias_type, "")
        if not raw_val:
            continue
        conn.execute(
            "INSERT INTO paper_aliases (paper_id, alias, alias_norm, alias_type) "
            "VALUES (?, ?, ?, ?)",
            (key, str(raw_val), str(raw_val).lower().strip(), alias_type),
        )

    # ── 3. Assets ────────────────────────────────────────────────────
    conn.execute("DELETE FROM paper_assets WHERE paper_id=?", (key,))
    for asset_type, entry_field in ASSET_FIELDS:
        path_val = entry.get(entry_field, "")
        if not path_val:
            continue
        rel_path = str(path_val).replace("\\", "/")
        abs_path = vault / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
        exists = 1 if abs_path.exists() else 0
        if asset_type == "deep_reading" and abs_path.exists():
            try:
                content = abs_path.read_text(encoding="utf-8")
                exists = 1 if "## 🔍 精读" in content else 0
            except Exception:
                exists = 0
        conn.execute(
            "INSERT OR REPLACE INTO paper_assets (paper_id, asset_type, path, exists_on_disk) "
            "VALUES (?, ?, ?, ?)",
            (key, asset_type, rel_path, exists),
        )

    # ── 4. State hash ────────────────────────────────────────────────
    hash_val = _paper_state_hash(entry, generated_at)
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (f"paper_state_hash:{key}", hash_val),
    )
    return hash_val
