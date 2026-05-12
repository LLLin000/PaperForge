from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import (
    CURRENT_SCHEMA_VERSION,
    clear_fts,
    drop_all_tables,
    ensure_schema,
    get_schema_version,
)
from paperforge.worker.asset_index import read_index
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)

logger = logging.getLogger(__name__)

PAPER_COLUMNS = [
    "zotero_key", "citation_key", "title", "year", "doi", "pmid",
    "journal", "first_author", "authors_json", "abstract", "domain",
    "collection_path", "collections_json",
    "has_pdf", "do_ocr", "analyze", "ocr_status", "deep_reading_status",
    "ocr_job_id", "impact_factor",
    "lifecycle", "maturity_level", "maturity_name", "next_step",
    "pdf_path", "note_path", "main_note_path", "paper_root",
    "fulltext_path", "ocr_md_path", "ocr_json_path", "ai_path",
    "deep_reading_md_path", "updated_at",
]

ASSET_FIELDS = [
    ("pdf", "pdf_path"),
    ("formal_note", "note_path"),
    ("main_note", "main_note_path"),
    ("ocr_fulltext", "fulltext_path"),
    ("ocr_meta", "ocr_json_path"),
    ("deep_reading", "main_note_path"),
    ("ai_dir", "ai_path"),
]

ALIAS_TYPES = ["zotero_key", "citation_key", "title", "doi"]


def compute_hash(items: list[dict]) -> str:
    sorted_items = sorted(items, key=lambda e: e["zotero_key"])
    raw = json.dumps(sorted_items, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_vault_path(vault: Path, rel_path: str) -> Path:
    if not rel_path:
        return Path()
    p = vault / rel_path
    return p.resolve() if p.exists() else p


def build_from_index(vault: Path) -> dict:
    """Read formal-library.json and build/rebuild paperforge.db.
    
    Returns a dict with counts for reporting.
    """
    envelope = read_index(vault)
    if envelope is None:
        raise FileNotFoundError(
            "Canonical index not found. Run paperforge sync --rebuild-index."
        )
    # Legacy format: bare list of entries (pre-envelope)
    if isinstance(envelope, list):
        items = envelope
        generated_at = ""
    else:
        items = envelope.get("items", [])
        generated_at = envelope.get("generated_at", "")
    canonical_hash = compute_hash(items) if isinstance(items, list) and items and isinstance(items[0], dict) else ""

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=False)
    try:
        stored_version = get_schema_version(conn)
        if stored_version != CURRENT_SCHEMA_VERSION:
            drop_all_tables(conn)
        ensure_schema(conn)

        conn.execute("DELETE FROM paper_aliases;")
        conn.execute("DELETE FROM paper_assets;")
        conn.execute("DELETE FROM papers;")

        clear_fts(conn)

        now_utc = datetime.now(timezone.utc).isoformat()
        papers_count = 0
        assets_count = 0
        aliases_count = 0

        for entry in items:
            zotero_key = entry.get("zotero_key", "")
            if not zotero_key:
                continue

            lifecycle = str(compute_lifecycle(entry))
            maturity = compute_maturity(entry)
            next_step = str(compute_next_step(entry))

            paper_values = {}
            for col in PAPER_COLUMNS:
                if col == "authors_json":
                    paper_values[col] = json.dumps(
                        entry.get("authors", []), ensure_ascii=False
                    )
                elif col == "collections_json":
                    paper_values[col] = json.dumps(
                        entry.get("collections", []), ensure_ascii=False
                    )
                elif col == "lifecycle":
                    paper_values[col] = lifecycle
                elif col == "maturity_level":
                    paper_values[col] = maturity.get("level", 1)
                elif col == "maturity_name":
                    paper_values[col] = maturity.get("level_name", "")
                elif col == "next_step":
                    paper_values[col] = next_step
                elif col == "updated_at":
                    paper_values[col] = generated_at
                elif col in ("do_ocr", "analyze"):
                    val = entry.get(col)
                    paper_values[col] = 1 if val else 0
                elif col == "has_pdf":
                    paper_values[col] = 1 if entry.get("has_pdf") else 0
                else:
                    paper_values[col] = entry.get(col, "")

            placeholders = ", ".join([f":{c}" for c in PAPER_COLUMNS])
            cols = ", ".join(PAPER_COLUMNS)
            conn.execute(
                f"INSERT OR REPLACE INTO papers ({cols}) VALUES ({placeholders})",
                paper_values,
            )
            papers_count += 1

            try:
                conn.execute(
                    """INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
                       VALUES ((SELECT rowid FROM papers WHERE zotero_key = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (zotero_key, zotero_key, entry.get("citation_key", ""), entry.get("title", ""),
                     entry.get("first_author", ""), paper_values.get("authors_json", ""),
                     entry.get("abstract", ""), entry.get("journal", ""), entry.get("domain", ""),
                     entry.get("collection_path", ""), paper_values.get("collections_json", "")),
                )
            except sqlite3.IntegrityError:
                pass  # duplicate rowid if FTS trigger already fired

            for asset_type, entry_field in ASSET_FIELDS:
                path_val = entry.get(entry_field, "")
                if not path_val:
                    continue
                rel_path = str(path_val).replace("\\", "/")
                abs_path = _resolve_vault_path(vault, rel_path)
                exists = 1 if abs_path.exists() else 0

                if asset_type == "deep_reading" and abs_path.exists():
                    try:
                        content = abs_path.read_text(encoding="utf-8")
                        exists = 1 if "## 🔍 精读" in content else 0
                    except Exception:
                        exists = 0

                conn.execute(
                    """INSERT OR REPLACE INTO paper_assets
                       (paper_id, asset_type, path, exists_on_disk)
                       VALUES (?, ?, ?, ?)""",
                    (zotero_key, asset_type, rel_path, exists),
                )
                assets_count += 1

            for alias_type in ALIAS_TYPES:
                raw_val = entry.get(alias_type, "")
                if not raw_val:
                    continue
                raw_str = str(raw_val)
                conn.execute(
                    """INSERT OR REPLACE INTO paper_aliases
                       (paper_id, alias, alias_norm, alias_type)
                       VALUES (?, ?, ?, ?)""",
                    (
                        zotero_key,
                        raw_str,
                        raw_str.lower().strip(),
                        alias_type,
                    ),
                )
                aliases_count += 1

        meta_upserts = [
            ("schema_version", str(CURRENT_SCHEMA_VERSION)),
            ("paperforge_version", PF_VERSION),
            ("created_at", now_utc),
            ("last_full_build_at", now_utc),
            ("canonical_index_hash", canonical_hash),
            ("canonical_index_generated_at", generated_at),
        ]
        for key, value in meta_upserts:
            conn.execute(
                """INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)""",
                (key, value),
            )

        conn.commit()

        return {
            "db_path": str(db_path),
            "papers_indexed": papers_count,
            "assets_indexed": assets_count,
            "aliases_indexed": aliases_count,
            "schema_version": str(CURRENT_SCHEMA_VERSION),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
