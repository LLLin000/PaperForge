"""Non-destructive upgrade self-healing (``reconcile_epoch``) for PaperForge vaults.

Provides an idempotent, O(1)-fast-pathed reconciliation pass that heals derived
vault state (``workspace_registry``, ``formal-library.json`` derived paths, and
canonical PaperForge ``.base`` views) after version upgrades without ever
modifying user Markdown note bodies, ``annotations.jsonl``, or ``reading-log.jsonl``,
and without creating an empty ``paperforge.db`` when none existed.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import sqlite3
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import filelock

from paperforge.core.fs_safe import safe_is_dir, safe_is_file, safe_iterdir
from paperforge.core.io import write_json_atomic, write_text_atomic

logger = logging.getLogger(__name__)

CURRENT_RECONCILE_EPOCH = 2

_LEGACY_ENGINE_PREFIXES = ("System/PaperForge/", "99_System/PaperForge/")
_INDEX_PATH_FIELDS = (
    "main_note_path",
    "note_path",
    "paper_root",
    "pdf_path",
    "fulltext_path",
    "ocr_md_path",
    "ocr_json_path",
    "ai_path",
    "deep_reading_md_path",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel_posix(path: Path, root: Path, *, root_resolved: Path | None = None) -> str:
    try:
        r_base = root_resolved if root_resolved is not None else root.resolve()
        return path.resolve().relative_to(r_base).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _has_vault_init_markers(vault_root: Path) -> bool:
    """Return True if *vault_root* looks like an initialized PaperForge vault."""
    if (vault_root / "paperforge.json").is_file():
        return True
    if (vault_root / ".paperforge").is_dir():
        return True
    from paperforge.services.vault_upgrade import find_legacy_engine_dirs

    if find_legacy_engine_dirs(vault_root):
        return True
    return False


def _fast_read_epoch(manifest_path: Path) -> int | None:
    """Read ``reconcile_epoch`` from *manifest_path* in O(1) without heavy imports."""
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    raw_epoch = data.get("reconcile_epoch")
    if raw_epoch is None:
        return 0
    try:
        return int(raw_epoch)
    except (TypeError, ValueError):
        return 0


def _resolve_reconcile_layout(vault_root: Path) -> dict[str, Path]:
    """Resolve engine, literature, bases, and exports roots safely for any layout."""
    from paperforge.config import ConfigError, load_config, resolve_paths

    try:
        snap = load_config(vault_root)
        paths = resolve_paths(vault_root, snap)
        return {
            "vault": vault_root,
            "paperforge": Path(paths["paperforge"]),
            "literature": Path(paths["literature"]),
            "bases": Path(paths["bases"]),
            "exports": Path(paths["exports"]),
            "config": Path(paths["config"]),
            "control": Path(paths.get("control") or (vault_root / "Resources" / "LiteratureControl")),
        }
    except (ConfigError, KeyError, TypeError, ValueError) as exc:
        logger.debug("fallback path resolution in upgrade_reconcile: %s", exc)

    raw_cfg: dict[str, Any] = {}
    cfg_path = vault_root / "paperforge.json"
    if cfg_path.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
            parsed = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                raw_cfg = parsed

    vc = raw_cfg.get("vault_config") if isinstance(raw_cfg.get("vault_config"), dict) else {}
    sys_dir = str(vc.get("system_dir") or raw_cfg.get("system_dir") or "").strip()
    res_dir = str(vc.get("resources_dir") or raw_cfg.get("resources_dir") or "").strip()
    lit_sub = str(vc.get("literature_dir") or raw_cfg.get("literature_dir") or "Literature").strip() or "Literature"
    ctrl_sub = str(vc.get("control_dir") or raw_cfg.get("control_dir") or "LiteratureControl").strip() or "LiteratureControl"
    base_sub = str(vc.get("base_dir") or raw_cfg.get("base_dir") or "").strip()

    dot_pf = vault_root / ".paperforge"
    if dot_pf.is_dir():
        engine_root = dot_pf
    elif sys_dir and sys_dir != ".paperforge" and (vault_root / sys_dir / "PaperForge").is_dir():
        engine_root = vault_root / sys_dir / "PaperForge"
    else:
        from paperforge.services.vault_upgrade import find_legacy_engine_dirs

        legacy_dirs = find_legacy_engine_dirs(vault_root, configured_sys_dir=sys_dir)
        engine_root = legacy_dirs[0] if legacy_dirs else dot_pf

    if res_dir:
        lit_root = vault_root / res_dir / lit_sub
        control_root = vault_root / res_dir / ctrl_sub
    elif not (vault_root / "Resources" / "Literature").is_dir() and (vault_root / "03_Resources" / "Literature").is_dir():
        lit_root = vault_root / "03_Resources" / "Literature"
        control_root = vault_root / "03_Resources" / "LiteratureControl"
    else:
        lit_root = vault_root / "Resources" / "Literature"
        control_root = vault_root / "Resources" / "LiteratureControl"

    if base_sub:
        base_root = vault_root / base_sub
    elif not (vault_root / "Bases").is_dir() and (vault_root / "05_Bases").is_dir():
        base_root = vault_root / "05_Bases"
    else:
        base_root = vault_root / "Bases"

    return {
        "vault": vault_root,
        "paperforge": engine_root,
        "literature": lit_root,
        "bases": base_root,
        "exports": engine_root / "exports",
        "config": engine_root / "config" / "domain-collections.json",
        "control": control_root,
    }


def _normalize_relpath_value(
    raw: str,
    *,
    lit_rel: str,
    rewrite_legacy_engine: bool,
) -> str:
    """Normalize malformed/duplicated relative path segments without corrupting wikilinks."""
    if not raw:
        return raw
    is_wikilink = raw.startswith("[[") and raw.endswith("]]")
    inner = raw[2:-2] if is_wikilink else raw
    norm = inner.replace("\\", "/").strip()
    if norm.startswith("./"):
        norm = norm[2:]
    while "//" in norm:
        norm = norm.replace("//", "/")

    # Collapse duplicated literature/resources segments, e.g. Resources/Literature/Literature/...
    if lit_rel:
        lit_clean = lit_rel.strip("/")
        lit_leaf = lit_clean.rsplit("/", 1)[-1]
        if lit_leaf:
            duplicated = f"{lit_clean}/{lit_leaf}/"
            single = f"{lit_clean}/"
            while duplicated in norm:
                norm = norm.replace(duplicated, single)
        parts = [p for p in lit_clean.split("/") if p]
        for seg in parts:
            while f"/{seg}/{seg}/" in norm:
                norm = norm.replace(f"/{seg}/{seg}/", f"/{seg}/")
            if norm.startswith(f"{seg}/{seg}/"):
                norm = norm[len(seg) + 1 :]

    norm = norm.replace(".paperforge/.paperforge/", ".paperforge/")
    if rewrite_legacy_engine:
        for pref in _LEGACY_ENGINE_PREFIXES:
            if norm.startswith(pref):
                norm = ".paperforge/" + norm[len(pref) :]
                break
            if f"/{pref}" in norm:
                norm = norm.replace(f"/{pref}", "/.paperforge/")
                break

    return f"[[{norm}]]" if is_wikilink else norm


def _is_pid_alive(pid: int) -> bool:
    """Return True if OS process *pid* still exists."""
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            try:
                code = ctypes.c_ulong()
                if k32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return code.value == 259  # STILL_ACTIVE
                return True
            finally:
                k32.CloseHandle(h)
        except Exception:
            return True
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _has_active_ocr_job(conn: sqlite3.Connection, engine_root: Path | None = None) -> bool:
    """Return True if ``engine_jobs`` has a running OCR job (verified by live PID or <30m heartbeat)."""
    del engine_root
    try:
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(engine_jobs)").fetchall()}
        if not cols:
            return False
        has_pid = "pid" in cols
        sel = "updated_at, pid" if has_pid else "updated_at"
        rows = conn.execute(
            f"""
            SELECT {sel} FROM engine_jobs
            WHERE lower(trim(coalesce(status, ''))) = 'running'
              AND lower(coalesce(job_type, '')) LIKE '%ocr%'
            """
        ).fetchall()
    except sqlite3.DatabaseError:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    for row in rows:
        if has_pid and row[1] is not None:
            try:
                pid_val = int(row[1])
                if pid_val > 0 and not _is_pid_alive(pid_val):
                    continue
                if pid_val > 0 and _is_pid_alive(pid_val):
                    return True
            except (TypeError, ValueError) as exc:
                logger.debug("ignoring non-integer ocr job pid %r: %s", row[1], exc)
        raw_ts = str(row[0] or "").strip()
        if not raw_ts:
            continue
        if raw_ts.endswith("Z"):
            raw_ts = raw_ts[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw_ts)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            return True
    return False


def _resolve_ocr_status_from_disk(ocr_root: Path, key: str) -> str:
    """Resolve a stale ``running`` OCR status using canonical disk artifacts."""
    if safe_is_file(ocr_root / key / "fulltext.md") and safe_is_file(
        ocr_root / key / "json" / "result.json"
    ):
        return "done"
    return "interrupted"


def _reconcile_sqlite_if_present(
    vault_root: Path,
    db_path: Path,
    scan: Any,
    *,
    lit_rel: str,
    rewrite_legacy_engine: bool,
    engine_root: Path | None = None,
) -> dict[str, Any]:
    """Reconcile ``workspace_registry``, FTS5, and stale ``papers`` rows ONLY when ``paperforge.db`` exists."""
    if not safe_is_file(db_path):
        return {
            "db_reconciled": False,
            "workspace_registry_upserted": 0,
            "workspace_registry_removed": 0,
            "papers_paths_healed": 0,
            "fts_repaired": [],
            "zombie_running_healed": 0,
            "zombie_healed_map": {},
            "has_active_ocr": False,
        }

    from paperforge.memory.db import WriterLock, check_and_heal_fts, get_connection
    from paperforge.memory.schema import ensure_schema

    now_iso = _utcnow_iso()
    upserted = 0
    removed = 0
    papers_healed = 0
    fts_repaired: list[str] = []
    zombie_healed_map: dict[str, str] = {}
    has_active_ocr = False
    ocr_root = (Path(engine_root) if engine_root is not None else db_path.parent.parent) / "ocr"

    with WriterLock(vault_root):
        conn = get_connection(db_path)
        try:
            ensure_schema(conn)
            fts_res = check_and_heal_fts(conn)
            fts_repaired = list(fts_res.get("repaired") or [])

            vault_resolved = vault_root.resolve()
            reg_rows: list[tuple[Any, ...]] = []
            for key, ws in scan.workspaces.items():
                try:
                    mtime_ns = int(ws.workspace_dir.stat().st_mtime_ns)
                except OSError:
                    mtime_ns = 0
                ws_rel = _rel_posix(ws.workspace_dir, vault_root, root_resolved=vault_resolved)
                note_rel = _rel_posix(ws.main_note_path, vault_root, root_resolved=vault_resolved) if ws.main_note_path else ""
                reg_rows.append(
                    (
                        key,
                        ws.domain,
                        ws_rel,
                        note_rel,
                        mtime_ns,
                        ",".join(ws.identity_sources),
                        "duplicate" if key in scan.duplicate_workspaces else "active",
                        now_iso,
                    )
                )
            if reg_rows:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO workspace_registry (
                        zotero_key, domain, workspace_relpath, main_note_relpath,
                        dir_mtime_ns, identity_source, status, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    reg_rows,
                )
                upserted = len(reg_rows)

            existing_keys = {
                str(r[0]) for r in conn.execute("SELECT zotero_key FROM workspace_registry").fetchall()
            }
            stale_reg_keys = [(k,) for k in (existing_keys - set(scan.workspaces.keys()))]
            if stale_reg_keys:
                conn.executemany("DELETE FROM workspace_registry WHERE zotero_key = ?", stale_reg_keys)
                removed = len(stale_reg_keys)

            # Heal stale path columns inside `papers` when DB points to missing/malformed paths
            paper_cols = {
                str(r[1]) for r in conn.execute("PRAGMA table_info(papers)").fetchall()
            }
            if {"zotero_key", "main_note_path"}.issubset(paper_cols):
                sel_cols = [
                    c
                    for c in (
                        "zotero_key",
                        "domain",
                        "paper_root",
                        "main_note_path",
                        "note_path",
                        "ocr_md_path",
                        "ocr_json_path",
                        "fulltext_path",
                        "ai_path",
                    )
                    if c in paper_cols
                ]
                rows = conn.execute(f"SELECT {', '.join(sel_cols)} FROM papers").fetchall()
                lit_leaf = lit_rel.strip("/").rsplit("/", 1)[-1]
                col_updates: dict[tuple[str, ...], list[tuple[Any, ...]]] = {}
                for row in rows:
                    zk = str(row["zotero_key"] or "").strip()
                    if not zk:
                        continue
                    updates: dict[str, str] = {}
                    ws = scan.workspaces.get(zk)
                    if ws is not None:
                        ws_rel = _rel_posix(ws.workspace_dir, vault_root, root_resolved=vault_resolved)
                        if "paper_root" in sel_cols:
                            cur_root = str(row["paper_root"] or "")
                            if cur_root != ws_rel and (not cur_root or not safe_is_dir(vault_root / cur_root)):
                                updates["paper_root"] = ws_rel
                        if ws.main_note_path is not None and safe_is_file(ws.main_note_path):
                            new_note_rel = _rel_posix(ws.main_note_path, vault_root, root_resolved=vault_resolved)
                            cur_main = str(row["main_note_path"] or "")
                            if cur_main != new_note_rel and (not cur_main or not safe_is_file(vault_root / cur_main)):
                                updates["main_note_path"] = new_note_rel
                            if "note_path" in sel_cols:
                                cur_np = str(row["note_path"] or "")
                                if cur_np and cur_np != new_note_rel and not safe_is_file(vault_root / cur_np):
                                    updates["note_path"] = new_note_rel
                        if "domain" in sel_cols and ws.domain:
                            cur_dom = str(row["domain"] or "").strip()
                            if not cur_dom or (lit_leaf and cur_dom == lit_leaf and ws.domain != lit_leaf):
                                updates["domain"] = ws.domain

                    for col in ("ocr_md_path", "ocr_json_path", "fulltext_path", "ai_path"):
                        if col not in sel_cols:
                            continue
                        cur_val = str(row[col] or "")
                        if not cur_val:
                            continue
                        norm_val = _normalize_relpath_value(
                            cur_val,
                            lit_rel=lit_rel,
                            rewrite_legacy_engine=rewrite_legacy_engine,
                        )
                        if norm_val != cur_val:
                            updates[col] = norm_val

                    if updates:
                        ukeys = tuple(updates.keys())
                        col_updates.setdefault(ukeys, []).append((*updates.values(), zk))
                        papers_healed += len(updates)

                for ukeys, params_list in col_updates.items():
                    set_clause = ", ".join(f"{col} = ?" for col in ukeys)
                    conn.executemany(f"UPDATE papers SET {set_clause} WHERE zotero_key = ?", params_list)

            # Heal zombie `ocr_status = 'running'` rows when no live OCR job is active
            has_active_ocr = _has_active_ocr_job(conn, engine_root)
            if not has_active_ocr and {"zotero_key", "ocr_status"}.issubset(paper_cols):
                running_rows = conn.execute(
                    "SELECT zotero_key FROM papers WHERE lower(trim(coalesce(ocr_status, ''))) = 'running'"
                ).fetchall()
                zombie_params: list[tuple[str, str]] = []
                for row in running_rows:
                    zk = str(row[0] or "").strip()
                    if not zk:
                        continue
                    resolved_status = _resolve_ocr_status_from_disk(ocr_root, zk)
                    zombie_params.append((resolved_status, zk))
                    zombie_healed_map[zk] = resolved_status
                if zombie_params:
                    conn.executemany("UPDATE papers SET ocr_status = ? WHERE zotero_key = ?", zombie_params)

            conn.commit()
        finally:
            conn.close()

    return {
        "db_reconciled": True,
        "workspace_registry_upserted": upserted,
        "workspace_registry_removed": removed,
        "papers_paths_healed": papers_healed,
        "fts_repaired": fts_repaired,
        "zombie_running_healed": len(zombie_healed_map),
        "zombie_healed_map": zombie_healed_map,
        "has_active_ocr": has_active_ocr,
    }


def _reconcile_formal_index(
    vault_root: Path,
    index_path: Path,
    scan: Any,
    *,
    lit_rel: str,
    rewrite_legacy_engine: bool,
    engine_root: Path | None = None,
    zombie_healed_map: dict[str, str] | None = None,
    has_active_ocr: bool = False,
) -> dict[str, Any]:
    """Normalize derived path fields in ``formal-library.json`` while preserving canonical fields."""
    if not safe_is_file(index_path):
        return {"index_normalized": False, "index_entries_updated": 0, "zombie_healed_keys": []}

    lock_path = index_path.with_suffix(".json.lock")
    updated_entries = 0
    wrote_file = False
    lit_leaf = lit_rel.strip("/").rsplit("/", 1)[-1]
    ocr_root = (Path(engine_root) if engine_root is not None else index_path.parent.parent) / "ocr"
    idx_zombie_healed: list[str] = []

    with filelock.FileLock(str(lock_path), timeout=10.0):
        raw_text = index_path.read_text(encoding="utf-8")
        raw_idx = json.loads(raw_text)
        if isinstance(raw_idx, list):
            items_list = raw_idx
        elif isinstance(raw_idx, dict) and isinstance(raw_idx.get("items"), list):
            items_list = raw_idx["items"]
        else:
            return {"index_normalized": False, "index_entries_updated": 0, "zombie_healed_keys": []}

        for entry in items_list:
            if not isinstance(entry, dict):
                continue
            entry_changed = False

            for fld in _INDEX_PATH_FIELDS:
                val = entry.get(fld)
                if not isinstance(val, str) or not val:
                    continue
                norm_val = _normalize_relpath_value(
                    val,
                    lit_rel=lit_rel,
                    rewrite_legacy_engine=rewrite_legacy_engine,
                )
                if norm_val != val:
                    entry[fld] = norm_val
                    entry_changed = True

            ek = str(entry.get("zotero_key") or "").strip()
            ws = scan.workspaces.get(ek)
            if ws is not None:
                ws_rel = _rel_posix(ws.workspace_dir, vault_root)
                cur_root = str(entry.get("paper_root") or "")
                if cur_root != ws_rel and (not cur_root or not safe_is_dir(vault_root / cur_root)):
                    entry["paper_root"] = ws_rel
                    entry_changed = True

                if ws.main_note_path is not None and safe_is_file(ws.main_note_path):
                    new_note_rel = _rel_posix(ws.main_note_path, vault_root)
                    cur_main = str(entry.get("main_note_path") or "")
                    if cur_main != new_note_rel and (not cur_main or not safe_is_file(vault_root / cur_main)):
                        entry["main_note_path"] = new_note_rel
                        entry_changed = True
                    cur_np = str(entry.get("note_path") or "")
                    if cur_np and cur_np != new_note_rel and not safe_is_file(vault_root / cur_np):
                        entry["note_path"] = new_note_rel
                        entry_changed = True

                if ws.domain:
                    cur_dom = str(entry.get("domain") or "").strip()
                    if not cur_dom or (lit_leaf and cur_dom == lit_leaf and ws.domain != lit_leaf):
                        entry["domain"] = ws.domain
                        entry_changed = True

            if not has_active_ocr and ek and str(entry.get("ocr_status") or "").strip().lower() == "running":
                if zombie_healed_map and ek in zombie_healed_map:
                    resolved_status = zombie_healed_map[ek]
                else:
                    resolved_status = _resolve_ocr_status_from_disk(ocr_root, ek)
                entry["ocr_status"] = resolved_status
                idx_zombie_healed.append(ek)
                entry_changed = True

            if entry_changed:
                updated_entries += 1

        if updated_entries > 0:
            fd, tmp_name = tempfile.mkstemp(prefix=".formal-lib-", suffix=".tmp", dir=index_path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(raw_idx, fh, ensure_ascii=False, indent=2)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_name, index_path)
                wrote_file = True
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_name)
                raise

    return {
        "index_normalized": wrote_file,
        "index_entries_updated": updated_entries,
        "zombie_healed_keys": idx_zombie_healed,
    }


def _is_pf_managed_base_file(txt: str, base_file: Path, known_domains: set[str]) -> bool:
    """Strictly distinguish PaperForge-managed ``.base`` files from user custom ``.base`` files."""
    from paperforge.worker.base_views import PAPERFORGE_VIEW_PREFIX, RETIRED_PF_VIEWS

    if PAPERFORGE_VIEW_PREFIX in txt or "# paperforge-base-schema:" in txt or "paperforge-table" in txt:
        return True
    has_zotero_anchor = "zotero_key" in txt
    has_retired = any(rv in txt for rv in RETIRED_PF_VIEWS)
    norm_stem = unicodedata.normalize("NFC", base_file.stem)
    norm_domains = {unicodedata.normalize("NFC", d) for d in known_domains}
    if has_zotero_anchor and (has_retired or norm_stem in norm_domains or base_file.name == "Literature Hub.base"):
        return True
    if has_retired and (base_file.name == "Literature Hub.base" or any(f"name: {rv}" in txt or f'name: "{rv}"' in txt for rv in RETIRED_PF_VIEWS)):
        return True
    return False


def _base_needs_refresh(txt: str, lit_rel: str) -> bool:
    """Return True if a PaperForge-managed ``.base`` file is outdated or structurally broken."""
    from paperforge.worker.base_views import RETIRED_PF_VIEWS

    if not txt.strip():
        return True
    if not txt.startswith("# paperforge-base-schema:"):
        return True
    if re.search(r"^\s*-\s*type:\s*table\s*$", txt, re.MULTILINE):
        return True
    if any(rv in txt for rv in RETIRED_PF_VIEWS):
        return True
    if re.search(r"^\s*(?:-\s+)?!(?!\!)[^\n\"']+?\s*$", txt, re.MULTILINE):
        return True
    if "views:" not in txt:
        return True
    lit_leaf = lit_rel.strip("/").rsplit("/", 1)[-1]
    if lit_leaf and f"{lit_rel.strip('/')}/{lit_leaf}" in txt:
        return True
    try:
        import yaml  # type: ignore[import-untyped]

        parsed = yaml.safe_load(txt)
        if not isinstance(parsed, dict) or "views" not in parsed:
            return True
    except ImportError as exc:
        logger.debug("PyYAML unavailable for .base validation: %s", exc)
    except Exception:
        return True
    return False


def _reconcile_base_views(
    vault_root: Path,
    paths: dict[str, Path],
    scan: Any,
    *,
    lit_rel: str,
) -> list[str]:
    """Refresh outdated/broken PaperForge ``.base`` files without touching user custom ``.base`` files."""
    from paperforge.worker.base_views import (
        PAPERFORGE_VIEW_PREFIX,
        build_base_views,
        ensure_base_views,
        substitute_config_placeholders,
    )

    base_root = paths["bases"]
    exports_dir = paths["exports"]
    known_domains: set[str] = {ws.domain for ws in scan.workspaces.values() if ws.domain}
    domain_cfg: dict[str, Any] = {"schema_version": 1, "domains": []}

    if safe_is_dir(exports_dir):
        for exp in safe_iterdir(exports_dir):
            if exp.suffix.lower() != ".json" or not safe_is_file(exp):
                continue
            known_domains.add(exp.stem)
            domain_cfg["domains"].append(
                {"domain": exp.stem, "export_file": exp.name, "allowed_collections": []}
            )

    existing_domains = {d["domain"] for d in domain_cfg["domains"]}
    for dom in sorted(known_domains):
        if dom not in existing_domains:
            domain_cfg["domains"].append(
                {"domain": dom, "export_file": f"{dom}.json", "allowed_collections": []}
            )
            existing_domains.add(dom)

    pf_owned_bases: list[tuple[Path, str]] = []
    if safe_is_dir(base_root):
        for bf in safe_iterdir(base_root):
            if bf.suffix.lower() != ".base" or not safe_is_file(bf):
                continue
            txt = bf.read_text(encoding="utf-8", errors="ignore")
            if not _is_pf_managed_base_file(txt, bf, known_domains):
                continue
            pf_owned_bases.append((bf, txt))
            if bf.name != "Literature Hub.base" and bf.stem not in existing_domains:
                domain_cfg["domains"].append(
                    {"domain": bf.stem, "export_file": f"{bf.stem}.json", "allowed_collections": []}
                )
                existing_domains.add(bf.stem)

    if not pf_owned_bases and not domain_cfg["domains"]:
        return []

    before_contents: dict[Path, str] = {}
    for bf, txt in pf_owned_bases:
        before_contents[bf] = txt

    # Only run ensure_base_views when at least one PF-managed base is outdated/missing
    needs_any = any(_base_needs_refresh(txt, lit_rel) for _, txt in pf_owned_bases)
    hub_path = base_root / "Literature Hub.base"
    if not pf_owned_bases and domain_cfg["domains"]:
        needs_any = True
    elif pf_owned_bases and not hub_path.exists():
        needs_any = True

    if not needs_any:
        return []

    ensure_base_views(vault_root, paths, domain_cfg, force=False)

    # Verify any PF-managed base file that was severely malformed is valid YAML; rebuild only that file if broken
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        yaml = None  # type: ignore[assignment]

    refreshed: list[str] = []
    if safe_is_dir(base_root):
        for bf in safe_iterdir(base_root):
            if bf.suffix.lower() != ".base" or not safe_is_file(bf):
                continue
            if bf not in before_contents and bf.name != "Literature Hub.base":
                continue
            cur_txt = bf.read_text(encoding="utf-8", errors="ignore")
            if yaml is not None and _is_pf_managed_base_file(cur_txt, bf, known_domains):
                broken_yaml = False
                try:
                    parsed = yaml.safe_load(cur_txt)
                    if not isinstance(parsed, dict) or not isinstance(parsed.get("views"), list):
                        broken_yaml = True
                except Exception:
                    broken_yaml = True
                if broken_yaml:
                    domain_name = "Literature Hub" if bf.name == "Literature Hub.base" else bf.stem
                    folder_tpl = "${LITERATURE}" if bf.name == "Literature Hub.base" else f"${{LITERATURE}}/{domain_name}"
                    resolved_folder = substitute_config_placeholders(folder_tpl, paths)
                    views = build_base_views(domain_name)
                    views_yaml_lines = []
                    for v in views:
                        vtype = str(v.get("type") or "paperforge-table")
                        views_yaml_lines.append(f"{PAPERFORGE_VIEW_PREFIX}{v['name']}")
                        views_yaml_lines.append(f"  - type: {vtype}")
                        views_yaml_lines.append(f'    name: "{v["name"]}"')
                        views_yaml_lines.append("    order:")
                        for col in v["order"]:
                            views_yaml_lines.append(f"      - {col}")
                    rebuilt = (
                        "# paperforge-base-schema: 2\n"
                        "filters:\n"
                        "  and:\n"
                        f'    - file.inFolder("{resolved_folder}")\n'
                        '    - file.ext == "md"\n'
                        '    - "!zotero_key.isEmpty()"\n'
                        "properties:\n"
                        "  zotero_key:\n"
                        '    displayName: "Zotero Key"\n'
                        "  title:\n"
                        '    displayName: "标题"\n'
                        "  year:\n"
                        '    displayName: "年份"\n'
                        "  first_author:\n"
                        '    displayName: "第一作者"\n'
                        "  journal:\n"
                        '    displayName: "期刊"\n'
                        "  impact_factor:\n"
                        '    displayName: "IF"\n'
                        "  domain:\n"
                        '    displayName: "领域"\n'
                        "  ocr_status:\n"
                        '    displayName: "状态"\n'
                        "views:\n"
                        + "\n".join(views_yaml_lines)
                        + "\n"
                    )
                    write_text_atomic(bf, rebuilt)
                    cur_txt = rebuilt

            if before_contents.get(bf) != cur_txt:
                refreshed.append(_rel_posix(bf, vault_root))

    return refreshed


def _persist_reconcile_manifest(
    vault_root: Path,
    engine_root: Path,
    *,
    now_iso: str,
) -> Path:
    """Atomically write ``reconcile_epoch``, ``last_reconciled_version``, and ``last_reconciled_at``."""
    from paperforge import __version__ as pf_version
    from paperforge.memory.schema import CURRENT_SCHEMA_VERSION
    from paperforge.services.vault_engine import CURRENT_LAYOUT_VERSION

    manifest_path = engine_root / "vault-manifest.json"
    existing: dict[str, Any] = {}
    if manifest_path.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
            parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                existing = parsed

    from paperforge.services.vault_upgrade import find_legacy_engine_dirs

    has_legacy_engine = bool(find_legacy_engine_dirs(vault_root))
    default_layout = 1 if (has_legacy_engine and engine_root != vault_root / ".paperforge") else CURRENT_LAYOUT_VERSION

    payload: dict[str, Any] = dict(existing)
    payload.setdefault("schema_version", 1)
    payload.setdefault("layout_version", default_layout)
    payload["paperforge_version"] = pf_version
    payload.setdefault("engine_ssot", "sqlite")
    payload.setdefault("db_schema_version", CURRENT_SCHEMA_VERSION)
    payload.setdefault("default_system_dir", ".paperforge" if engine_root == vault_root / ".paperforge" else engine_root.name)
    payload.setdefault("created_at", now_iso)
    payload["updated_at"] = now_iso
    payload.setdefault("migration_history", [])
    payload["reconcile_epoch"] = CURRENT_RECONCILE_EPOCH
    payload["last_reconciled_version"] = pf_version
    payload["last_reconciled_at"] = now_iso

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(manifest_path, payload)
    return manifest_path


def ensure_vault_reconciled(
    vault: Path,
    *,
    force: bool = False,
    scan: Any | None = None,
) -> dict[str, Any]:
    """Run non-destructive derived-state reconciliation if ``reconcile_epoch`` is behind.

    Fast-paths in O(1) (< 1 ms) when ``not force`` and the vault manifest
    already records ``reconcile_epoch >= CURRENT_RECONCILE_EPOCH``, and safely
    no-ops when *vault* is not initialized.
    """
    vault_root = Path(vault).expanduser()

    if not force:
        fast_epoch = _fast_read_epoch(vault_root / ".paperforge" / "vault-manifest.json")
        if fast_epoch is not None and fast_epoch >= CURRENT_RECONCILE_EPOCH:
            return {
                "reconciled": False,
                "skipped": True,
                "reason": "epoch_current",
                "reconcile_epoch": fast_epoch,
            }

    if not _has_vault_init_markers(vault_root):
        return {
            "reconciled": False,
            "skipped": True,
            "reason": "vault_not_initialized",
            "reconcile_epoch": 0,
        }

    vault_root = vault_root.resolve()
    paths = _resolve_reconcile_layout(vault_root)
    engine_root = paths["paperforge"]
    lit_root = paths["literature"]

    if not force:
        alt_epoch = _fast_read_epoch(engine_root / "vault-manifest.json")
        if alt_epoch is not None and alt_epoch >= CURRENT_RECONCILE_EPOCH:
            return {
                "reconciled": False,
                "skipped": True,
                "reason": "epoch_current",
                "reconcile_epoch": alt_epoch,
            }

    from paperforge import __version__ as pf_version
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.state_signal import bump_state_seq_in_dir

    if scan is None:
        scan = scan_vault_identities(lit_root)
    lit_rel = _rel_posix(lit_root, vault_root)
    rewrite_legacy_engine = engine_root == (vault_root / ".paperforge")

    # (a) Reconcile workspace_registry, FTS5, & stale paper rows ONLY if paperforge.db already exists
    db_path = engine_root / "indexes" / "paperforge.db"
    db_res = _reconcile_sqlite_if_present(
        vault_root,
        db_path,
        scan,
        lit_rel=lit_rel,
        rewrite_legacy_engine=rewrite_legacy_engine,
        engine_root=engine_root,
    )

    # (b) Reconcile/normalize derived formal-library.json metadata fields
    index_path = engine_root / "indexes" / "formal-library.json"
    idx_res = _reconcile_formal_index(
        vault_root,
        index_path,
        scan,
        lit_rel=lit_rel,
        rewrite_legacy_engine=rewrite_legacy_engine,
        engine_root=engine_root,
        zombie_healed_map=db_res["zombie_healed_map"],
        has_active_ocr=db_res["has_active_ocr"],
    )

    all_zombie_healed_keys = set(db_res["zombie_healed_map"].keys()) | set(
        idx_res.get("zombie_healed_keys") or ()
    )

    # (c) Reconcile/refresh outdated/broken PaperForge Base view templates
    refreshed_bases = _reconcile_base_views(vault_root, paths, scan, lit_rel=lit_rel)

    # (d) Atomically persist reconcile_epoch & bump .state-seq.json ONLY after (a)-(c) succeed
    now_iso = _utcnow_iso()
    manifest_path = _persist_reconcile_manifest(vault_root, engine_root, now_iso=now_iso)
    seq_payload = bump_state_seq_in_dir(
        engine_root / "indexes",
        reason="upgrade.reconcile",
        changed_keys=sorted(scan.workspaces.keys())[:50],
    )

    return {
        "reconciled": True,
        "skipped": False,
        "reason": "forced" if force else "reconciled",
        "reconcile_epoch": CURRENT_RECONCILE_EPOCH,
        "last_reconciled_version": pf_version,
        "last_reconciled_at": now_iso,
        "manifest_path": str(manifest_path),
        "db_reconciled": db_res["db_reconciled"],
        "workspace_registry_upserted": db_res["workspace_registry_upserted"],
        "workspace_registry_removed": db_res["workspace_registry_removed"],
        "papers_paths_healed": db_res["papers_paths_healed"],
        "fts_repaired": db_res["fts_repaired"],
        "zombie_running_healed": len(all_zombie_healed_keys),
        "index_normalized": idx_res["index_normalized"],
        "index_entries_updated": idx_res["index_entries_updated"],
        "bases_refreshed": refreshed_bases,
        "state_seq": int(seq_payload.get("seq") or 0),
    }
