"""Canonical literature asset index — envelope format, atomic writes, cross-process locking.

This module is the single canonical home for generating and writing the
literature asset index (``formal-library.json``).  Responsibilities:

* ``get_index_path(vault)`` — resolve the index file location.
* ``build_envelope(items)`` — wrap a list of paper entries in a versioned
  envelope (schema_version, generated_at, paper_count).
* ``atomic_write_index(path, data)`` — write index JSON atomically using
  ``tempfile.NamedTemporaryFile`` + ``os.replace``, protected by a
  ``filelock`` cross-process lock (10 s timeout).
* ``build_index(vault, verbose)`` — full index rebuild extracted from the
  legacy ``sync.run_index_refresh`` loop; writes formal notes and produces
  the canonical index.

Design decisions (see Phase 23 context):
* D-01: Index file stays at ``indexes/formal-library.json``.
* D-02: Versioned envelope wraps the items list.
* D-05: Atomic writes via tempfile + os.replace.
* D-06: Cross-process locking via filelock.
* D-15: Extract index generation from sync.py to this module.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import filelock
import shutil

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION = "2"
"""Current index schema version.  Bump when the envelope or entry shape
changes incompatibly."""

INDEX_FILENAME = "formal-library.json"
"""Filename of the canonical asset index."""

LOCK_TIMEOUT = 10
"""Seconds to wait for the cross-process file lock before raising
``filelock.Timeout``."""


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def get_index_path(vault: Path) -> Path:
    """Return the canonical index file path for *vault*.

    This is the same path that ``pipeline_paths()["index"]`` returns:
    ``<paperforge>/indexes/formal-library.json``.
    """
    paths = paperforge_paths(vault)
    return paths["paperforge"] / "indexes" / INDEX_FILENAME


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


def build_envelope(items: list[dict]) -> dict:
    """Wrap *items* in a versioned envelope dict.

    Returns::

        {
            "schema_version": "2",
            "generated_at": "2026-05-04T12:34:56Z",
            "paper_count": len(items),
            "items": items,
        }
    """
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "paper_count": len(items),
        "items": items,
    }


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def atomic_write_index(path: Path, data: dict) -> None:
    """Write *data* as JSON to *path* atomically with cross-process locking.

    Steps:
    1. Create parent directory if it does not exist.
    2. Acquire a ``filelock`` on ``<path>.lock`` with a 10-second timeout.
    3. Write to a temporary file in the same directory (same-filesystem for
       Windows-safe ``os.replace``).
    4. ``os.replace(temp.name, path)`` — atomic on both POSIX and Windows.
    5. On failure: clean up the temp file before propagating.

    Raises:
        filelock.Timeout: If the lock cannot be acquired within
            *LOCK_TIMEOUT* seconds.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = path.with_suffix(".json.lock")
    lock = filelock.FileLock(lock_path, timeout=LOCK_TIMEOUT)

    with lock:
        tmp = None
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=path.parent,
            )
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, path)
        except BaseException:
            if tmp is not None:
                tmp.close()
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
            raise


# ---------------------------------------------------------------------------
# Index read / legacy migration
# ---------------------------------------------------------------------------


def read_index(vault: Path) -> dict | list | None:
    """Read the existing index file and return its parsed content.

    Returns:
        The parsed JSON data (dict for envelope, list for legacy bare-list),
        or ``None`` if the file does not exist or is corrupt.
    """
    path = get_index_path(vault)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupt index at %s, treating as missing: %s", path, exc)
        return None


def is_legacy_format(data) -> bool:
    """Return ``True`` if *data* is a bare list (pre-v1.6 legacy format).

    The current envelope format is a dict with ``"schema_version"``;
    the legacy format is a plain list of entry dicts.
    """
    return isinstance(data, list)


def migrate_legacy_index(vault: Path) -> bool:
    """Detect a legacy bare-list index and back it up before rebuild.

    If the existing index is in legacy format (a bare list), this function
    copies it to ``<index>.bak`` and returns ``True`` to signal that a
    rebuild should happen.  If the file is already envelope format, does
    not exist, or is corrupt, returns ``False`` (no action needed).

    The backup is idempotent — calling repeatedly overwrites the previous
    backup with the latest legacy state.
    """
    path = get_index_path(vault)
    if not path.exists():
        return False

    data = read_index(vault)
    if data is None:
        return False
    if not is_legacy_format(data):
        return False

    bak_path = path.with_suffix(".json.bak")
    shutil.copy2(str(path), str(bak_path))
    logger.info("Legacy format detected at %s, backed up to %s", path, bak_path)
    print(f"Legacy format detected at {path}, backed up to {bak_path}")
    return True


# ---------------------------------------------------------------------------
# Single-entry builder  (shared by full rebuild and incremental refresh)
# ---------------------------------------------------------------------------


def _build_entry(item: dict, vault: Path, paths: dict, domain: str, zotero_dir: Path) -> dict:
    """Construct a single canonical index entry from a BBT export *item*.

    This helper is used by both ``build_index()`` (all items) and
    ``refresh_index_entry()`` (single item).  It:

    1. Gathers OCR meta, PDF paths, deep-reading state.
    2. Writes / updates the formal Obsidian note via ``frontmatter_note()``.
    3. Returns the entry dict with all fields (including workspace paths).

    Lazy imports inside avoid circular dependencies with ``sync.py``.
    """
    # Lazy imports to avoid circular deps with sync.py
    from paperforge.worker.ocr import validate_ocr_meta
    from paperforge.worker._utils import read_json, write_json, slugify_filename
    from paperforge.worker.sync import (
        collection_fields,
        frontmatter_note,
        has_deep_reading_content,
        obsidian_wikilink_for_path,
        obsidian_wikilink_for_pdf,
    )

    key = item["key"]
    collection_meta = collection_fields(item.get("collections", []))
    pdf_attachments = [
        a for a in item.get("attachments", []) if a.get("contentType") == "application/pdf"
    ]
    meta_path = paths["ocr"] / key / "meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {}
    if meta:
        validated_ocr_status, validated_error = validate_ocr_meta(paths, meta)
        meta["ocr_status"] = validated_ocr_status
        if validated_error:
            meta["error"] = validated_error
            write_json(meta_path, meta)
    title_slug = slugify_filename(item["title"])
    note_path = paths["literature"] / domain / f"{key} - {title_slug}.md"
    if note_path.parent.exists():
        for stale_note in note_path.parent.glob(f"{key} - *.md"):
            if stale_note != note_path:
                stale_note.unlink()

    # ---- entry dict -------------------------------------------------------
    entry = {
        "zotero_key": key,
        "domain": domain,
        "title": item["title"],
        "authors": item.get("authors", []),
        "abstract": item.get("abstract", ""),
        "journal": item.get("journal", ""),
        "year": item.get("year", ""),
        "doi": item.get("doi", ""),
        "pmid": item.get("pmid", ""),
        "collection_path": " | ".join(item.get("collections", [])),
        "collections": collection_meta.get("collections", []),
        "collection_tags": collection_meta.get("collection_tags", []),
        "collection_group": collection_meta.get("collection_group", []),
        "has_pdf": bool(pdf_attachments),
        "pdf_path": (
            obsidian_wikilink_for_pdf(pdf_attachments[0]["path"], vault, zotero_dir)
            if pdf_attachments
            else ""
        ),
        "ocr_status": meta.get("ocr_status", "pending"),
        "ocr_job_id": meta.get("ocr_job_id", ""),
        "ocr_md_path": obsidian_wikilink_for_path(vault, meta.get("markdown_path", "")),
        "ocr_json_path": meta.get("json_path", ""),
        "deep_reading_status": (
            "done"
            if note_path.exists() and has_deep_reading_content(note_path.read_text(encoding="utf-8"))
            else "pending"
        ),
        "note_path": str(note_path.relative_to(vault)).replace("\\", "/"),
        "deep_reading_md_path": (
            str(note_path.relative_to(vault)).replace("\\", "/")
            if note_path.exists() and has_deep_reading_content(note_path.read_text(encoding="utf-8"))
            else ""
        ),
        # Workspace path fields (Phase 22 paper workspace structure, per D-12)
        "paper_root": f"Literature/{domain}/{key} - {title_slug}/",
        "main_note_path": f"Literature/{domain}/{key} - {title_slug}/{key} - {title_slug}.md",
        "fulltext_path": f"Literature/{domain}/{key} - {title_slug}/fulltext.md",
        "deep_reading_path": f"Literature/{domain}/{key} - {title_slug}/deep-reading.md",
        "ai_path": f"Literature/{domain}/{key} - {title_slug}/ai/",
    }

    # Write / update the formal note
    note_path.parent.mkdir(parents=True, exist_ok=True)
    existing_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
    note_path.write_text(frontmatter_note(entry, existing_text), encoding="utf-8")

    return entry


# ---------------------------------------------------------------------------
# Full index build
# ---------------------------------------------------------------------------


def build_index(vault: Path, verbose: bool = False) -> int:
    """Full rebuild of the canonical asset index for *vault*.

    This function is the core build loop:
    1. Reads all Better BibTeX export JSON files.
    2. For each paper entry, delegates to ``_build_entry()`` for metadata
       collection and formal note writing.
    3. Wraps the entries in a versioned envelope.
    4. Writes the index atomically via ``atomic_write_index``.

    The orphaned-record cleanup that follows in ``run_index_refresh()`` is
    **not** included here.

    Returns:
        Number of items written to the index.
    """
    # Lazy imports to avoid circular dependencies with sync.py
    from paperforge.config import load_vault_config
    from paperforge.worker._utils import pipeline_paths, read_json  # noqa: F811
    from paperforge.worker.base_views import ensure_base_views
    from paperforge.worker.sync import load_domain_config, load_export_rows

    paths = pipeline_paths(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)

    # Legacy format migration — detect bare-list format and back up before rebuild
    migrated = migrate_legacy_index(vault)
    if migrated:
        print("Legacy index format detected and backed up. Rebuilding with envelope...")

    # Schema version check — mismatch triggers full rebuild
    existing_data = read_index(vault)
    if isinstance(existing_data, dict) and existing_data.get("schema_version") != CURRENT_SCHEMA_VERSION:
        print(
            f"Schema version mismatch: index has {existing_data.get('schema_version')}, "
            f"need {CURRENT_SCHEMA_VERSION}. Rebuilding..."
        )

    cfg = load_vault_config(vault)
    zotero_dir = vault / cfg.get("system_dir", "99_System") / "Zotero"

    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

    index_rows: list[dict] = []

    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        for item in export_rows:
            entry = _build_entry(item, vault, paths, domain, zotero_dir)
            index_rows.append(entry)

    # Atomically write the envelope-wrapped index
    index_path = paths["index"]
    envelope = build_envelope(index_rows)
    atomic_write_index(index_path, envelope)
    print(f"index-refresh: wrote {len(index_rows)} index rows")
    return len(index_rows)


# ---------------------------------------------------------------------------
# Incremental refresh
# ---------------------------------------------------------------------------


def refresh_index_entry(vault: Path, key: str) -> bool:
    """Incrementally refresh a single index entry identified by *key*.

    *key* is the Zotero citation key (8-character alphanumeric).

    Behaviour:
    * If the index does not exist → delegates to ``build_index()`` (full rebuild).
    * If the index is in legacy bare-list format → delegates to ``build_index()``.
    * If the index is envelope format:
        1. Reads the existing ``items`` list.
        2. Finds the entry whose ``zotero_key`` matches *key*.
        3. Rebuilds that single entry via ``_build_entry()`` (same code path
           as a full rebuild, guaranteeing field consistency).
        4. If *key* is not found in the items list, builds a new entry and
           appends it (handles newly-synced papers).
        5. Writes the updated envelope back atomically.

    Returns:
        ``True`` if incremental refresh was performed,
        ``False`` if a full rebuild was triggered instead.
    """
    from paperforge.config import load_vault_config
    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.sync import load_domain_config, load_export_rows

    paths = pipeline_paths(vault)

    # Read existing index
    existing = read_index(vault)
    if existing is None:
        build_index(vault)
        return False

    if is_legacy_format(existing):
        build_index(vault)
        return False

    # Envelope format — incremental refresh
    items = existing.get("items", [])

    # Find the export item for the requested key
    config = load_domain_config(paths)
    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}
    cfg = load_vault_config(vault)
    zotero_dir = vault / cfg.get("system_dir", "99_System") / "Zotero"

    found_item = None
    found_domain = ""
    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        for item in export_rows:
            if item["key"] == key:
                found_item = item
                found_domain = domain
                break
        if found_item:
            break

    if found_item is None:
        logger.warning("Key %s not found in any export — cannot refresh", key)
        return False

    # Build single entry and update the items list
    new_entry = _build_entry(found_item, vault, paths, found_domain, zotero_dir)

    replaced = False
    for i, existing_entry in enumerate(items):
        if existing_entry.get("zotero_key") == key:
            items[i] = new_entry
            replaced = True
            break
    if not replaced:
        items.append(new_entry)

    # Write back atomically
    index_path = paths["index"]
    envelope = build_envelope(items)
    atomic_write_index(index_path, envelope)
    logger.info("refresh_index_entry: updated entry %s (%s)", key, found_domain)
    return True
