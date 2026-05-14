from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.memory._columns import PAPER_COLUMNS, build_paper_row
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import (
    CURRENT_SCHEMA_VERSION,
    PAPERS_AI_TRIGGER,
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


def _import_reading_log(conn, vault: Path) -> int:
    """Import reading-log.jsonl into reading_log table. Returns count."""
    from paperforge.memory.permanent import read_all_reading_notes

    notes = read_all_reading_notes(vault)
    conn.execute("DELETE FROM reading_log")
    count = 0
    for note in notes:
        conn.execute(
            """INSERT INTO reading_log (id, paper_id, project, section, excerpt, context, usage, note, tags_json, created_at, agent, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                note["id"], note["paper_id"],
                note.get("project", ""),
                note["section"], note["excerpt"],
                note.get("context", ""), note["usage"],
                note.get("note", ""),
                json.dumps(note.get("tags", []), ensure_ascii=False),
                note["created_at"],
                note.get("agent", ""),
                1 if note.get("verified") else 0,
            ),
        )
        count += 1
    return count


def _import_project_log(conn, vault: Path) -> int:
    """Import project-log.jsonl into project_log table. Returns count."""
    from paperforge.memory.permanent import read_all_project_entries

    entries = read_all_project_entries(vault)
    conn.execute("DELETE FROM project_log")
    count = 0
    for entry in entries:
        conn.execute(
            """INSERT INTO project_log (id, project, date, type, title, decisions_json, detours_json, reusable_json, todos_json, related_papers_json, tags_json, created_at, agent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["id"], entry["project"],
                entry.get("date", ""), entry["type"], entry["title"],
                json.dumps(entry.get("decisions", []), ensure_ascii=False),
                json.dumps(entry.get("detours", []), ensure_ascii=False),
                json.dumps(entry.get("reusable", []), ensure_ascii=False),
                json.dumps(entry.get("todos", []), ensure_ascii=False),
                json.dumps(entry.get("related_papers", []), ensure_ascii=False),
                json.dumps(entry.get("tags", []), ensure_ascii=False),
                entry.get("created_at", ""),
                entry.get("agent", ""),
            ),
        )
        count += 1
    return count


def _import_correction_log(conn, vault: Path) -> int:
    """Import correction-log.jsonl into paper_events for FTS search. Returns count."""
    from paperforge.memory.permanent import read_all_corrections

    corrections = read_all_corrections(vault)
    count = 0
    for c in corrections:
        payload = {
            "original_id": c.get("original_id", ""),
            "correction": c.get("correction", ""),
            "reason": c.get("reason", ""),
        }
        conn.execute(
            "INSERT INTO paper_events (paper_id, event_type, payload_json) VALUES (?, 'correction_note', ?)",
            (c["paper_id"], json.dumps(payload, ensure_ascii=False)),
        )
        count += 1
    return count


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

        conn.execute("DROP TRIGGER IF EXISTS papers_ai")

        now_utc = datetime.now(timezone.utc).isoformat()
        paper_rows: list[dict] = []
        asset_rows: list[tuple] = []
        alias_rows: list[tuple] = []

        placeholders = ", ".join([f":{c}" for c in PAPER_COLUMNS])
        cols = ", ".join(PAPER_COLUMNS)
        paper_sql = f"INSERT OR REPLACE INTO papers ({cols}) VALUES ({placeholders})"

        for entry in items:
            zotero_key = entry.get("zotero_key", "")
            if not zotero_key:
                continue

            entry["lifecycle"] = str(compute_lifecycle(entry))
            entry["maturity"] = compute_maturity(entry)
            entry["next_step"] = str(compute_next_step(entry))
            paper_rows.append(build_paper_row(entry, generated_at))

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

                asset_rows.append((zotero_key, asset_type, rel_path, exists))

            for alias_type in ALIAS_TYPES:
                raw_val = entry.get(alias_type, "")
                if not raw_val:
                    continue
                raw_str = str(raw_val)
                alias_rows.append((zotero_key, raw_str, raw_str.lower().strip(), alias_type))

        conn.executemany(paper_sql, paper_rows)
        conn.executemany(
            """INSERT OR REPLACE INTO paper_assets
               (paper_id, asset_type, path, exists_on_disk)
               VALUES (?, ?, ?, ?)""",
            asset_rows,
        )
        conn.executemany(
            """INSERT OR REPLACE INTO paper_aliases
               (paper_id, alias, alias_norm, alias_type)
               VALUES (?, ?, ?, ?)""",
            alias_rows,
        )

        conn.execute("""INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
                         SELECT rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json
                         FROM papers""")
        conn.execute(PAPERS_AI_TRIGGER)

        reading_count = _import_reading_log(conn, vault)
        logger.info("Imported %d reading notes from JSONL", reading_count)

        project_count = _import_project_log(conn, vault)
        logger.info("Imported %d project log entries from JSONL", project_count)

        correction_count = _import_correction_log(conn, vault)
        logger.info("Imported %d corrections from JSONL", correction_count)

        conn.execute(
            "DELETE FROM paper_events WHERE event_type != 'correction_note';"
        )

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
            "papers_indexed": len(paper_rows),
            "assets_indexed": len(asset_rows),
            "aliases_indexed": len(alias_rows),
            "reading_notes_imported": reading_count,
            "project_entries_imported": project_count,
            "corrections_imported": correction_count,
            "schema_version": str(CURRENT_SCHEMA_VERSION),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
