from __future__ import annotations

import logging
import shutil
from pathlib import Path

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)


def _collect_orphan_candidates(lit_dir: Path, fresh_keys: set[str]) -> list[dict]:
    if not lit_dir.exists():
        return []

    candidates: list[dict] = []
    for domain_dir in sorted(lit_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        try:
            entries = sorted(domain_dir.iterdir())
        except OSError as exc:
            logger.warning("prune: cannot scan %s: %s", domain_dir, exc)
            continue
        for sub in entries:
            if not sub.is_dir():
                continue
            parts = sub.name.split(" - ", 1)
            if len(parts) < 2:
                continue
            key = parts[0]
            if not key:
                continue
            if key in fresh_keys:
                continue
            candidates.append(
                {
                    "key": key,
                    "domain": domain_dir.name,
                    "workspace_dir": sub,
                    "ocr_dir": None,
                }
            )

    return candidates


def _resolve_ocr_dir(vault: Path, key: str) -> Path:
    cfg = paperforge_paths(vault)
    ocr_root = cfg.get("ocr", vault / "System" / "PaperForge" / "ocr")
    return ocr_root / key


def _enrich_orphan_preview(vault: Path, candidates: list[dict]) -> list[dict]:
    from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict

    enriched = []
    for c in candidates:
        key = c["key"]
        ws = c["workspace_dir"]

        title_from_dir = ws.name.split(" - ", 1)[1] if " - " in ws.name else key

        note_path = ws / f"{key}.md"
        fm = {}
        if note_path.exists():
            try:
                fm = read_frontmatter_dict(note_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        title = fm.get("title", title_from_dir) or title_from_dir
        first_author = fm.get("first_author", "") or ""
        coll = fm.get("collection_path", "")
        if isinstance(coll, list):
            coll = " | ".join(coll)

        enriched.append({
            "key": key,
            "citation_key": fm.get("citation_key") or key,
            "title": title,
            "year": str(fm.get("year", "")),
            "authors": first_author,
            "has_pdf": fm.get("has_pdf", False) in (True, "true"),
            "collection_path": coll,
            "domain": c["domain"],
            "workspace": str(ws),
            "ocr_dir": str(c["ocr_dir"]) if c["ocr_dir"] and c["ocr_dir"].exists() else None,
        })

    return enriched


def prune_orphan_papers(
    vault: Path,
    *,
    fresh_index: dict | None = None,
    fresh_keys: set[str] | None = None,
    dry_run: bool = True,
    enrich: bool = True,
    _candidates: list[dict] | None = None,
) -> dict:
    """Orphan cleanup.  **Zotero is the authority** (2026-08-14): pass
    ``fresh_keys`` = the Zotero key set (from the live export at sync time)
    so an orphan is a workspace paper whose key is ABSENT from Zotero.
    ``fresh_index`` is a legacy fallback (index snapshot) for callers that
    only have the index; it risks false orphans when Zotero gained papers
    that were not synced yet."""
    cfg = paperforge_paths(vault)
    lit_dir = cfg.get("literature")
    if not lit_dir:
        return {"preview": [], "deleted": [], "counts": {}}

    if fresh_keys is None:
        fresh_keys = {
            item["zotero_key"]
            for item in (fresh_index or {}).get("items", [])
            if item.get("zotero_key")
        }

    if _candidates is not None:
        candidates = _candidates
    else:
        candidates = _collect_orphan_candidates(lit_dir, fresh_keys)
    if not candidates:
        return {"preview": [], "deleted": [], "counts": {}}

    for c in candidates:
        c["ocr_dir"] = _resolve_ocr_dir(vault, c["key"])

    if enrich:
        preview = _enrich_orphan_preview(vault, candidates)
    else:
        preview = [
            {
                "key": c["key"],
                "domain": c["domain"],
                "workspace": str(c["workspace_dir"]),
                "ocr_dir": str(c["ocr_dir"]) if c["ocr_dir"].exists() else None,
            }
            for c in candidates
        ]

    if dry_run:
        return {"preview": preview, "deleted": [], "counts": {}}

    # P0-4: the whole destructive pass (OCR dirs + workspace dirs + vectors)
    # must run under the global writer lock — a shadow build holds it while
    # reading OCR fulltext, and deleting those files mid-build would break
    # the worker or produce an inconsistent snapshot.  Locking only the
    # vector delete (as before) left the file deletions unprotected.
    from paperforge.memory.db import WriterLock

    with WriterLock(vault):
        return _prune_orphan_papers_locked(vault, candidates, preview)


def _prune_orphan_papers_locked(
    vault: Path, candidates: list[dict], preview: list[dict]
) -> dict:
    """Locked body: caller owns the WriterLock.

    Safety (2026-08-14 incident → trash architecture): NO user data is
    ever physically deleted here.  Workspace/OCR directories are MOVED
    into ``.paperforge/trash/<ts>/<id>/`` with a manifest (recoverable via
    ``paperforge trash restore``), behind a fail-closed capability check
    (empty paths, ``.``, vault root, and anything outside the literature/
    OCR roots are refused).  Vectors and DB rows are transactional DB
    deletes (rowid-verified), not filesystem deletes."""
    from paperforge.config import paperforge_paths as _pp
    from paperforge.worker.trash import DangerousPathError, trash_remove

    _paths = _pp(vault)
    _lit_root = (_paths.get("literature") or Path()).resolve()
    _ocr_root = (_paths.get("ocr") or Path()).resolve()

    deleted: list[str] = []
    counts = {"workspace": 0, "ocr": 0, "vectors": 0, "failed": 0}

    for c in candidates:
        key = c["key"]
        try:
            ocr = c.get("ocr_dir")
            if ocr and ocr.exists():
                try:
                    rec = trash_remove(
                        ocr,
                        vault=vault,
                        allowed_root=_ocr_root,
                        operation="library.prune",
                        paper_key=key,
                    )
                    if rec is not None:
                        counts["ocr"] += 1
                except DangerousPathError as exc:
                    logger.warning("prune: refuse to trash OCR %s: %s", ocr, exc)
                    counts["failed"] += 1

            ws = c.get("workspace_dir")
            if ws and ws.exists():
                try:
                    rec = trash_remove(
                        ws,
                        vault=vault,
                        allowed_root=_lit_root,
                        operation="library.prune",
                        paper_key=key,
                    )
                    if rec is not None:
                        counts["workspace"] += 1
                except DangerousPathError as exc:
                    logger.warning("prune: refuse to trash workspace %s: %s", ws, exc)
                    counts["failed"] += 1

            try:
                from paperforge.embedding._chroma import _delete_paper_vectors_locked
                n = _delete_paper_vectors_locked(vault, key)
                if n > 0:
                    counts["vectors"] += n
            except Exception as vec_err:
                logger.warning("prune: failed to delete vectors for %s: %s", key, vec_err)
                counts["failed"] += 1

            # #135: unified residual cleanup — the full-text index rows,
            # OCR retrieval units, and lineage/alias/event records for the
            # same paper.  Same WriterLock, same transaction family; the
            # papers AFTER-DELETE trigger keeps paper_fts in sync.
            try:
                from paperforge.memory.db import (
                    ensure_vec_extension,
                    get_connection,
                    get_memory_db_path,
                )

                db_path = get_memory_db_path(vault)
                if db_path.exists():
                    conn = get_connection(db_path)
                    ensure_vec_extension(conn)
                    try:
                        # external-content FTS5: body_units_fts has NO
                        # trigger — sync the delete manually before removing
                        # the content rows.  Production only indexes
                        # indexable=1 rows (see _upsert_body_units), so only
                        # those have FTS rows; deleting an absent FTS row
                        # raises SQLITE_CORRUPT_VTAB.
                        body_rows = conn.execute(
                            "SELECT rowid, unit_id FROM body_units "
                            "WHERE paper_id = ? AND indexable = 1",
                            (key,),
                        ).fetchall()
                        for br in body_rows:
                            conn.execute(
                                "INSERT INTO body_units_fts(body_units_fts, rowid, unit_id) "
                                "VALUES('delete', ?, ?)",
                                (br["rowid"], br["unit_id"]),
                            )
                        conn.execute("DELETE FROM body_units WHERE paper_id = ?", (key,))
                        conn.execute("DELETE FROM object_units WHERE paper_id = ?", (key,))
                        for table in ("lineage", "paper_aliases", "paper_assets", "paper_events"):
                            conn.execute(f"DELETE FROM {table} WHERE paper_id = ?", (key,))
                        # papers AFTER-DELETE trigger clears paper_fts rows.
                        conn.execute("DELETE FROM papers WHERE zotero_key = ?", (key,))
                        conn.commit()
                    finally:
                        conn.close()
            except Exception as db_err:
                logger.warning("prune: failed to clean DB records for %s: %s", key, db_err)
                counts["failed"] += 1

            deleted.append(key)

        except Exception as exc:
            logger.error("prune: failed to clean up %s: %s", key, exc)
            counts["failed"] += 1

    return {"preview": preview, "deleted": deleted, "counts": counts}
