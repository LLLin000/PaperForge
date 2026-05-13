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
import re
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import filelock

from paperforge import __version__ as _paperforge_version
from paperforge.adapters.obsidian_frontmatter import (
    _legacy_control_flags,
    read_frontmatter_dict,
    read_frontmatter_optional_bool,
)
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
            "paperforge_version": "1.8.0",
            "items": items,
        }
    """
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "paper_count": len(items),
        "paperforge_version": _paperforge_version,
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
        with open(path, encoding="utf-8") as fh:
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
# ── Single-entry builder (shared by full rebuild and incremental refresh) ──
# read_frontmatter_bool / read_frontmatter_optional_bool imported from adapters


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
    import shutil

    from paperforge import __version__ as PAPERFORGE_VERSION
    from paperforge.worker._utils import lookup_impact_factor, read_json, slugify_filename, write_json, yaml_quote
    from paperforge.worker.asset_state import (
        compute_health,
        compute_lifecycle,
        compute_maturity,
        compute_next_step,
    )
    from paperforge.worker.ocr import validate_ocr_meta
    from paperforge.worker.paper_meta import write_paper_meta
    from paperforge.worker.sync import (
        collection_fields,
        frontmatter_note,
        has_deep_reading_content,
        obsidian_wikilink_for_path,
        obsidian_wikilink_for_pdf,
    )

    key = item["key"]
    collection_meta = collection_fields(item.get("collections", []))
    pdf_attachments = [a for a in item.get("attachments", []) if a.get("contentType") == "application/pdf"]
    meta_path = paths["ocr"] / key / "meta.json"
    meta = read_json(meta_path) if meta_path.exists() else {}
    if meta:
        validated_ocr_status, validated_error = validate_ocr_meta(paths, meta)
        meta["ocr_status"] = validated_ocr_status
        if validated_error:
            meta["error"] = validated_error
            write_json(meta_path, meta)
    title_slug = slugify_filename(item["title"])
    note_path = paths["literature"] / domain / f"{key}.md"

    # --- Freeze slug: reuse existing workspace if it exists under a different slug ---
    workspace_dir = paths["literature"] / domain / f"{key} - {title_slug}"
    if not workspace_dir.exists():
        for candidate in (paths["literature"] / domain).glob(f"{key} - *"):
            if candidate.is_dir():
                workspace_dir = candidate
                title_slug = workspace_dir.name.split(" - ", 1)[1] if " - " in workspace_dir.name else title_slug
                break

    if note_path.parent.exists():
        for stale_note in note_path.parent.glob(f"{key}*.md"):
            if stale_note != note_path:
                stale_note.unlink()

    # Workspace paths (Phase 26: flat-to-workspace migration)
    main_note_path = workspace_dir / f"{key}.md"

    # Self-healing migration: rename old-format {key} - {title}.md -> {key}.md
    if not main_note_path.exists():
        for old_candidate in workspace_dir.glob(f"{key} - *.md"):
            old_candidate.rename(main_note_path)
            # Inject alias into frontmatter
            try:
                text = main_note_path.read_text(encoding="utf-8")
                if "aliases:" not in text[: text.find("\n---", 4)]:
                    alias_line = f"aliases: [{yaml_quote(item.get('title', ''))}, {yaml_quote(item.get('citation_key') or item.get('key', ''))}]\n"
                    text = re.sub(
                        r"(^title:.*\n)",
                        r"\1" + alias_line,
                        text,
                        count=1,
                        flags=re.MULTILINE,
                    )
                    main_note_path.write_text(text, encoding="utf-8")
            except Exception:
                pass  # alias will be injected on next full frontmatter_note pass
            break  # only one old file per key
    deep_reading_file = workspace_dir / "deep-reading.md"
    target_fulltext = workspace_dir / "fulltext.md"
    source_fulltext = paths["ocr"] / key / "fulltext.md"

    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "ai").mkdir(parents=True, exist_ok=True)
    if meta.get("ocr_status") == "done" and source_fulltext.exists() and not target_fulltext.exists():
        shutil.copy2(str(source_fulltext), str(target_fulltext))
        logger.info("Bridged fulltext.md to workspace for %s", key)

    fulltext_exists = target_fulltext.exists()
    deep_reading_exists = deep_reading_file.exists()

    # ---- entry dict -------------------------------------------------------
    authors = item.get("authors", [])
    first_author = authors[0] if authors else ""
    extra = item.get("extra", "")
    impact_factor = lookup_impact_factor(item.get("journal", ""), extra, vault)
    legacy_flags = _legacy_control_flags(paths, key)
    legacy_do_ocr = legacy_flags.get("do_ocr")
    legacy_analyze = legacy_flags.get("analyze")
    note_do_ocr = read_frontmatter_optional_bool(main_note_path, "do_ocr")
    if note_do_ocr is None:
        note_do_ocr = read_frontmatter_optional_bool(note_path, "do_ocr")
    note_analyze = read_frontmatter_optional_bool(main_note_path, "analyze")
    if note_analyze is None:
        note_analyze = read_frontmatter_optional_bool(note_path, "analyze")

    # deep_reading_status: frontmatter first (finalize.py sets it), body detection fallback (sync ensures it)
    def _read_fm_str(fp: Path, key: str) -> str:
        if not fp or not fp.exists():
            return ""
        try:
            fm = read_frontmatter_dict(fp.read_text(encoding="utf-8"))
            return str(fm.get(key, "")).strip()
        except Exception:
            return ""

    note_dr = _read_fm_str(main_note_path, "deep_reading_status")
    if not note_dr:
        note_dr = _read_fm_str(note_path, "deep_reading_status")

    do_ocr_value = note_do_ocr if note_do_ocr is not None else legacy_do_ocr
    if do_ocr_value is None:
        do_ocr_value = meta.get("do_ocr") is True or meta.get("ocr_status") == "done"

    analyze_value = note_analyze if note_analyze is not None else legacy_analyze
    if analyze_value is None:
        analyze_value = meta.get("analyze") is True or meta.get("deep_reading_status") == "done"

    entry = {
        "zotero_key": key,
        "citation_key": item.get("citation_key", ""),
        "domain": domain,
        "title": item["title"],
        "authors": authors,
        "first_author": first_author,
        "abstract": item.get("abstract", ""),
        "journal": item.get("journal", ""),
        "impact_factor": impact_factor,
        "year": item.get("year", ""),
        "doi": item.get("doi", ""),
        "pmid": item.get("pmid", ""),
        "collection_path": " | ".join(item.get("collections", [])),
        "collections": collection_meta.get("collections", []),
        "collection_tags": collection_meta.get("collection_tags", []),
        "collection_group": collection_meta.get("collection_group", []),
        "has_pdf": bool(pdf_attachments),
        "do_ocr": do_ocr_value,
        "analyze": analyze_value,
        "pdf_path": (
            obsidian_wikilink_for_pdf(pdf_attachments[0]["path"], vault, zotero_dir) if pdf_attachments else ""
        ),
        "ocr_status": meta.get("ocr_status", "pending"),
        "ocr_job_id": meta.get("ocr_job_id", ""),
        "ocr_md_path": obsidian_wikilink_for_path(vault, meta.get("markdown_path", "")),
        "ocr_json_path": meta.get("json_path", ""),
        "deep_reading_status": (
            "done"
            if note_dr == "done"
            else "done"
            if main_note_path.exists() and has_deep_reading_content(main_note_path.read_text(encoding="utf-8"))
            else "done"
            if note_path.exists() and has_deep_reading_content(note_path.read_text(encoding="utf-8"))
            else "pending"
        ),
        "note_path": str((main_note_path if main_note_path.exists() else note_path).relative_to(vault)).replace(
            "\\", "/"
        ),
        "deep_reading_md_path": (
            str(main_note_path.relative_to(vault)).replace("\\", "/")
            if main_note_path.exists() and has_deep_reading_content(main_note_path.read_text(encoding="utf-8"))
            else str(note_path.relative_to(vault)).replace("\\", "/")
            if note_path.exists() and has_deep_reading_content(note_path.read_text(encoding="utf-8"))
            else ""
        ),
        # Workspace path fields are only advertised when the backing files/dirs exist.
        "paper_root": str(workspace_dir.relative_to(vault)).replace("\\", "/") + "/",
        "main_note_path": str(main_note_path.relative_to(vault)).replace("\\", "/"),
        "fulltext_path": str(target_fulltext.relative_to(vault)).replace("\\", "/") if fulltext_exists else "",
        "deep_reading_path": "",  # deprecated: deep reading content now lives in main note as ## 🔍 精读
        "ai_path": str((workspace_dir / "ai").relative_to(vault)).replace("\\", "/") + "/",
    }

    # ---- derived state (Phase 24: lifecycle, health, maturity, next-step) ----
    entry["lifecycle"] = str(compute_lifecycle(entry))
    entry["health"] = compute_health(entry)
    entry["maturity"] = compute_maturity(entry)
    entry["next_step"] = compute_next_step(entry)

    # Slug already frozen above — for existing notes, update frontmatter only (preserve body)
    if main_note_path.exists():
        text = main_note_path.read_text(encoding="utf-8")
        fm_close = text.find("---\n", 4)  # closing --- after opening ---
        if fm_close != -1:
            body = text[fm_close + 4 :]  # everything after frontmatter
            new_full = frontmatter_note(entry, "")
            new_fm_close = new_full.find("---\n", 4)
            if new_fm_close != -1:
                new_fm = new_full[: new_fm_close + 4]  # new frontmatter block with closing ---\n
                main_note_path.write_text(new_fm + body, encoding="utf-8")
            else:
                main_note_path.write_text(new_full, encoding="utf-8")
        else:
            main_note_path.write_text(frontmatter_note(entry, text), encoding="utf-8")
    else:
        existing_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        main_note_path.write_text(frontmatter_note(entry, existing_text), encoding="utf-8")

    # Write per-workspace paper-meta.json (Phase 37: internal state outside frontmatter)
    write_paper_meta(workspace_dir, entry, paperforge_version=PAPERFORGE_VERSION)

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
    from paperforge.worker._utils import pipeline_paths  # noqa: F811
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
    zotero_dir = vault / cfg.get("system_dir", "System") / "Zotero"

    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

    index_rows: list[dict] = []

    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        for item in export_rows:
            entry = _build_entry(item, vault, paths, domain, zotero_dir)
            index_rows.append(entry)
            try:
                from paperforge.memory.refresh import refresh_paper

                refresh_paper(vault, entry)
            except Exception:
                pass  # memory DB refresh is best-effort

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
    zotero_dir = vault / cfg.get("system_dir", "System") / "Zotero"

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

    try:
        from paperforge.memory.refresh import refresh_paper

        refresh_paper(vault, new_entry)
    except Exception:
        pass  # memory DB refresh is best-effort

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


# ---------------------------------------------------------------------------
# Index summarization  (Phase 25: consumed by status --json and doctor)
# ---------------------------------------------------------------------------


def summarize_index(vault: Path) -> dict | None:
    """Read the canonical index and return summary aggregates.

    Returns a dict with lifecycle counts, per-dimension health counts,
    and maturity distribution — or ``None`` if the index is missing,
    corrupt, or in legacy bare-list format.

    The caller (``status.py``) handles filesystem fallback when this
    returns ``None``.

    Return shape::

        {
            "paper_count": int,
            "lifecycle_level_counts": {
                "indexed": int,
                "pdf_ready": int,
                "fulltext_ready": int,
                "deep_read_done": int,
                "ai_context_ready": int,
            },
            "health_aggregate": {
                "pdf_health": {"healthy": int, "unhealthy": int},
                "ocr_health": {"healthy": int, "unhealthy": int},
                "note_health": {"healthy": int, "unhealthy": int},
                "asset_health": {"healthy": int, "unhealthy": int},
            },
            "maturity_distribution": {
                "1": int, "2": int, "3": int,
                "4": int, "5": int, "6": int,
            },
        }
    """
    data = read_index(vault)
    if data is None:
        return None
    if is_legacy_format(data):
        return None

    items = data.get("items", []) if isinstance(data, dict) else []

    # Pre-seeded empty counts
    lifecycle_counts: dict[str, int] = {
        "indexed": 0,
        "pdf_ready": 0,
        "fulltext_ready": 0,
        "deep_read_done": 0,
        "ai_context_ready": 0,
    }
    health_keys = ["pdf_health", "ocr_health", "note_health", "asset_health"]
    health_agg: dict[str, dict[str, int]] = {k: {"healthy": 0, "unhealthy": 0} for k in health_keys}
    maturity_dist: dict[str, int] = {str(i): 0 for i in range(1, 7)}

    for entry in items:
        if not isinstance(entry, dict):
            continue

        # Lifecycle
        lc = entry.get("lifecycle", "pdf_ready")
        if lc in lifecycle_counts:
            lifecycle_counts[lc] += 1
        else:
            lifecycle_counts["pdf_ready"] += 1

        # Health
        health: dict = entry.get("health", {})
        for hk in health_keys:
            val = health.get(hk, "healthy") if isinstance(health, dict) else "healthy"
            if val == "healthy":
                health_agg[hk]["healthy"] += 1
            else:
                health_agg[hk]["unhealthy"] += 1

        # Maturity
        maturity: dict = entry.get("maturity", {})
        level = maturity.get("level", 1) if isinstance(maturity, dict) else 1
        level_str = str(min(max(int(level), 1), 6))
        maturity_dist[level_str] += 1

    return {
        "paper_count": len(items),
        "lifecycle_level_counts": lifecycle_counts,
        "health_aggregate": health_agg,
        "maturity_distribution": maturity_dist,
    }
