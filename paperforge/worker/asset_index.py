"""Canonical literature asset index -- envelope format, atomic writes, cross-process locking.

This module is the single canonical home for generating and writing the
literature asset index (``formal-library.json``).  Responsibilities:

* ``get_index_path(vault)`` -- resolve the index file location.
* ``build_envelope(items)`` -- wrap a list of paper entries in a versioned
  envelope (schema_version, generated_at, paper_count).
* ``atomic_write_index(path, data)`` -- write index JSON atomically using
  ``tempfile.NamedTemporaryFile`` + ``os.replace``, protected by a
  ``filelock`` cross-process lock (10 s timeout).
* ``build_index(vault, verbose)`` -- full index rebuild extracted from the
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

import copy
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import filelock

from paperforge import __version__ as _paperforge_version
from paperforge.adapters.obsidian_frontmatter import (
    _legacy_control_flags,
    extract_preserved_tags,
    read_frontmatter_dict,
    split_frontmatter_block,
)
from paperforge.config import paperforge_paths
from paperforge.core.io import write_text_atomic
from paperforge.core.stat_cache import RACY_WINDOW_NS

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


def _index_lock(path: Path) -> filelock.FileLock:
    return filelock.FileLock(path.with_suffix(".json.lock"), timeout=LOCK_TIMEOUT)


def mutate_index(vault: Path, mutator) -> bool:
    """Read, mutate, and write the canonical index under one lock."""
    path = get_index_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _index_lock(path):
        if not path.exists():
            return False
        try:
            with open(path, encoding="utf-8") as fh:
                current = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt index at %s during mutation: %s", path, exc)
            return False

        updated = mutator(current)
        if updated is None:
            return False

        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=path.parent)
        try:
            json.dump(updated, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, path)
            _invalidate_read_cache(path)
            try:
                from paperforge.services.state_signal import bump_state_seq_in_dir

                bump_state_seq_in_dir(path.parent, reason="index.write")
            except Exception:
                pass
        except BaseException:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise
    return True


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


def build_envelope(items: list[dict], export_hash: str = "") -> dict:
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
        "export_hash": export_hash,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


_INDEX_READ_CACHE_LOCK = threading.Lock()
_INDEX_READ_CACHE: dict[str, tuple[int, int, dict | list]] = {}


def _invalidate_read_cache(path: Path) -> None:
    key = str(path.resolve(strict=False))
    with _INDEX_READ_CACHE_LOCK:
        _INDEX_READ_CACHE.pop(key, None)


def atomic_write_index(path: Path, data: dict) -> None:
    """Write *data* as JSON to *path* atomically with cross-process locking.

    Steps:
    1. Create parent directory if it does not exist.
    2. Acquire a ``filelock`` on ``<path>.lock`` with a 10-second timeout.
    3. Write to a temporary file in the same directory (same-filesystem for
       Windows-safe ``os.replace``).
    4. ``os.replace(temp.name, path)`` -- atomic on both POSIX and Windows.
    5. On failure: clean up the temp file before propagating.

    Raises:
        filelock.Timeout: If the lock cannot be acquired within
            *LOCK_TIMEOUT* seconds.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with _index_lock(path):
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
            _invalidate_read_cache(path)
            try:
                from paperforge.services.state_signal import bump_state_seq_in_dir

                bump_state_seq_in_dir(path.parent, reason="index.write")
            except Exception:
                pass
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
        _invalidate_read_cache(path)
        return None
    cache_key = str(path.resolve(strict=False))
    try:
        st = path.stat()
    except OSError as exc:
        logger.warning("Stat failed for index at %s: %s", path, exc)
        return None
    is_racy = abs(time.time_ns() - st.st_mtime_ns) < RACY_WINDOW_NS
    sig = (int(st.st_size), int(st.st_mtime_ns))
    if not is_racy:
        with _INDEX_READ_CACHE_LOCK:
            cached = _INDEX_READ_CACHE.get(cache_key)
            if cached is not None and cached[:2] == sig:
                return copy.deepcopy(cached[2])
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not is_racy:
            with _INDEX_READ_CACHE_LOCK:
                _INDEX_READ_CACHE[cache_key] = (sig[0], sig[1], copy.deepcopy(data))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupt index at %s, treating as missing: %s", path, exc)
        _invalidate_read_cache(path)
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

    The backup is idempotent -- calling repeatedly overwrites the previous
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
    # #137: human logs -> stderr; stdout carries machine output only.
    print(f"Legacy format detected at {path}, backed up to {bak_path}", file=sys.stderr)
    return True


# ---------------------------------------------------------------------------
# ── Single-entry builder (shared by full rebuild and incremental refresh) ──
# read_frontmatter_bool / read_frontmatter_optional_bool imported from adapters


def _build_entry(
    item: dict,
    vault: Path,
    paths: dict,
    domain: str,
    zotero_dir: Path,
    *,
    active_domain_keys: dict[str, set[str]] | None = None,
) -> dict:
    """Construct a single canonical index entry from a BBT export *item*.

    This helper is used by both ``build_index()`` (all items) and
    ``refresh_index_entry()`` (single item).  It:

    1. Gathers OCR meta, PDF paths, deep-reading state.
    2. Writes / updates the formal Obsidian note via ``frontmatter_note()``.
    3. Returns the entry dict with all fields (including workspace paths).

    Lazy imports inside avoid circular dependencies with ``sync.py``.
    """
    # Lazy imports to avoid circular deps with sync.py

    from paperforge import __version__ as PAPERFORGE_VERSION
    from paperforge.adapters.obsidian_frontmatter import has_deep_reading_content
    from paperforge.worker._utils import lookup_impact_factor, read_json, slugify_filename, yaml_quote
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
        obsidian_wikilink_for_path,
        obsidian_wikilink_for_pdf,
    )

    key = item["key"]
    collection_meta = collection_fields(item.get("collections", []))
    pdf_attachments = [a for a in item.get("attachments", []) if a.get("contentType") == "application/pdf"]
    # #135: the canonical index must pick the SAME main PDF as the paper DB —
    # identify_main_pdf (title=="PDF" > largest > shortest > first), never
    # blindly attachments[0] (a paper with two PDFs would surface a
    # different one in the dashboard than in paper-status).
    from paperforge.adapters.bbt import identify_main_pdf

    main_pdf, _supplementary = identify_main_pdf(pdf_attachments)
    main_pdf_path = main_pdf["path"] if main_pdf else (pdf_attachments[0]["path"] if pdf_attachments else "")
    meta_path = paths["ocr"] / key / "meta.json"
    # SSOT boundary (2026-08-16): OCR meta.json's ONLY writer is the OCR
    # subsystem.  The index builder is a READ-ONLY consumer:
    # - meta unreadable (restore corruption) → treat OCR state as
    #   UNOBSERVABLE — continue the refresh, never throw, never "repair"
    #   the file by writing an empty/derived meta back over it;
    # - validated errors are consumed into the index entry, not written
    #   back into the OCR meta.
    meta = None
    _meta_unreadable = False
    if meta_path.exists():
        try:
            meta = read_json(meta_path)
        except Exception:  # noqa: BLE001 — unreadable meta = unobservable
            meta = None
            _meta_unreadable = True
    validated_ocr_status = "pending"
    if meta:
        validated_ocr_status, validated_error = validate_ocr_meta(paths, meta)
        # NOTE: validated_error is carried on the index entry only; the
        # OCR meta file is never written here.
    # absent meta = never ran → pending; unreadable meta = unobservable.
    ocr_status_field = validated_ocr_status if meta is not None else ("unknown" if _meta_unreadable else "pending")
    title_slug = slugify_filename(item["title"])
    note_path = paths["literature"] / domain / f"{key}.md"

    # --- Freeze slug & migrate moved workspace across renamed domains ---
    workspace_dir = paths["literature"] / domain / f"{key} - {title_slug}"
    if not workspace_dir.exists():
        found_in_domain = False
        for candidate in (paths["literature"] / domain).glob(f"{key} - *"):
            if candidate.is_dir():
                workspace_dir = candidate
                title_slug = workspace_dir.name.split(" - ", 1)[1] if " - " in workspace_dir.name else title_slug
                found_in_domain = True
                break
        if not found_in_domain and paths["literature"].exists():
            moved_candidates: list[Path] = []
            for other_dir in sorted(paths["literature"].iterdir()):
                if not other_dir.is_dir() or other_dir.name == domain:
                    continue
                if active_domain_keys is not None and key in active_domain_keys.get(other_dir.name, set()):
                    continue
                for candidate in other_dir.glob(f"{key} - *"):
                    if candidate.is_dir():
                        moved_candidates.append(candidate)
            if len(moved_candidates) == 1:
                old_ws = moved_candidates[0]
                target_ws = paths["literature"] / domain / old_ws.name
                if not target_ws.exists():
                    target_ws.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_ws), str(target_ws))
                    workspace_dir = target_ws
                    title_slug = (
                        workspace_dir.name.split(" - ", 1)[1]
                        if " - " in workspace_dir.name
                        else title_slug
                    )

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
                    write_text_atomic(main_note_path, text)
            except Exception:
                pass  # alias will be injected on next full frontmatter_note pass
            break  # only one old file per key
    source_fulltext = paths["ocr"] / key / "fulltext.md"
    stale_workspace_fulltext = workspace_dir / "fulltext.md"
    hidden_engine = Path(str(paths["paperforge"])).name == ".paperforge"

    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "ai").mkdir(parents=True, exist_ok=True)
    # Materialize per-paper cropped visual assets (<KEY>_figure_001.jpg, <KEY>_table_001.jpg)
    # inside <workspace>/assets/ so Obsidian displays images natively without scanning .paperforge/.
    sync_workspace_visual_assets(paths["ocr"] / key, workspace_dir, key)
    # ponytail: size + mtime guard avoids I/O on unchanged fulltext.
    # When engine lives in hidden .paperforge/, keep fulltext internal (never expose workspace copy).
    if hidden_engine or not source_fulltext.exists():
        if stale_workspace_fulltext.exists():
            stale_workspace_fulltext.unlink()
    else:
        try:
            src = source_fulltext.stat()
            dst = stale_workspace_fulltext.stat() if stale_workspace_fulltext.exists() else None
        except OSError:
            dst = None
        fulltext_changed = (
            dst is None
            or src.st_size != dst.st_size
            or src.st_mtime_ns != dst.st_mtime_ns
        )
        if fulltext_changed:
            if stale_workspace_fulltext.exists():
                stale_workspace_fulltext.unlink()
            shutil.copy2(str(source_fulltext), str(stale_workspace_fulltext))

    fulltext_exists = source_fulltext.exists()

    # ---- entry dict -------------------------------------------------------
    authors = item.get("authors", [])
    first_author = authors[0] if authors else ""
    extra = item.get("extra", "")
    impact_factor = lookup_impact_factor(item.get("journal", ""), extra, vault)
    legacy_flags = _legacy_control_flags(paths, key)
    legacy_do_ocr = legacy_flags.get("do_ocr")
    legacy_analyze = legacy_flags.get("analyze")
    # Single frontmatter read for all control fields -- cache text for reuse
    fm = {}
    fm_cached_text = ""
    fm_was_main = False
    for fp in (main_note_path, note_path):
        if fp and fp.exists():
            try:
                note_text = fp.read_text(encoding="utf-8")
                fm = read_frontmatter_dict(note_text)
                fm_cached_text = note_text
                fm_was_main = (fp == main_note_path)
                break
            except Exception:
                continue

    _v = fm.get("do_ocr")
    note_do_ocr = _v if isinstance(_v, bool) else None
    _v = fm.get("analyze")
    note_analyze = _v if isinstance(_v, bool) else None
    note_dr = str(fm.get("deep_reading_status", "")).strip()
    _v = fm.get("ocr_redo")
    note_ocr_redo = _v if isinstance(_v, bool) else False

    do_ocr_value = note_do_ocr if note_do_ocr is not None else legacy_do_ocr
    if do_ocr_value is None:
        _m = meta or {}
        do_ocr_value = _m.get("do_ocr") is True or ocr_status_field == "done"

    analyze_value = note_analyze if note_analyze is not None else legacy_analyze
    if analyze_value is None:
        _m = meta or {}
        analyze_value = _m.get("analyze") is True or _m.get("deep_reading_status") == "done"

    # Compute deep reading status once, reusing cached text when possible.
    # main_note_path is canonical -- don't fall back to note_path when it exists.
    _dr_status = "pending"
    if note_dr == "done":
        _dr_status = "done"
    elif fm_was_main:
        _dr_status = "done" if has_deep_reading_content(fm_cached_text) else "pending"
    elif main_note_path.exists():
        try:
            _dr_status = "done" if has_deep_reading_content(main_note_path.read_text(encoding="utf-8")) else "pending"
        except Exception:
            pass

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
            obsidian_wikilink_for_pdf(main_pdf_path, vault, zotero_dir) if main_pdf_path else ""
        ),
        "ocr_status": ocr_status_field,
        "ocr_job_id": (meta or {}).get("ocr_job_id", ""),
        "ocr_md_path": obsidian_wikilink_for_path(vault, (meta or {}).get("markdown_path", "")),
        "ocr_json_path": (meta or {}).get("json_path", ""),
        "deep_reading_status": _dr_status,
        "ocr_redo": note_ocr_redo,
        "ocr_time": (meta or {}).get("ocr_finished_at", ""),
        "note_path": str((main_note_path if main_note_path.exists() else note_path).relative_to(vault)).replace(
            "\\", "/"
        ),
        "deep_reading_md_path": (
            str(main_note_path.relative_to(vault)).replace("\\", "/")
            if _dr_status == "done" and main_note_path.exists()
            else str(note_path.relative_to(vault)).replace("\\", "/")
            if _dr_status == "done" and note_path.exists()
            else ""
        ),
        # Workspace path fields are only advertised when the backing files/dirs exist.
        "paper_root": str(workspace_dir.relative_to(vault)).replace("\\", "/") + "/",
        "main_note_path": str(main_note_path.relative_to(vault)).replace("\\", "/"),
        "fulltext_path": str(source_fulltext.relative_to(vault)).replace("\\", "/") if fulltext_exists else "",
        "deep_reading_path": "",  # deprecated: deep reading content now lives in main note as ## 🔍 精读
        "ai_path": str((workspace_dir / "ai").relative_to(vault)).replace("\\", "/") + "/",
    }

    # ---- derived state (Phase 24: lifecycle, health, maturity, next-step) ----
    entry["lifecycle"] = str(compute_lifecycle(entry))
    entry["health"] = compute_health(entry)
    entry["maturity"] = compute_maturity(entry)
    entry["next_step"] = compute_next_step(entry)

    # Slug already frozen above -- for existing notes, update frontmatter only (preserve body)
    if main_note_path.exists():
        try:
            text = fm_cached_text if fm_was_main else main_note_path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 — corrupt restored note: skip rewrite
            text = None
        if text is not None:
            split_old = split_frontmatter_block(text)
            if split_old is not None:
                _old_fm, body = split_old
                preserved_tags = extract_preserved_tags(text)
                new_full = frontmatter_note(entry, text, preserved_tags=preserved_tags)
                split_new = split_frontmatter_block(new_full)
                if split_new is not None:
                    new_fm, _ = split_new
                    target_text = new_fm + body
                else:
                    target_text = new_full
            else:
                target_text = frontmatter_note(entry, text)
            if target_text != text:
                write_text_atomic(main_note_path, target_text)
    else:
        existing_text = fm_cached_text if not fm_was_main and fm_cached_text else (
            note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        )
        write_text_atomic(main_note_path, frontmatter_note(entry, existing_text))

    # Write per-workspace paper-meta.json (Phase 37: internal state outside frontmatter)
    write_paper_meta(workspace_dir, entry, paperforge_version=PAPERFORGE_VERSION)

    return entry


def _vec_auto_embed_if_new(vault: Path, entry: dict) -> None:
    """Auto-embed a paper into vector DB if OCR is done and vectors missing."""
    if entry.get("ocr_status") != "done":
        return
    fulltext_rel = entry.get("fulltext_path", "")
    if not fulltext_rel:
        return
    fulltext_path = vault / fulltext_rel
    if not fulltext_path.exists():
        return
    # Check if vector DB is enabled and set up
    try:
        from paperforge.embedding import embed_paper
        from paperforge.embedding._config import _read_plugin_settings
        from paperforge.embedding.substrate import assess_vector_substrate
        from paperforge.memory.chunker import chunk_fulltext
        settings = _read_plugin_settings(vault)
        if not settings.get("features", {}).get("vector_db", False):
            return
        # Missing vec0 substrate means vectors were never built — auto-embed
        # on ingest rebuilds exactly that case (embed.build --force covers
        # the explicit path).  Never silently skip a configured feature.
        # Absent/incompatible substrate routes to an explicit embed.build;
        # auto-embed must not silently manufacture vectors here.
        if not assess_vector_substrate(vault).compatible:
            return
        chunks = chunk_fulltext(fulltext_path)
        if not chunks:
            return
        embed_paper(vault, entry["zotero_key"], chunks)
    except Exception:
        pass  # model not installed -- silently skip

# ---------------------------------------------------------------------------
# Full index build
# ---------------------------------------------------------------------------


def _compute_export_hash(paths: dict) -> str:
    import hashlib

    h = hashlib.sha256()
    for p in sorted(paths["exports"].glob("*.json")):
        h.update(p.read_bytes())
    return h.hexdigest()


def compute_export_hash(paths: dict) -> str:
    """Public read-only seam for the library probe — delegates to the canonical hash."""
    return _compute_export_hash(paths)



def sync_workspace_visual_assets(
    ocr_paper_dir: Path,
    workspace_dir: Path,
    zotero_key: str,
) -> list[str]:
    """Copy cropped figure/table JPGs from OCR assets into ``<workspace>/assets/<KEY>_*.jpg``.

    Size + mtime guarded; never overwrites unrelated user files or ``<KEY>_ann_*.jpg`` crops.
    Returns list of materialized filenames under ``<workspace>/assets/``.
    """
    assets_src = ocr_paper_dir / "assets"
    if not assets_src.exists() or not zotero_key:
        return []
    dst_dir = workspace_dir / "assets"
    materialized: list[str] = []
    for subdir in ("figures", "tables"):
        src_folder = assets_src / subdir
        if not src_folder.exists():
            continue
        for img_path in sorted(src_folder.glob("*.jpg")):
            target_name = f"{zotero_key}_{img_path.name}"
            dst_path = dst_dir / target_name
            try:
                src_st = img_path.stat()
                dst_st = dst_path.stat() if dst_path.exists() else None
            except OSError:
                dst_st = None
                src_st = None
            changed = (
                dst_st is None
                or src_st is None
                or src_st.st_size != dst_st.st_size
                or src_st.st_mtime_ns != dst_st.st_mtime_ns
            )
            if changed:
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(img_path), str(dst_path))
            materialized.append(target_name)
    return materialized


def _sync_workspace_fulltexts(items: list[dict], vault: Path, paths: dict, verbose: bool = False) -> None:
    hidden_engine = Path(str(paths["paperforge"])).name == ".paperforge"
    for entry in items:
        ws_dir_rel = entry.get("paper_root", "")
        if not ws_dir_rel:
            continue
        ws_dir = vault / ws_dir_rel
        ws_ft = ws_dir / "fulltext.md"
        if hidden_engine and ws_ft.exists():
            ws_ft.unlink()
        if entry.get("ocr_status") not in ("done", "done_degraded"):
            continue
        key = str(entry.get("zotero_key") or "")
        if key:
            sync_workspace_visual_assets(paths["ocr"] / key, ws_dir, key)
        if hidden_engine:
            continue
        if ws_ft.exists():
            continue
        ft_rel = entry.get("fulltext_path", "")
        if not ft_rel:
            ocr_ft = paths["ocr"] / entry["zotero_key"] / "fulltext.md"
        else:
            ocr_ft = vault / ft_rel
        if ocr_ft.exists():
            ws_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(ocr_ft), str(ws_ft))
            if verbose:
                print(f"  synced fulltext to workspace: {entry['zotero_key']}")


def build_index(vault: Path, verbose: bool = False, force_rebuild: bool = False) -> int:
    """Full rebuild of the canonical asset index for *vault*."""
    from paperforge.config import load_vault_config
    from paperforge.worker._utils import pipeline_paths  # noqa: F811
    from paperforge.worker.base_views import ensure_base_views
    from paperforge.worker.sync import load_domain_config, load_export_rows

    paths = pipeline_paths(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)

    migrated = migrate_legacy_index(vault)
    if migrated:
        print("Legacy index format detected and backed up. Rebuilding with envelope...", file=sys.stderr)

    existing_data = read_index(vault)
    if isinstance(existing_data, dict) and existing_data.get("schema_version") != CURRENT_SCHEMA_VERSION:
        print(
            f"Schema version mismatch: index has {existing_data.get('schema_version')}, "
            f"need {CURRENT_SCHEMA_VERSION}. Rebuilding...",
            file=sys.stderr,
        )

    zotero_dir = paths.get("zotero_dir") or (Path(paths.get("paperforge", vault / ".paperforge")) / "Zotero")

    export_hash = _compute_export_hash(paths)
    if not force_rebuild and isinstance(existing_data, dict) and existing_data.get("export_hash") == export_hash:
        if existing_data.get("schema_version") == CURRENT_SCHEMA_VERSION:
            items = existing_data.get("items", [])
            sample = items[:min(5, len(items))]
            if sample and not all(isinstance(it, dict) and "ocr_redo" in it and "ocr_time" in it for it in sample):
                if verbose:
                    print("index-refresh: ocr_redo or ocr_time field missing in index, forcing rebuild")
            else:
                count = len(items)
                _sync_workspace_fulltexts(items, vault, paths, verbose)
                if verbose:
                    print(f"index-refresh: {count} entries (unchanged)")
                return count

    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

    staged_exports: list[tuple[str, list[dict]]] = []
    active_domain_keys: dict[str, set[str]] = {}
    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        staged_exports.append((domain, export_rows))
        keys_in_domain = active_domain_keys.setdefault(domain, set())
        for item in export_rows:
            if item.get("key"):
                keys_in_domain.add(str(item["key"]))

    index_rows: list[dict] = []
    seen_keys: set[str] = set()
    for domain, export_rows in staged_exports:
        for item in export_rows:
            item_key = str(item.get("key") or "")
            if item_key and item_key in seen_keys:
                logger.warning(
                    "Duplicate zotero_key %s in domain '%s'; keeping first export entry",
                    item_key,
                    domain,
                )
                continue
            if item_key:
                seen_keys.add(item_key)
            entry = _build_entry(
                item,
                vault,
                paths,
                domain,
                zotero_dir,
                active_domain_keys=active_domain_keys,
            )
            index_rows.append(entry)

    index_path = paths["index"]
    envelope = build_envelope(index_rows, export_hash)
    atomic_write_index(index_path, envelope)
    # #137: human logs → stderr; stdout carries machine output only.
    import sys as _sys

    print(f"index-refresh: wrote {len(index_rows)} index rows", file=_sys.stderr)
    return len(index_rows)


# ---------------------------------------------------------------------------
# Incremental refresh
# ---------------------------------------------------------------------------


def refresh_index_entry(vault: Path, key: str) -> bool:
    """Incrementally refresh a single index entry identified by *key*.

    *key* is the Zotero citation key (8-character alphanumeric).

    Behaviour:
    * If the index does not exist, delegates to ``build_index()`` (full rebuild).
    * If the index is in legacy bare-list format, delegates to ``build_index()``.
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

    # Find the export item for the requested key
    config = load_domain_config(paths)
    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}
    zotero_dir = paths.get("zotero_dir") or (Path(paths.get("paperforge", vault / ".paperforge")) / "Zotero")

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
        logger.warning("Key %s not found in any export -- cannot refresh", key)
        return False

    # Build single entry and update the items list
    new_entry = _build_entry(found_item, vault, paths, found_domain, zotero_dir)

    try:
        from paperforge.memory.refresh import refresh_paper

        refresh_paper(vault, new_entry)
    except Exception as exc:
        # Memory DB refresh is best-effort, but a writer-lock timeout during
        # a shadow rebuild is a real signal — surface it (D2b).
        logger.warning("refresh_paper failed for %s (best-effort): %s", key, exc)

    def _apply(current):
        if is_legacy_format(current) or not isinstance(current, dict):
            return None
        items = list(current.get("items", []))
        replaced = False
        for i, existing_entry in enumerate(items):
            if existing_entry.get("zotero_key") == key:
                items[i] = new_entry
                replaced = True
                break
        if not replaced:
            items.append(new_entry)
        return build_envelope(items)

    if not mutate_index(vault, _apply):
        build_index(vault)
        return False

    logger.info("refresh_index_entry: updated entry %s (%s)", key, found_domain)
    return True


# ---------------------------------------------------------------------------
# Index summarization  (Phase 25: consumed by status --json and doctor)
# ---------------------------------------------------------------------------


def summarize_index(vault: Path) -> dict | None:
    # Read the canonical index and return summary aggregates.
    # Returns None if missing, corrupt, or legacy format.

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
