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
from datetime import datetime
from pathlib import Path

import filelock

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
        "generated_at": datetime.utcnow().isoformat() + "Z",
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
# Full index build  (extracted from sync.run_index_refresh)
# ---------------------------------------------------------------------------


def build_index(vault: Path, verbose: bool = False) -> int:
    """Full rebuild of the canonical asset index for *vault*.

    This function is extracted from the legacy ``sync.run_index_refresh()``
    loop (lines 1686-1746 of sync.py).  It:

    1. Reads all Better BibTeX export JSON files.
    2. For each paper entry, gathers metadata (OCR, deep-reading status,
       PDF paths, etc.) and writes/updates the formal Obsidian note.
    3. Builds a list of entry dicts.
    4. Writes the canonical index via ``atomic_write_index`` with the
       versioned envelope.

    The orphaned-record cleanup that follows in ``run_index_refresh()`` is
    **not** included here.

    Returns:
        Number of items written to the index.
    """
    # Lazy imports to avoid circular dependencies — sync.py imports this
    # module at module level, so importing from sync.py at module level
    # here would cause a circular import.
    from paperforge.config import load_vault_config
    from paperforge.worker._utils import pipeline_paths, read_json, slugify_filename, write_json  # noqa: F811
    from paperforge.worker.base_views import ensure_base_views
    from paperforge.worker.ocr import validate_ocr_meta
    from paperforge.worker.sync import (
        collection_fields,
        frontmatter_note,
        has_deep_reading_content,
        load_domain_config,
        load_export_rows,
        obsidian_wikilink_for_path,
        obsidian_wikilink_for_pdf,
    )

    paths = pipeline_paths(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)
    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

    cfg = load_vault_config(vault)
    zotero_dir = vault / cfg.get("system_dir", "99_System") / "Zotero"

    index_rows: list[dict] = []
    lit_root = paths["literature"]

    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        for item in export_rows:
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
            note_path = lit_root / domain / f"{key} - {title_slug}.md"
            if note_path.parent.exists():
                for stale_note in note_path.parent.glob(f"{key} - *.md"):
                    if stale_note != note_path:
                        stale_note.unlink()
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
            }
            note_path.parent.mkdir(parents=True, exist_ok=True)
            existing_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
            note_path.write_text(frontmatter_note(entry, existing_text), encoding="utf-8")
            index_rows.append(entry)

    # Atomically write the envelope-wrapped index
    index_path = paths["index"]
    envelope = build_envelope(index_rows)
    atomic_write_index(index_path, envelope)
    print(f"index-refresh: wrote {len(index_rows)} index rows")
    return len(index_rows)
