from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.io import read_json, read_jsonl
from paperforge.memory._columns import build_paper_row
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.paper_state import ASSET_FIELDS, ALIAS_TYPES, _paper_state_hash, upsert_paper_state
from paperforge.memory.schema import (
    CURRENT_SCHEMA_VERSION,
    PAPERS_AI_TRIGGER,
    clear_fts,
    drop_all_tables,
    ensure_schema,
    get_schema_version,
    migrate_schema,
)
from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, build_paper_manifest
from paperforge.retrieval.units import build_body_units, build_object_units
from paperforge.worker.asset_index import read_index
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)

logger = logging.getLogger(__name__)

def compute_hash(items: list[dict]) -> str:
    sorted_items = sorted(items, key=lambda e: e["zotero_key"])
    raw = json.dumps(sorted_items, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_vault_path(vault: Path, rel_path: str) -> Path:
    if not rel_path:
        return Path()
    p = vault / rel_path
    return p.resolve() if p.exists() else p


def _import_reading_log(conn, vault: Path, valid_keys: set[str] | None = None) -> dict:
    """Import reading-log.jsonl into reading_log table.

    Skips records whose ``paper_id`` is not in *valid_keys* (prevents FK
    failures when a paper was deleted but its reading-log JSONL survives).
    Returns ``{"imported": N, "orphaned_skipped": M}``.
    """
    from paperforge.memory.permanent import read_all_reading_notes

    notes = read_all_reading_notes(vault)
    conn.execute("DELETE FROM reading_log")
    imported = 0
    skipped = 0
    for note in notes:
        pid = note["paper_id"]
        if valid_keys is not None and pid not in valid_keys:
            skipped += 1
            continue
        conn.execute(
            """INSERT INTO reading_log (id, paper_id, project, section, excerpt, context, usage, note, tags_json, created_at, agent, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                note["id"], pid,
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
        imported += 1
    return {"imported": imported, "orphaned_skipped": skipped}


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


def _diff_paper_state(conn: sqlite3.Connection, items: list[dict]) -> dict:
    """Compare per-paper state hashes → {added, changed, deleted, unchanged}.

    Exactly 2 SQL queries regardless of library size.
    """
    index_keys = {e["zotero_key"] for e in items if e.get("zotero_key")}
    db_keys = {r[0] for r in conn.execute("SELECT zotero_key FROM papers").fetchall()}

    # Single query: load all stored hashes
    stored = dict(
        conn.execute(
            "SELECT substr(key, 18), value FROM meta WHERE key LIKE 'paper_state_hash:%'"
        ).fetchall()
    )

    added: set[str] = set()
    changed: set[str] = set()
    unchanged: set[str] = set()
    for entry in items:
        key = entry.get("zotero_key", "")
        if not key:
            continue
        if key not in db_keys:
            added.add(key)
        else:
            h = _paper_state_hash(entry, generated_at="")
            if stored.get(key) == h:
                unchanged.add(key)
            else:
                changed.add(key)

    deleted = db_keys - index_keys
    return {"added": added, "changed": changed, "deleted": deleted, "unchanged": unchanged}


def _delete_paper(conn: sqlite3.Connection, vault: Path, key: str) -> None:
    """Delete one paper and all derived state. Same transaction, no commit/rollback.

    Deletion order respects FK constraints:
    0. Vectors (same transaction — prevents ghost retrieval results)
    1. FK-referencing leaf tables (body_units_fts, body_units, object_units,
       paper_events, reading_log, paper_aliases, paper_assets)
    2. Meta entries (manifest, paper_state_hash)
    3. Papers (last — other tables FK-reference it)

    ``reading_log`` is deleted from memory DB only; JSONL is the permanent store.
    """
    from paperforge.embedding._chroma import delete_paper_vectors_in_conn

    # 0. Vector invalidation (same transaction — P0)
    try:
        delete_paper_vectors_in_conn(conn, key)
    except Exception:
        logger.warning("Vector deletion failed for %s, deleting meta only", key)
        for t in ("vec_body_meta", "vec_objects_meta", "vec_fulltext_meta"):
            conn.execute(f"DELETE FROM {t} WHERE paper_id=?", (key,))

    # 1. FK-referencing tables
    conn.execute("DELETE FROM body_units_fts WHERE paper_id=?", (key,))
    conn.execute("DELETE FROM body_units WHERE paper_id=?", (key,))
    conn.execute("DELETE FROM object_units WHERE paper_id=?", (key,))
    conn.execute("DELETE FROM paper_events WHERE paper_id=?", (key,))
    conn.execute("DELETE FROM reading_log WHERE paper_id=?", (key,))
    conn.execute("DELETE FROM paper_aliases WHERE paper_id=?", (key,))
    conn.execute("DELETE FROM paper_assets WHERE paper_id=?", (key,))

    # 2. Meta entries
    conn.execute(
        "DELETE FROM meta WHERE key IN (?, ?)",
        (f"manifest:{key}", f"paper_state_hash:{key}"),
    )

    # 3. Papers last
    conn.execute("DELETE FROM papers WHERE zotero_key=?", (key,))

def build_from_index(vault: Path) -> dict:
    """Read formal-library.json and build/rebuild paperforge.db.

    Scheduling:
    1. Schema migration (destructive → full rebuild).
    2. Global hash unchanged → skip (fast path).
    3. Per-paper incremental: diff → delete → upsert → units.
    """
    envelope = read_index(vault)
    if envelope is None:
        raise FileNotFoundError(
            "Canonical index not found. Run paperforge sync --rebuild-index."
        )
    if isinstance(envelope, list):
        items = envelope
        generated_at = ""
    else:
        items = envelope.get("items", [])
        generated_at = envelope.get("generated_at", "")
    canonical_hash = (
        compute_hash(items)
        if isinstance(items, list) and items and isinstance(items[0], dict)
        else ""
    )

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=False)
    try:
        # ── 0. Read version BEFORE ensure_schema/migrate_schema ──────────
        stored_version = get_schema_version(conn)

        # ── 1. Schema migration ──────────────────────────────────────────
        migration_action = migrate_schema(conn, stored_version, CURRENT_SCHEMA_VERSION)
        ensure_schema(conn)

        ocr_root = vault / "System" / "PaperForge" / "ocr"

        # ── 2. Destructive migration → full rebuild ──────────────────────
        if migration_action == "destructive":
            result = _full_rebuild(conn, vault, items, canonical_hash, generated_at, ocr_root)
            conn.commit()
            conn.close()
            return result

        # ── 3. Global hash unchanged → fast path ─────────────────────────
        if canonical_hash and db_path.exists():
            try:
                cached = conn.execute(
                    "SELECT value FROM meta WHERE key='canonical_index_hash'"
                ).fetchone()
            except Exception:
                cached = None
            if cached and cached[0] == canonical_hash:
                if ocr_root.exists():
                    _incremental_units_only(conn, items, ocr_root)
                conn.commit()
                papers_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
                conn.close()
                logger.info(
                    "Index unchanged, incremental unit update done (%s papers)", papers_count
                )
                return {"papers_indexed": papers_count, "db_path": str(db_path), "hash_match": True}

        # ── 4. Per-paper incremental ─────────────────────────────────────
        diff = _diff_paper_state(conn, items)

        # 4a. Delete removed papers
        for key in diff["deleted"]:
            _delete_paper(conn, vault, key)

        # 4b. Upsert changed / added papers
        now_utc = datetime.now(timezone.utc).isoformat()
        changed_count = 0
        for entry in items:
            key = entry.get("zotero_key", "")
            if not key:
                continue
            if key in diff["added"] | diff["changed"]:
                entry["lifecycle"] = str(compute_lifecycle(entry))
                entry["maturity"] = compute_maturity(entry)
                entry["next_step"] = str(compute_next_step(entry))
                upsert_paper_state(conn, vault=vault, entry=entry, generated_at=now_utc)
                changed_count += 1

        # 4c. Import logs with orphan guard
        valid_keys = {e["zotero_key"] for e in items if e.get("zotero_key")}
        reading_result = _import_reading_log(conn, vault, valid_keys)
        _import_project_log(conn, vault)
        conn.execute("DELETE FROM paper_events WHERE event_type = 'correction_note';")
        correction_result = _import_correction_log(conn, vault, valid_keys)
        conn.execute("DELETE FROM paper_events WHERE event_type != 'correction_note';")

        # 4d. OCR unit rebuilds (per-paper hash comparison)
        if ocr_root.exists():
            _incremental_units_only(conn, items, ocr_root)

        # 4e. Advance canonical hash LAST — if anything fails before this,
        #     the next run re-diffs and retries
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("canonical_index_hash", canonical_hash),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("canonical_index_generated_at", generated_at),
        )

        conn.commit()
        logger.info(
            "Index built: %d changed, %d deleted, %d reading (orphans: %d), %d corrections (orphans: %d)",
            changed_count,
            len(diff["deleted"]),
            reading_result.get("imported", 0),
            reading_result.get("orphaned_skipped", 0),
            correction_result.get("imported", 0),
            correction_result.get("orphaned_skipped", 0),
        )
        papers_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        conn.close()
        return {
            "papers_indexed": papers_count,
            "db_path": str(db_path),
            "hash_match": False,
            "changed": list(diff["changed"]),
            "added": list(diff["added"]),
            "deleted": list(diff["deleted"]),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _full_rebuild(
    conn: sqlite3.Connection,
    vault: Path,
    items: list[dict],
    canonical_hash: str,
    generated_at: str,
    ocr_root: Path,
) -> dict:
    """Full rebuild: DELETE all tables, re-INSERT everything.

    Only used for destructive schema migrations. Seeds per-paper hashes
    so subsequent builds use the incremental path.
    """
    logger.info("Starting full rebuild")
    ensure_schema(conn)
    conn.execute("PRAGMA foreign_keys=OFF;")
    conn.execute("DELETE FROM paper_events;")
    conn.execute("DELETE FROM reading_log;")
    conn.execute("DELETE FROM project_log;")
    conn.execute("DELETE FROM paper_aliases;")
    conn.execute("DELETE FROM paper_assets;")
    conn.execute("DELETE FROM papers;")
    conn.execute("DELETE FROM body_units;")
    conn.execute("DELETE FROM object_units;")
    # Clean residual per-paper meta entries
    conn.execute("DELETE FROM meta WHERE key LIKE 'paper_state_hash:%' OR key LIKE 'manifest:%'")
    conn.execute("PRAGMA foreign_keys=ON;")

    clear_fts(conn)
    conn.execute("DROP TRIGGER IF EXISTS papers_ai")

    now_utc = datetime.now(timezone.utc).isoformat()
    paper_rows: list[dict] = []
    asset_rows: list[tuple] = []
    alias_rows: list[tuple] = []
    all_hashes: list[tuple[str, str]] = []

    placeholders = ", ".join([f":{c}" for c in build_paper_row(items[0], "").keys()])
    cols = ", ".join(build_paper_row(items[0], "").keys())
    paper_sql = f"INSERT OR REPLACE INTO papers ({cols}) VALUES ({placeholders})"

    for entry in items:
        zotero_key = entry.get("zotero_key", "")
        if not zotero_key:
            continue
        entry["lifecycle"] = str(compute_lifecycle(entry))
        entry["maturity"] = compute_maturity(entry)
        entry["next_step"] = str(compute_next_step(entry))
        paper_rows.append(build_paper_row(entry, now_utc))
        all_hashes.append((f"paper_state_hash:{zotero_key}", _paper_state_hash(entry, "")))

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

    conn.execute(
        """INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
           SELECT rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json
           FROM papers"""
    )
    conn.execute(PAPERS_AI_TRIGGER)

    # Import logs with orphan guard
    valid_keys = {e["zotero_key"] for e in items if e.get("zotero_key")}
    reading_result = _import_reading_log(conn, vault, valid_keys)
    _import_project_log(conn, vault)
    conn.execute("DELETE FROM paper_events WHERE event_type = 'correction_note';")
    correction_result = _import_correction_log(conn, vault, valid_keys)
    conn.execute("DELETE FROM paper_events WHERE event_type != 'correction_note';")

    # Build retrieval units
    body_unit_count = 0
    object_unit_count = 0
    if ocr_root.exists():
        for entry in items:
            zotero_key = entry.get("zotero_key", "")
            if not zotero_key:
                continue
            ocr_dir = ocr_root / zotero_key
            index_root = ocr_dir / "index"
            tree_path = index_root / "structure-tree.json"
            structured_path = ocr_dir / "structure" / "blocks.structured.jsonl"
            if not tree_path.exists() or not structured_path.exists():
                continue
            tree = read_json(tree_path)
            structured_blocks = read_jsonl(structured_path)
            role_index_path = index_root / "role-index.json"
            role_index = read_json(role_index_path) if role_index_path.exists() else {}
            body_units = build_body_units(tree=tree, structured_blocks=structured_blocks)
            object_units = build_object_units(
                tree=tree, structured_blocks=structured_blocks, role_index=role_index
            )
            _upsert_body_units(conn, body_units)
            _upsert_object_units(conn, object_units)
            ocr_result_hash = _resolve_ocr_result_hash(ocr_dir)
            manifest = build_paper_manifest(
                paper_id=zotero_key,
                ocr_result_hash=ocr_result_hash,
                structure_tree_bytes=tree_path.read_bytes(),
                retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
                body_units=body_units,
                object_units=object_units,
                source_paths={
                    "structured_blocks": str(structured_path),
                    "role_index": str(role_index_path),
                    "fulltext": str(ocr_dir / "fulltext.md"),
                },
            )
            _write_manifest_row(conn, manifest)
            body_unit_count += len(body_units)
            object_unit_count += len(object_units)
    if body_unit_count or object_unit_count:
        logger.info("Retrieval units built: %d body, %d object", body_unit_count, object_unit_count)

    # Seed all per-paper hashes (P0-4)
    conn.executemany(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", all_hashes
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
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

    return {
        "db_path": str(get_memory_db_path(vault)),
        "papers_indexed": len(paper_rows),
        "assets_indexed": len(asset_rows),
        "aliases_indexed": len(alias_rows),
        "reading_notes_imported": reading_result.get("imported", 0),
        "project_entries_imported": 0,
        "corrections_imported": correction_result.get("imported", 0),
        "schema_version": str(CURRENT_SCHEMA_VERSION),
        "body_units_built": body_unit_count,
        "object_units_built": object_unit_count,
        "hash_match": True,
    }

def _resolve_ocr_result_hash(paper_dir: Path) -> str:
    """Resolve OCR result hash with 3-level fallback.
    
    1. index/result-hash.txt (fastest, preferred)
    2. SHA-256 of structured artifacts (structure/blocks.structured.jsonl,
       index/structure-tree.json, index/role-index.json)
    3. meta.json derived_version hash
    """
    # Level 1: explicit result-hash.txt
    rp = paper_dir / "index" / "result-hash.txt"
    if rp.exists():
        return rp.read_text(encoding="utf-8").strip()
    # Level 2: hash of structured artifacts
    h = hashlib.sha256()
    for rel in ["structure/blocks.structured.jsonl", "index/structure-tree.json",
                 "index/role-index.json"]:
        p = paper_dir / rel
        if p.exists():
            h.update(p.read_bytes())
    if h.hexdigest() != hashlib.sha256(b"").hexdigest():
        return h.hexdigest()
    # Level 3: meta.json derived_version
    meta_p = paper_dir / "meta.json"
    if meta_p.exists():
        try:
            dv = json.loads(meta_p.read_bytes()).get("derived_version", {})
            return hashlib.sha256(json.dumps(dv, sort_keys=True).encode()).hexdigest()
        except Exception:
            pass
    return ""


def _upsert_body_units(conn: sqlite3.Connection, body_units: list[dict]) -> None:
    """Insert or replace body unit rows, then refresh the FTS index."""
    for unit in body_units:
        conn.execute(
            """INSERT OR REPLACE INTO body_units
               (unit_id, paper_id, node_id, section_path,
                section_path_json, section_level, section_title,
                unit_text, unit_kind, part_ordinal,
                page_span_json, block_span_json,
                token_estimate, indexable, veto_reason, quality_hints_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                unit["unit_id"],
                unit["paper_id"],
                unit.get("node_id", ""),
                unit["section_path"],
                unit.get("section_path_json", "[]"),
                unit.get("section_level", 0),
                unit.get("section_title", ""),
                unit["unit_text"],
                unit.get("unit_kind", "body"),
                unit.get("part_ordinal", 0),
                json.dumps(unit.get("page_span", [])),
                json.dumps(unit.get("block_span", [])),
                unit.get("token_estimate", 0),
                1 if unit.get("indexable") else 0,
                unit.get("veto_reason", ""),
                json.dumps(unit.get("quality_hints", [])),
            ),
        )
    # Refresh FTS for all body units of the affected papers
    paper_ids = list({u["paper_id"] for u in body_units})
    for pid in paper_ids:
        # ponytail: FTS5 external content table raises DatabaseError on DELETE
        # when the index is empty (first build). Wrap to handle both cases.
        try:
            conn.execute("DELETE FROM body_units_fts WHERE paper_id = ?", (pid,))
        except sqlite3.DatabaseError:
            pass
        conn.execute(
            """INSERT INTO body_units_fts(rowid, unit_id, paper_id, section_path, unit_text)
               SELECT rowid, unit_id, paper_id, section_path, unit_text
               FROM body_units WHERE paper_id = ? AND indexable = 1""",
            (pid,),
        )


def _upsert_object_units(conn: sqlite3.Connection, object_units: list[dict]) -> None:
    """Insert or replace object unit rows."""
    for unit in object_units:
        conn.execute(
            """INSERT OR REPLACE INTO object_units
               (unit_id, paper_id, node_id, section_path,
                section_path_json, object_kind, object_label,
                caption_text, nearby_body_text,
                page_span_json, block_span_json,
                token_estimate, indexable, veto_reason, quality_hints_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                unit["unit_id"],
                unit["paper_id"],
                unit.get("node_id", ""),
                unit["section_path"],
                unit.get("section_path_json", "[]"),
                unit.get("object_kind", ""),
                unit.get("object_label", ""),
                unit.get("caption_text", ""),
                unit.get("nearby_body_text", ""),
                json.dumps(unit.get("page_span", [])),
                json.dumps(unit.get("block_span", [])),
                unit.get("token_estimate", 0),
                1 if unit.get("indexable") else 0,
                unit.get("veto_reason", ""),
                json.dumps(unit.get("quality_hints", [])),
            ),
        )


def _incremental_units_only(conn: sqlite3.Connection, items: list[dict], ocr_root: Path) -> None:
    """Incremental: rebuild only body/object units for papers whose OCR hash changed."""
    built_count = 0
    for entry in items:
        key = entry.get("zotero_key", "")
        if not key:
            continue
        paper_dir = ocr_root / key
        tree_path = paper_dir / "index" / "structure-tree.json"
        blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
        if not tree_path.exists() or not blocks_path.exists():
            continue
        current_hash = _resolve_ocr_result_hash(paper_dir)
        row = conn.execute(
            "SELECT value FROM meta WHERE key=?", (f"manifest:{key}",)
        ).fetchone()
        if row:
            stored = json.loads(row[0])
            if (stored.get("ocr_result_hash") == current_hash
                and stored.get("retrieval_policy_version") == RETRIEVAL_POLICY_VERSION):
                continue
        _rebuild_paper_units(conn, key, paper_dir, tree_path, blocks_path)
        built_count += 1
    if built_count:
        logger.info("Incremental units rebuilt for %d papers", built_count)
    else:
        logger.info("No papers needed incremental unit rebuild")


def _rebuild_paper_units(conn: sqlite3.Connection, key: str, paper_dir: Path,
                          tree_path: Path, blocks_path: Path) -> None:
    """Delete and rebuild body + object units for a single paper."""
    conn.execute("DELETE FROM body_units WHERE paper_id = ?", (key,))
    conn.execute("DELETE FROM body_units_fts WHERE paper_id = ?", (key,))
    conn.execute("DELETE FROM object_units WHERE paper_id = ?", (key,))
    tree = read_json(tree_path)
    blocks = read_jsonl(blocks_path)
    role_index_path = paper_dir / "index" / "role-index.json"
    role_index = read_json(role_index_path) if role_index_path.exists() else {}
    body_units = build_body_units(tree=tree, structured_blocks=blocks)
    object_units = build_object_units(
        tree=tree, structured_blocks=blocks, role_index=role_index
    )
    _upsert_body_units(conn, body_units)
    _upsert_object_units(conn, object_units)
    current_hash = _resolve_ocr_result_hash(paper_dir)
    manifest = build_paper_manifest(
        paper_id=key,
        ocr_result_hash=current_hash,
        structure_tree_bytes=tree_path.read_bytes(),
        retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
        body_units=body_units,
        object_units=object_units,
        source_paths={
            "structured_blocks": str(blocks_path),
            "role_index": str(role_index_path),
            "fulltext": str(paper_dir / "fulltext.md"),
        },
    )
    _write_manifest_row(conn, manifest)


def _write_manifest_row(conn: sqlite3.Connection, manifest: dict) -> None:
    """Store a paper's retrieval manifest in the meta table."""
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (f"manifest:{manifest['paper_id']}", json.dumps(manifest)),
    )
