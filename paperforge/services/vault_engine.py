"""Unified File & State Engine (`VaultEngine`) — ADR-018 / ADR-0006.

Consolidates:
1. Quarantine-first file removal (zero bare unlink/rmtree in runtime flows).
2. Explicit ``.paperforge/vault-manifest.json`` layout versioning & audit trail.
3. SQLite SSOT tables inside ``paperforge.db`` (``workspace_registry``,
   ``ocr_catalog``, ``vault_kv``, ``engine_jobs``).
4. Calibre-style lossless DB reconstruction from per-paper plaintext truths
   (Zotero BBT exports + workspace identities + ``annotations.jsonl`` +
   ``ai/memory-card.json`` + ``.paperforge/ocr/<KEY>/``).
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json_atomic

logger = logging.getLogger(__name__)

VAULT_MANIFEST_FILENAME = "vault-manifest.json"
CURRENT_LAYOUT_VERSION = 2


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utcnow_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _engine_root(vault: Path) -> Path:
    vault_root = Path(vault).expanduser().resolve()
    try:
        from paperforge.config import paperforge_paths

        return paperforge_paths(vault_root)["paperforge"]
    except Exception:  # noqa: BLE001
        from paperforge.config import fallback_paperforge_dir

        return fallback_paperforge_dir(vault_root)


def quarantine_move(
    target: Path | None,
    *,
    vault: Path,
    allowed_root: Path,
    operation: str,
    paper_key: str = "",
    backup_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Safely move *target* into trash or an explicit backup quarantine dir — never delete.

    When *backup_dir* is omitted, delegates to :func:`paperforge.worker.trash.trash_remove`.
    When *backup_dir* is provided, moves the resolved target inside
    ``backup_dir/<uuid>/<name>`` and records a ``manifest.json`` after
    enforcing the same fail-closed containment check.
    """
    from paperforge.worker.trash import DangerousPathError, MANIFEST_NAME, trash_remove, validate_target

    if backup_dir is None:
        return trash_remove(
            target,
            vault=vault,
            allowed_root=allowed_root,
            operation=operation,
            paper_key=paper_key,
        )

    try:
        resolved = validate_target(target, allowed_root=allowed_root)
    except DangerousPathError as exc:
        if str(exc).startswith("target does not exist"):
            return None
        raise

    record_id = uuid.uuid4().hex[:12]
    dest_root = Path(backup_dir) / record_id
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / resolved.name
    shutil.move(str(resolved), str(dest))
    manifest = {
        "quarantine_id": record_id,
        "operation": operation,
        "paper_key": paper_key,
        "original_path": str(resolved),
        "quarantine_path": str(dest),
        "timestamp": _utcnow_compact(),
        "quarantined_at": _utcnow_iso(),
    }
    write_json_atomic(dest_root / MANIFEST_NAME, manifest)
    logger.info("quarantined %s -> %s (%s)", resolved, dest, operation)
    return manifest


def vault_manifest_path(vault: Path) -> Path:
    return _engine_root(vault) / VAULT_MANIFEST_FILENAME


def read_vault_manifest(vault: Path) -> dict[str, Any] | None:
    """Read ``vault-manifest.json`` from ``.paperforge/`` (or configured engine dir)."""
    vault_root = Path(vault).expanduser().resolve()
    for cand in (
        vault_root / ".paperforge" / VAULT_MANIFEST_FILENAME,
        vault_manifest_path(vault_root),
    ):
        if cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                return None
    return None


def write_vault_manifest(
    vault: Path,
    *,
    migration_entry: dict[str, Any] | None = None,
    layout_version: int = CURRENT_LAYOUT_VERSION,
) -> Path:
    """Create or update ``.paperforge/vault-manifest.json`` atomically."""
    from paperforge import __version__ as pf_version
    from paperforge.memory.schema import CURRENT_SCHEMA_VERSION

    vault_root = Path(vault).expanduser().resolve()
    existing = read_vault_manifest(vault_root) or {}
    history = list(existing.get("migration_history") or [])
    if migration_entry is not None:
        history.append(migration_entry)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "layout_version": int(layout_version),
        "paperforge_version": pf_version,
        "engine_ssot": "sqlite",
        "db_schema_version": CURRENT_SCHEMA_VERSION,
        "default_system_dir": ".paperforge",
        "created_at": existing.get("created_at") or _utcnow_iso(),
        "updated_at": _utcnow_iso(),
        "migration_history": history[-50:],
    }
    target = vault_manifest_path(vault_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(target, payload)
    return target


def ensure_current_vault_manifest(vault: Path) -> Path | None:
    """Stamp ``.paperforge/vault-manifest.json`` on clean ``.paperforge`` setups without masking legacy layouts."""
    from paperforge.config import paperforge_paths
    from paperforge.services.vault_upgrade import detect_vault_provenance

    vault_root = Path(vault).expanduser().resolve()
    existing = read_vault_manifest(vault_root)
    if existing is not None and int(existing.get("layout_version") or 0) >= CURRENT_LAYOUT_VERSION:
        return vault_manifest_path(vault_root)

    paths = paperforge_paths(vault_root)
    if Path(paths["system"]).name != ".paperforge":
        return None

    prov = detect_vault_provenance(vault_root)
    tier1 = prov.get("tier1_evidence") or []
    if any(
        isinstance(ev, str)
        and (ev.startswith("legacy_engine_dir:") or ev.startswith("configured_legacy_engine:"))
        for ev in tier1
    ):
        return None

    return write_vault_manifest(vault_root)


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def sync_workspace_registry(
    vault: Path,
    *,
    lit_root: Path | None = None,
    prune_missing: bool = True,
) -> dict[str, Any]:
    """Scan structured identity anchors and upsert ``workspace_registry`` inside ``paperforge.db``."""
    from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.state_signal import bump_state_seq

    vault_root = Path(vault).expanduser().resolve()
    if lit_root is None:
        try:
            from paperforge.config import paperforge_paths

            lit_root = paperforge_paths(vault_root).get("literature")
        except Exception:  # noqa: BLE001
            lit_root = vault_root / "Resources" / "Literature"

    scan = scan_vault_identities(lit_root)
    db_path = get_memory_db_path(vault_root)
    now = _utcnow_iso()
    upserted = 0
    removed = 0

    with WriterLock(vault_root):
        conn = get_connection(db_path)
        try:
            ensure_schema(conn)
            for key, ws in scan.workspaces.items():
                try:
                    mtime_ns = int(ws.workspace_dir.stat().st_mtime_ns)
                except OSError:
                    mtime_ns = 0
                conn.execute(
                    """
                    INSERT OR REPLACE INTO workspace_registry (
                        zotero_key, domain, workspace_relpath, main_note_relpath,
                        dir_mtime_ns, identity_source, status, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        ws.domain,
                        _safe_rel(ws.workspace_dir, vault_root),
                        _safe_rel(ws.main_note_path, vault_root) if ws.main_note_path else "",
                        mtime_ns,
                        ",".join(ws.identity_sources),
                        "duplicate" if key in scan.duplicate_workspaces else "active",
                        now,
                    ),
                )
                upserted += 1

            if prune_missing:
                existing_keys = {
                    str(r[0]) for r in conn.execute("SELECT zotero_key FROM workspace_registry").fetchall()
                }
                stale_keys = existing_keys - set(scan.workspaces.keys())
                for sk in stale_keys:
                    conn.execute("DELETE FROM workspace_registry WHERE zotero_key = ?", (sk,))
                    removed += 1
            conn.commit()
        finally:
            conn.close()

    bump_state_seq(vault_root, reason="workspace_registry.sync", changed_keys=list(scan.workspaces)[:50])
    return {
        "upserted": upserted,
        "removed": removed,
        "flat_notes": len(scan.flat_notes),
        "duplicates": len(scan.duplicate_workspaces),
        "mismatches": scan.mismatches,
    }


def sync_ocr_catalog(
    vault: Path,
    *,
    keys: list[str] | None = None,
) -> dict[str, Any]:
    """Assess OCR atom health (Tier-0 truth vs Tier-1 derived) and persist into ``ocr_catalog``."""
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms
    from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.state_signal import bump_state_seq

    vault_root = Path(vault).expanduser().resolve()
    ocr_root = _engine_root(vault_root) / "ocr"
    reports: list[dict[str, Any]] = []
    if ocr_root.is_dir():
        target_dirs = (
            [ocr_root / k for k in keys if (ocr_root / k).is_dir()]
            if keys is not None
            else sorted(d for d in ocr_root.iterdir() if d.is_dir())
        )
        for pdir in target_dirs:
            reports.append(assess_ocr_bundle_atoms(pdir))

    db_path = get_memory_db_path(vault_root)
    now = _utcnow_iso()
    counts = {
        "current": 0,
        "rebuild_derived_local": 0,
        "backfill_from_result_json": 0,
        "re_ocr_needed": 0,
    }

    with WriterLock(vault_root):
        conn = get_connection(db_path)
        try:
            ensure_schema(conn)
            for rep in reports:
                act = rep["salvage_action"]
                counts[act] = counts.get(act, 0) + 1
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ocr_catalog (
                        zotero_key, ocr_status, tier0_truth_intact, result_json_sha256,
                        has_blocks_raw, has_blocks_structured, has_fulltext,
                        pipeline_version, salvage_action, derived_defects_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rep["zotero_key"],
                        rep["ocr_status"],
                        1 if rep["tier0_truth_intact"] else 0,
                        rep["tier0_sha256"],
                        1 if rep["has_blocks_raw"] else 0,
                        1 if rep["has_blocks_structured"] else 0,
                        1 if rep["has_fulltext"] else 0,
                        rep["pipeline_version"],
                        act,
                        json.dumps(rep["derived_defects"], ensure_ascii=False),
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    bump_state_seq(vault_root, reason="ocr_catalog.sync", changed_keys=[r["zotero_key"] for r in reports][:50])
    return {"total": len(reports), "counts": counts, "reports": reports}


def kv_get(vault: Path, key: str) -> Any | None:
    from paperforge.memory.db import get_memory_db_path, open_live_reader

    vault_root = Path(vault).expanduser().resolve()
    db_path = get_memory_db_path(vault_root)
    if not db_path.is_file():
        return None
    try:
        with open_live_reader(vault_root, db_path) as conn:
            has_tbl = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vault_kv'"
            ).fetchone()
            if not has_tbl:
                return None
            row = conn.execute("SELECT value_json FROM vault_kv WHERE key = ?", (key,)).fetchone()
            return json.loads(row[0]) if row else None
    except (sqlite3.Error, json.JSONDecodeError, OSError):
        return None


def kv_set(vault: Path, key: str, value: Any) -> None:
    from paperforge.memory.db import WriterLock, get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema

    vault_root = Path(vault).expanduser().resolve()
    db_path = get_memory_db_path(vault_root)
    payload = json.dumps(value, ensure_ascii=False)
    now = _utcnow_iso()
    with WriterLock(vault_root):
        conn = get_connection(db_path)
        try:
            ensure_schema(conn)
            conn.execute(
                "INSERT OR REPLACE INTO vault_kv (key, value_json, updated_at) VALUES (?, ?, ?)",
                (key, payload, now),
            )
            conn.commit()
        finally:
            conn.close()


def rebuild_db_from_truth(vault: Path, *, backup_existing: bool = True) -> dict[str, Any]:
    """Calibre-style lossless SQLite rebuild from per-paper plaintext truths on disk.

    Backs up any existing ``paperforge.db`` before rebuilding ``papers``,
    ``workspace_registry``, ``ocr_catalog``, and re-ingesting annotations,
    living memory cards, and permanent logs.
    """
    from paperforge.memory.builder import build_for_keys
    from paperforge.memory.db import get_memory_db_path, quarantine_corrupt_db

    vault_root = Path(vault).expanduser().resolve()
    db_path = get_memory_db_path(vault_root)
    backup_path_str = ""
    if backup_existing and db_path.is_file():
        backup_root = _engine_root(vault_root) / "backups" / f"db-rebuild-{_utcnow_compact()}"
        backup_root.mkdir(parents=True, exist_ok=True)
        dst = backup_root / db_path.name
        shutil.copy2(str(db_path), str(dst))
        backup_path_str = str(dst)

    quarantined_path = quarantine_corrupt_db(db_path)

    ws_res = sync_workspace_registry(vault_root)
    ocr_res = sync_ocr_catalog(vault_root)
    build_counts: dict[str, Any] = {}
    try:
        build_counts = build_for_keys(vault_root, None)
    except Exception as exc:  # noqa: BLE001 — partial truth vaults still retain registry & catalog
        build_counts = {"warning": str(exc)}

    out: dict[str, Any] = {
        "db_path": str(db_path),
        "backup_path": backup_path_str,
        "workspace_registry": {
            "upserted": ws_res["upserted"],
            "duplicates": ws_res["duplicates"],
        },
        "ocr_catalog": {
            "total": ocr_res["total"],
            "counts": ocr_res["counts"],
        },
        "memory_build": build_counts,
    }
    if quarantined_path is not None:
        out["quarantined_corrupt_db"] = str(quarantined_path)
    return out
