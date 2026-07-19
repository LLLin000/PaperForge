from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from paperforge.memory._columns import PAPER_COLUMNS, build_paper_row
from paperforge.memory.builder import (
    ALIAS_TYPES,
    ASSET_FIELDS,
    _resolve_vault_path,
)
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import PAPERS_AI_TRIGGER, ensure_schema
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)


def refresh_paper(vault: Path, entry: dict) -> bool:
    """Upsert a single paper into memory DB. Entry is from _build_entry() output."""
    zotero_key = entry.get("zotero_key", "")
    if not zotero_key:
        return False

    generated_at = datetime.now(timezone.utc).isoformat()

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False

    conn = get_connection(db_path, read_only=False)
    try:
        ensure_schema(conn)

        conn.execute("DROP TRIGGER IF EXISTS papers_ai")

        entry["lifecycle"] = str(compute_lifecycle(entry))
        entry["maturity"] = compute_maturity(entry)
        entry["next_step"] = str(compute_next_step(entry))
        paper_values = build_paper_row(entry, generated_at)

        # Step 1: Get old rowid before papers upsert (rowid may change on REPLACE)
        old = conn.execute(
            "SELECT rowid FROM papers WHERE zotero_key = ?",
            (zotero_key,),
        ).fetchone()

        # Step 2: Delete old FTS row BEFORE papers changes
        if old:
            conn.execute(
                "DELETE FROM paper_fts WHERE rowid = ?",
                (old["rowid"],),
            )

        # Step 3: Upsert papers
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

        # Step 4: Get new rowid after upsert
        new = conn.execute(
            "SELECT rowid FROM papers WHERE zotero_key = ?",
            (zotero_key,),
        ).fetchone()

        # Step 5: Insert new FTS row
        if new:
            conn.execute(
                "INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json) "
                "VALUES ((SELECT rowid FROM papers WHERE zotero_key = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    zotero_key,
                    zotero_key,
                    entry.get("citation_key", ""),
                    entry.get("title", ""),
                    entry.get("first_author", ""),
                    paper_values["authors_json"],
                    entry.get("abstract", ""),
                    entry.get("journal", ""),
                    entry.get("domain", ""),
                    entry.get("collection_path", ""),
                    paper_values["collections_json"],
                ),
            )
        conn.execute(PAPERS_AI_TRIGGER)

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
