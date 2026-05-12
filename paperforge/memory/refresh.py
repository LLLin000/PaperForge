from __future__ import annotations

import json
from pathlib import Path

from paperforge.memory.builder import (
    PAPER_COLUMNS,
    ASSET_FIELDS,
    ALIAS_TYPES,
    compute_hash,
    _resolve_vault_path,
)
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.worker.asset_index import read_index
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)


def refresh_paper(vault: Path, zotero_key: str) -> bool:
    """Incrementally refresh one paper in paperforge.db from formal-library.json."""
    envelope = read_index(vault)
    if not envelope:
        return False
    items = envelope if isinstance(envelope, list) else envelope.get("items", [])

    entry = None
    for e in items:
        if e.get("zotero_key") == zotero_key:
            entry = e
            break
    if not entry:
        return False

    generated_at = envelope.get("generated_at", "") if not isinstance(envelope, list) else ""

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False

    conn = get_connection(db_path, read_only=False)
    try:
        ensure_schema(conn)

        lifecycle = str(compute_lifecycle(entry))
        maturity = compute_maturity(entry)
        next_step = str(compute_next_step(entry))

        paper_values = {}
        for col in PAPER_COLUMNS:
            if col == "authors_json":
                paper_values[col] = json.dumps(entry.get("authors", []), ensure_ascii=False)
            elif col == "collections_json":
                paper_values[col] = json.dumps(entry.get("collections", []), ensure_ascii=False)
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

        conn.execute("DELETE FROM paper_assets WHERE paper_id = ?", (zotero_key,))
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
                    exists = 1 if "## \U0001f52d \u7cbe\u8bfb" in content else 0
                except Exception:
                    exists = 0
            conn.execute(
                "INSERT OR REPLACE INTO paper_assets (paper_id, asset_type, path, exists_on_disk) VALUES (?, ?, ?, ?)",
                (zotero_key, asset_type, rel_path, exists),
            )

        conn.execute("DELETE FROM paper_aliases WHERE paper_id = ?", (zotero_key,))
        for alias_type in ALIAS_TYPES:
            raw_val = entry.get(alias_type, "")
            if not raw_val:
                continue
            raw_str = str(raw_val)
            conn.execute(
                "INSERT OR REPLACE INTO paper_aliases (paper_id, alias, alias_norm, alias_type) VALUES (?, ?, ?, ?)",
                (zotero_key, raw_str, raw_str.lower().strip(), alias_type),
            )

        # Re-index FTS
        try:
            conn.execute("DELETE FROM paper_fts WHERE zotero_key = ?", (zotero_key,))
            conn.execute(
                "INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json) "
                "VALUES ((SELECT rowid FROM papers WHERE zotero_key = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (zotero_key, zotero_key, entry.get("citation_key", ""), entry.get("title", ""),
                 entry.get("first_author", ""), paper_values["authors_json"],
                 entry.get("abstract", ""), entry.get("journal", ""), entry.get("domain", ""),
                 entry.get("collection_path", ""), paper_values["collections_json"]),
            )
        except Exception:
            pass  # FTS may not be available

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
