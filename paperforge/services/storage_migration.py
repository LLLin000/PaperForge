"""Vault storage migration from visible System/PaperForge to hidden .paperforge/."""
from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import re
import shutil
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any

from paperforge.config import bootstrap_config, load_config, resolve_paths, set_config
from paperforge.core.fs_safe import is_windows_reserved_name, safe_is_dir, safe_is_file, safe_iterdir
from paperforge.core.io import write_bytes_atomic, write_json_atomic, write_text_atomic
from paperforge.worker.asset_index import cleanup_or_preserve_workspace_fulltext, sync_workspace_visual_assets

logger = logging.getLogger(__name__)

_VISUAL_MD_EMBED_RE = re.compile(
    r"!\[\[(?:[^\[\]|]*/)?((?:figure|table)_\d+)\.(?:md|jpg)(\|[^\[\]]*)?\]\]",
    re.IGNORECASE,
)

_MERGEABLE_JSONL_LOGS = frozenset({"reading-log.jsonl", "project-log.jsonl", "correction-log.jsonl"})
_JOURNAL_FLUSH_MUTATION_INTERVAL = 50
_JOURNAL_FLUSH_TIME_INTERVAL_SEC = 1.0


def quiesce_sqlite_wal(db_path: Path) -> bool:
    """Checkpoint and exit WAL mode cleanly before moving a SQLite DB across directories."""
    from paperforge.services.identity_resolver import is_reparse_or_symlink

    if is_windows_reserved_name(db_path.name) or is_reparse_or_symlink(db_path) or not safe_is_file(db_path):
        return False
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.commit()
    except (sqlite3.Error, OSError):
        return False
    finally:
        if conn is not None:
            with contextlib.suppress(sqlite3.Error):
                conn.close()

    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if safe_is_file(sidecar):
            with contextlib.suppress(OSError):
                if sidecar.stat().st_size == 0:
                    sidecar.unlink()
    return True


def _score_sqlite_richness(db_path: Path) -> tuple[int, int, int, int]:
    """Score SQLite DB richness as ``(total_vec_rows, papers_count, permanent_log_rows, size_bytes)``."""
    if not safe_is_file(db_path):
        return (0, 0, 0, 0)
    try:
        size_bytes = int(db_path.stat().st_size)
    except OSError:
        return (0, 0, 0, 0)

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        existing = {
            str(r[0])
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }

        def _count(tbl: str) -> int:
            if tbl not in existing:
                return 0
            row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            return int(row[0]) if row else 0

        total_vec_rows = (
            _count("vec_body_meta") + _count("vec_objects_meta") + _count("vec_fulltext_meta")
        )
        papers_count = _count("papers")
        permanent_log_rows = (
            _count("reading_log")
            + _count("project_log")
            + _count("paper_annotations")
            + _count("paper_memory_cards")
        )
        return (total_vec_rows, papers_count, permanent_log_rows, size_bytes)
    except (sqlite3.Error, OSError):
        return (0, 0, 0, 0)
    finally:
        if conn is not None:
            with contextlib.suppress(sqlite3.Error):
                conn.close()


def _score_formal_index_richness(idx_path: Path) -> tuple[int, int]:
    """Score formal-library.json richness as ``(item_count, size_bytes)``."""
    if not safe_is_file(idx_path):
        return (0, 0)
    try:
        size_bytes = int(idx_path.stat().st_size)
        raw = json.loads(idx_path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return (len(raw), size_bytes)
        if isinstance(raw, dict):
            items = raw.get("items")
            if isinstance(items, list):
                return (len(items), size_bytes)
        return (0, size_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return (0, 0)


def _unique_dest_path(dest_dir: Path, filename: str) -> Path:
    """Return a non-colliding path inside *dest_dir*."""
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{stem}__{counter}{suffix}"
        counter += 1
    return dest


def _merge_jsonl_by_id(
    src_path: Path,
    dst_path: Path,
    conflict_backup_dir: Path | None,
) -> int:
    """Union-merge two JSONL files by ``id`` / ``ann_id`` (or line hash) with pre-merge backups."""
    if conflict_backup_dir is not None:
        jsonl_bak_dir = conflict_backup_dir / "jsonl_merge"
        jsonl_bak_dir.mkdir(parents=True, exist_ok=True)
        if safe_is_file(dst_path):
            shutil.copy2(str(dst_path), str(_unique_dest_path(jsonl_bak_dir, f"dst__{dst_path.name}")))
        if safe_is_file(src_path):
            shutil.copy2(str(src_path), str(_unique_dest_path(jsonl_bak_dir, f"src__{src_path.name}")))

    merged: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for path in (dst_path, src_path):
        if not safe_is_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("id"):
                dedup_key = ("id", str(obj["id"]))
            elif obj.get("ann_id"):
                dedup_key = ("ann_id", str(obj["ann_id"]))
            else:
                digest = hashlib.sha256(
                    json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                dedup_key = ("hash", digest)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            merged.append(obj)

    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in merged)
    write_text_atomic(dst_path, payload)

    if conflict_backup_dir is not None and safe_is_file(src_path):
        merged_dir = conflict_backup_dir / "merged_sources"
        merged_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(_unique_dest_path(merged_dir, f"{src_path.parent.name}__{src_path.name}")))

    return len(merged)


def _ensure_wal_quiesced(db_path: Path) -> None:
    """Enforce WAL checkpoint before moving or arbitrating a SQLite DB with non-empty WAL."""
    ok = quiesce_sqlite_wal(db_path)
    if not ok:
        wal_path = Path(f"{db_path}-wal")
        if safe_is_file(wal_path):
            try:
                if wal_path.stat().st_size > 0:
                    raise OSError(f"Cannot quiesce active WAL for {db_path.name}; aborting move safely")
            except OSError:
                raise


def rewrite_visual_embeds_for_key(
    markdown: str,
    zotero_key: str,
    *,
    available_assets: set[str] | None = None,
) -> tuple[str, int]:
    """Rewrite legacy object embeds to ``![[<KEY>_figure_001.jpg]]`` inside one note."""
    replacements = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal replacements
        obj_stem = match.group(1)
        alias = match.group(2) or ""
        prefix = f"{zotero_key}_"
        stem = obj_stem if obj_stem.startswith(prefix) else f"{prefix}{obj_stem}"
        filename = unicodedata.normalize("NFC", f"{stem}.jpg")
        if available_assets is not None and filename not in available_assets:
            return match.group(0)
        target = f"![[{filename}{alias}]]"
        if target != match.group(0):
            replacements += 1
        return target

    updated = _VISUAL_MD_EMBED_RE.sub(_sub, markdown)
    return updated, replacements


def _move_tree_entries(
    src_dir: Path,
    dst_dir: Path,
    *,
    dry_run: bool,
    moved_pairs: list[tuple[Path, Path]] | None = None,
    conflict_backup_dir: Path | None = None,
    on_progress=None,
) -> dict[str, int]:
    """Move directories and files from *src_dir* into *dst_dir* safely.

    Never overwrites existing destination files blindly. Applies WAL quiesce,
    Rich-Wins arbitration for ``paperforge.db`` and ``formal-library.json``,
    union-by-id merge for permanent JSONL logs, and SHA-256 quarantine for
    other collisions.
    """
    from paperforge.services.identity_resolver import is_reparse_or_symlink

    counts = {
        "moved": 0,
        "skipped_existing": 0,
        "conflicts_quarantined": 0,
        "skipped_user_or_symlink": 0,
    }
    if (
        is_windows_reserved_name(src_dir.name)
        or not safe_is_dir(src_dir)
        or is_reparse_or_symlink(src_dir)
        or src_dir.resolve() == dst_dir.resolve()
    ):
        return counts
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
    for child in safe_iterdir(src_dir):
        if is_windows_reserved_name(child.name) or is_reparse_or_symlink(child):
            counts["skipped_user_or_symlink"] += 1
            continue
        # Remove empty 0-byte SQLite WAL/SHM sidecars so they do not clutter cutover or collide
        if child.name.endswith(("-wal", "-shm")) and safe_is_file(child):
            try:
                if child.stat().st_size == 0:
                    if not dry_run:
                        child.unlink()
                    continue
            except OSError:
                pass
        # Protect unknown user Markdown notes placed at engine root from vanishing into hidden .paperforge/
        if (
            safe_is_file(child)
            and child.suffix.lower() == ".md"
            and child.name not in ("deep-reading-queue.md", "_loss_survey_expanded.md", "bio-analysis-for-gpt.md")
            and src_dir.name == "PaperForge"
        ):
            counts["skipped_user_or_symlink"] += 1
            continue

        if safe_is_file(child) and child.suffix.lower() == ".db" and not dry_run:
            _ensure_wal_quiesced(child)

        target = dst_dir / child.name
        if not target.exists():
            if not dry_run:
                shutil.move(str(child), str(target))
                if moved_pairs is not None:
                    moved_pairs.append((child, target))
                if on_progress is not None:
                    on_progress()
            counts["moved"] += 1
        elif safe_is_dir(child) and safe_is_dir(target):
            sub = _move_tree_entries(
                child,
                target,
                dry_run=dry_run,
                moved_pairs=moved_pairs,
                conflict_backup_dir=conflict_backup_dir,
                on_progress=on_progress,
            )
            counts["moved"] += sub["moved"]
            counts["skipped_existing"] += sub["skipped_existing"]
            counts["conflicts_quarantined"] += sub["conflicts_quarantined"]
            counts["skipped_user_or_symlink"] += sub["skipped_user_or_symlink"]
            if not dry_run:
                with contextlib.suppress(OSError):
                    if not safe_iterdir(child):
                        child.rmdir()
        elif safe_is_file(child) and safe_is_file(target) and conflict_backup_dir is not None:
            if child.name in _MERGEABLE_JSONL_LOGS:
                if not dry_run:
                    _merge_jsonl_by_id(child, target, conflict_backup_dir)
                    if on_progress is not None:
                        on_progress()
                counts["conflicts_quarantined"] += 1
                continue

            if child.name == "paperforge.db":
                if not dry_run:
                    _ensure_wal_quiesced(target)
                src_wins = _score_sqlite_richness(child) > _score_sqlite_richness(target)
                if src_wins:
                    if not dry_run:
                        loser_dir = conflict_backup_dir / "rich_wins_loser"
                        loser_dir.mkdir(parents=True, exist_ok=True)
                        archived_loser = _unique_dest_path(loser_dir, f"{target.parent.name}__{target.name}")
                        shutil.move(str(target), str(archived_loser))
                        shutil.move(str(child), str(target))
                        if moved_pairs is not None:
                            moved_pairs.append((target, archived_loser))
                            moved_pairs.append((child, target))
                        if on_progress is not None:
                            on_progress()
                    counts["conflicts_quarantined"] += 1
                    continue

            if child.name == "formal-library.json":
                src_wins = _score_formal_index_richness(child) > _score_formal_index_richness(target)
                if src_wins:
                    if not dry_run:
                        loser_dir = conflict_backup_dir / "rich_wins_loser"
                        loser_dir.mkdir(parents=True, exist_ok=True)
                        archived_loser = _unique_dest_path(loser_dir, f"{target.parent.name}__{target.name}")
                        shutil.move(str(target), str(archived_loser))
                        shutil.move(str(child), str(target))
                        if moved_pairs is not None:
                            moved_pairs.append((target, archived_loser))
                            moved_pairs.append((child, target))
                        if on_progress is not None:
                            on_progress()
                    counts["conflicts_quarantined"] += 1
                    continue

            same_content = False
            with contextlib.suppress(OSError):
                same_content = (
                    hashlib.sha256(child.read_bytes()).hexdigest()
                    == hashlib.sha256(target.read_bytes()).hexdigest()
                )
            sub_dir = "duplicates" if same_content else "conflicts"
            if not dry_run:
                dest_dir = conflict_backup_dir / sub_dir
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = _unique_dest_path(dest_dir, f"{child.parent.name}__{child.name}")
                shutil.move(str(child), str(dest))
                if moved_pairs is not None:
                    moved_pairs.append((child, dest))
                if on_progress is not None:
                    on_progress()
            counts["conflicts_quarantined"] += 1
        else:
            counts["skipped_existing"] += 1
    if not dry_run:
        with contextlib.suppress(OSError):
            if safe_is_dir(src_dir) and not safe_iterdir(src_dir):
                src_dir.rmdir()
    return counts


def _rollback_mutations(
    *,
    rewritten_notes: list[tuple[Path, str]],
    restorable_fulltexts: list[tuple[Path, bytes | Path]],
    created_assets: list[Path],
    moved_pairs: list[tuple[Path, Path]],
    config_restorer=None,
) -> None:
    """Best-effort reverse rollback of all filesystem mutations recorded during migration."""
    if config_restorer is not None:
        with contextlib.suppress(Exception):
            config_restorer()
    for ft_path, raw_or_bak in reversed(restorable_fulltexts):
        with contextlib.suppress(OSError):
            data = raw_or_bak.read_bytes() if isinstance(raw_or_bak, Path) else raw_or_bak
            ft_path.parent.mkdir(parents=True, exist_ok=True)
            write_bytes_atomic(ft_path, data)
    for note_path, orig_text in reversed(rewritten_notes):
        with contextlib.suppress(OSError):
            write_text_atomic(note_path, orig_text)
    for asset_path in reversed(created_assets):
        with contextlib.suppress(OSError):
            if asset_path.is_file():
                asset_path.unlink()
    for src_p, dst_p in reversed(moved_pairs):
        with contextlib.suppress(OSError):
            if dst_p.exists() and not src_p.exists():
                src_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst_p), str(src_p))


def _validate_vault_contained_path(
    raw: str | Path,
    *,
    allowed_root: Path,
    allow_root: bool = False,
    label: str = "path",
) -> Path:
    """Fail-closed containment check: reject empty, ``..``, symlinks, or paths escaping *allowed_root*."""
    from paperforge.worker.trash import DangerousPathError

    text = str(raw or "").strip()
    if not text or text in (".", ".."):
        raise DangerousPathError(f"forbidden {label}: {text!r}")
    p = Path(text)
    if p.is_symlink():
        raise DangerousPathError(f"refusing symlink {label}: {p}")
    root_resolved = allowed_root.resolve()
    resolved = p.resolve()
    if not allow_root and resolved == root_resolved:
        raise DangerousPathError(f"{label} points to forbidden root {root_resolved}")
    if not resolved.is_relative_to(root_resolved):
        raise DangerousPathError(f"{label} escapes allowed root {root_resolved}: {resolved}")
    return resolved


def _load_rewritten_notes_for_rollback(
    items: list[Any],
    *,
    vault_root: Path,
    dot_pf_root: Path,
    label_prefix: str = "rewritten_notes",
) -> list[tuple[Path, str]]:
    """Load note rollback records supporting both inline ``original_text`` and external ``backup`` paths."""
    restored: list[tuple[Path, str]] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        note_path = _validate_vault_contained_path(
            item["path"],
            allowed_root=vault_root,
            label=f"{label_prefix}.path",
        )
        if "original_text" in item:
            restored.append((note_path, str(item["original_text"])))
        elif item.get("backup"):
            bak_path = _validate_vault_contained_path(
                item["backup"],
                allowed_root=dot_pf_root,
                label=f"{label_prefix}.backup",
            )
            if safe_is_file(bak_path):
                with contextlib.suppress(OSError, UnicodeDecodeError):
                    restored.append((note_path, bak_path.read_text(encoding="utf-8")))
    return restored


def rollback_incomplete_migration(vault: Path) -> dict[str, Any]:
    """Roll back an interrupted ``in_progress`` migration using ``.migration-journal.json``."""
    vault_root = Path(vault).expanduser().resolve()
    dot_pf_root = (vault_root / ".paperforge").resolve()
    journal_path = dot_pf_root / ".migration-journal.json"
    if not safe_is_file(journal_path):
        return {"recovered": False, "state": "no_journal"}
    data = json.loads(journal_path.read_text(encoding="utf-8"))
    if data.get("state") != "in_progress":
        return {"recovered": False, "state": str(data.get("state") or "unknown")}

    moved_pairs = [
        (
            _validate_vault_contained_path(item["src"], allowed_root=vault_root, label="moved_pairs.src"),
            _validate_vault_contained_path(item["dst"], allowed_root=vault_root, label="moved_pairs.dst"),
        )
        for item in (data.get("moved_pairs") or [])
        if isinstance(item, dict) and item.get("src") and item.get("dst")
    ]
    rewritten_notes = _load_rewritten_notes_for_rollback(
        list(data.get("rewritten_notes") or []),
        vault_root=vault_root,
        dot_pf_root=dot_pf_root,
        label_prefix="rewritten_notes",
    )
    created_assets = [
        _validate_vault_contained_path(p, allowed_root=vault_root, label="created_assets")
        for p in (data.get("created_assets") or [])
    ]
    restorable_fulltexts: list[tuple[Path, bytes]] = []
    for pf_item in (data.get("preserved_fulltexts") or []):
        if isinstance(pf_item, dict) and pf_item.get("orig") and pf_item.get("backup"):
            orig_p = _validate_vault_contained_path(
                pf_item["orig"], allowed_root=vault_root, label="preserved_fulltexts.orig"
            )
            bp = _validate_vault_contained_path(
                pf_item["backup"], allowed_root=dot_pf_root, label="preserved_fulltexts.backup"
            )
            if safe_is_file(bp):
                with contextlib.suppress(OSError):
                    restorable_fulltexts.append((orig_p, bp.read_bytes()))

    prev_sys = data.get("previous_system_dir")

    def _restore_cfg() -> None:
        if prev_sys and (vault_root / "paperforge.json").is_file():
            set_config(vault_root, "system_dir", str(prev_sys))

    _rollback_mutations(
        rewritten_notes=rewritten_notes,
        restorable_fulltexts=restorable_fulltexts,
        created_assets=created_assets,
        moved_pairs=moved_pairs,
        config_restorer=_restore_cfg if prev_sys else None,
    )
    write_json_atomic(
        journal_path,
        {
            "state": "rolled_back",
            "reason": "journal_recovery",
            "rolled_back_moves": len(moved_pairs),
            "rolled_back_notes": len(rewritten_notes),
        },
    )
    return {
        "recovered": True,
        "state": "rolled_back",
        "rolled_back_moves": len(moved_pairs),
        "rolled_back_notes": len(rewritten_notes),
    }


def migrate_vault_storage(
    vault: Path,
    *,
    dry_run: bool = False,
    isolate_paper_errors: bool = False,
    backup_dir: Path | None = None,
    scan: Any | None = None,
) -> dict[str, Any]:
    """Transactionally migrate an existing vault to `.paperforge/` with rollback."""
    vault_root = Path(vault).expanduser().resolve()
    cfg_path = vault_root / "paperforge.json"
    previous_system_dir: str | None = None
    if cfg_path.exists():
        # Fail closed BEFORE mutating disk if config is corrupt or requires schema migration.
        snapshot = load_config(vault_root)
        previous_system_dir = str(snapshot.values["system_dir"].value)
        paths = resolve_paths(vault_root, snapshot)
        old_sys = paths["system"]
        old_pf = paths["paperforge"]
        lit_root = paths["literature"]
    else:
        old_sys = vault_root / "System"
        old_pf = old_sys / "PaperForge"
        lit_root = vault_root / "Resources" / "Literature"

    if not safe_is_dir(old_pf):
        from paperforge.services.vault_upgrade import _find_legacy_engine_dirs

        cands = _find_legacy_engine_dirs(vault_root, previous_system_dir or "")
        if cands:
            old_pf = cands[0]
            old_sys = old_pf.parent

    target_pf = vault_root / ".paperforge"
    journal_path = target_pf / ".migration-journal.json"
    conflict_backup_dir = target_pf / "backups" / "storage-migration"
    moved_pairs: list[tuple[Path, Path]] = []
    rewritten_notes: list[tuple[Path, str]] = []
    journal_notes: list[dict[str, str]] = []
    created_assets: list[Path] = []
    restorable_fulltexts: list[tuple[Path, bytes]] = []
    journal_fulltexts: list[dict[str, str]] = []
    paper_errors: list[dict[str, str]] = []
    config_updated = False

    if cfg_path.exists():
        raw_zotero = str(snapshot.values["zotero_data_dir"].value or "").strip()
        if raw_zotero:
            zp = Path(raw_zotero)
            _ = (zp if zp.is_absolute() else (vault_root / zp)).resolve()

    mutations_since_flush = 0
    last_flush_at = 0.0

    def _flush_journal(*, force: bool = False) -> None:
        nonlocal mutations_since_flush, last_flush_at
        if dry_run:
            return
        now = time.monotonic()
        if not force:
            mutations_since_flush += 1
            if (
                mutations_since_flush < _JOURNAL_FLUSH_MUTATION_INTERVAL
                and (now - last_flush_at) < _JOURNAL_FLUSH_TIME_INTERVAL_SEC
            ):
                return
        mutations_since_flush = 0
        last_flush_at = now
        write_json_atomic(
            journal_path,
            {
                "state": "in_progress",
                "source_engine_dir": str(old_pf),
                "target_engine_dir": str(target_pf),
                "previous_system_dir": previous_system_dir,
                "moved_pairs": [{"src": str(s), "dst": str(d)} for s, d in moved_pairs],
                "rewritten_notes": list(journal_notes),
                "created_assets": [str(p) for p in created_assets],
                "preserved_fulltexts": journal_fulltexts,
            },
        )

    def _restore_config_if_needed() -> None:
        if config_updated and previous_system_dir and cfg_path.is_file():
            set_config(vault_root, "system_dir", previous_system_dir)

    _flush_journal(force=True)

    moved_zotero = False
    zotero_preserved_in_place = False
    ocr_root = target_pf / "ocr" if not dry_run or not old_pf.exists() else old_pf / "ocr"
    assets_copied = 0
    notes_rewritten = 0
    workspace_copies_removed = 0
    workspace_copies_preserved = 0
    tree_counts = {"moved": 0, "skipped_existing": 0, "conflicts_quarantined": 0}

    try:
        tree_counts = _move_tree_entries(
            old_pf,
            target_pf,
            dry_run=dry_run,
            moved_pairs=moved_pairs,
            conflict_backup_dir=conflict_backup_dir,
            on_progress=_flush_journal,
        )
        _flush_journal(force=True)

        old_zotero = old_sys / "Zotero"
        if old_zotero.exists() and not old_zotero.is_symlink():
            # Never bury a user Zotero library inside hidden `.paperforge/`
            zotero_preserved_in_place = True

        if safe_is_dir(lit_root):
            from paperforge.services.identity_resolver import scan_vault_identities

            id_scan = scan if scan is not None else scan_vault_identities(lit_root)
            notes_bak_dir_ready = False
            ft_bak_dir_ready = False
            notes_bak_dir = conflict_backup_dir / "notes"
            ft_bak_dir = conflict_backup_dir / "fulltexts"
            ws_targets: list[tuple[str, Path, Any | None]] = [
                (key, ws_info.workspace_dir, ws_info)
                for key, ws_info in sorted(id_scan.workspaces.items())
            ]
            seen_ws_dirs = {ws_dir.resolve() for _, ws_dir, _ in ws_targets}
            # Fallback for un-anchored/bare legacy folders (`<KEY> - <Title>/`)
            for domain_dir in safe_iterdir(lit_root):
                if not safe_is_dir(domain_dir):
                    continue
                for candidate_dir in safe_iterdir(domain_dir):
                    if not safe_is_dir(candidate_dir) or " - " not in candidate_dir.name:
                        continue
                    if candidate_dir.resolve() in seen_ws_dirs:
                        continue
                    legacy_key = candidate_dir.name.split(" - ", 1)[0].strip()
                    if legacy_key:
                        ws_targets.append((legacy_key, candidate_dir, None))
                        seen_ws_dirs.add(candidate_dir.resolve())

            for key, ws_dir, ws_info in ws_targets:
                p_rewritten_start = len(rewritten_notes)
                p_journal_notes_start = len(journal_notes)
                p_fulltext_start = len(restorable_fulltexts)
                p_assets_start = len(created_assets)
                try:
                    paper_ocr_dir = ocr_root / key
                    if safe_is_dir(paper_ocr_dir):
                        if dry_run:
                            assets_src = paper_ocr_dir / "assets"
                            if safe_is_dir(assets_src):
                                for sub in ("figures", "tables"):
                                    if safe_is_dir(assets_src / sub):
                                        assets_copied += sum(1 for _ in (assets_src / sub).glob("*.jpg"))
                        else:
                            ws_assets_dir = ws_dir / "assets"
                            existing_before = (
                                {p.name for p in safe_iterdir(ws_assets_dir)}
                                if safe_is_dir(ws_assets_dir)
                                else set()
                            )
                            copied = sync_workspace_visual_assets(paper_ocr_dir, ws_dir, key)
                            assets_copied += len(copied)
                            for fname in copied:
                                if fname not in existing_before:
                                    created_assets.append(ws_assets_dir / fname)

                    note_candidates: list[Path] = []
                    if ws_info is not None:
                        if ws_info.main_note_path is not None:
                            note_candidates.append(ws_info.main_note_path)
                        note_candidates.extend(ws_info.legacy_named_notes)
                    note_candidates.extend(
                        [
                            ws_dir / f"{key}.md",
                            ws_dir / f"{ws_dir.name}.md",
                            ws_dir.parent / f"{key}.md",
                        ]
                    )
                    ws_assets_dir = ws_dir / "assets"
                    avail_assets: set[str] | None = None
                    if not dry_run:
                        if safe_is_dir(ws_assets_dir):
                            avail_assets = {
                                unicodedata.normalize("NFC", p.name)
                                for p in ws_assets_dir.glob("*.jpg")
                            }
                        elif safe_is_dir(paper_ocr_dir / "assets"):
                            avail_assets = set()

                    seen_notes: set[Path] = set()
                    for candidate_note in note_candidates:
                        if safe_is_file(candidate_note):
                            resolved_note = candidate_note.resolve()
                            if resolved_note in seen_notes:
                                continue
                            seen_notes.add(resolved_note)
                            original = candidate_note.read_text(encoding="utf-8")
                            updated, count = rewrite_visual_embeds_for_key(
                                original, key, available_assets=avail_assets
                            )
                            if count > 0:
                                notes_rewritten += 1
                                if not dry_run:
                                    note_bak_path = _unique_dest_path(
                                        notes_bak_dir,
                                        f"{key}__{candidate_note.name}",
                                    )
                                    if not notes_bak_dir_ready:
                                        note_bak_path.parent.mkdir(parents=True, exist_ok=True)
                                        notes_bak_dir_ready = True
                                    note_bak_path.write_text(original, encoding="utf-8")
                                    rewritten_notes.append((candidate_note, original))
                                    journal_notes.append(
                                        {"path": str(candidate_note), "backup": str(note_bak_path)}
                                    )
                                    _flush_journal()
                                    write_text_atomic(candidate_note, updated)

                    ocr_dir_for_verify = (
                        paper_ocr_dir
                        if safe_is_dir(paper_ocr_dir)
                        else ((old_pf / "ocr" / key) if safe_is_dir(old_pf / "ocr" / key) else None)
                    )
                    ws_ft_path = ws_dir / "fulltext.md"
                    ft_snapshot = ws_ft_path.read_bytes() if (not dry_run and safe_is_file(ws_ft_path)) else None
                    trash_box: list[Path] = []
                    matched_box: list[Path] = []
                    outcome = cleanup_or_preserve_workspace_fulltext(
                        ws_dir,
                        vault=vault_root,
                        ocr_paper_dir=ocr_dir_for_verify,
                        lit_root=lit_root,
                        paper_key=key,
                        dry_run=dry_run,
                        ws_bytes=ft_snapshot,
                        out_trash_path=trash_box,
                        out_matched_path=matched_box,
                    )
                    if ft_snapshot is not None and outcome in ("removed_verified_mirror", "preserved_to_trash"):
                        dot_pf_resolved = target_pf.resolve()
                        reusable_backup: Path | None = None
                        if outcome == "preserved_to_trash" and trash_box and trash_box[0].is_file():
                            reusable_backup = trash_box[0]
                        elif outcome == "removed_verified_mirror" and matched_box and matched_box[0].is_file():
                            try:
                                if matched_box[0].resolve().is_relative_to(dot_pf_resolved):
                                    reusable_backup = matched_box[0]
                            except (OSError, ValueError):
                                reusable_backup = None

                        if reusable_backup is not None:
                            journal_fulltexts.append({"orig": str(ws_ft_path), "backup": str(reusable_backup)})
                            restorable_fulltexts.append((ws_ft_path, reusable_backup))
                        else:
                            snap_backup = ft_bak_dir / f"{key}.md"
                            if not ft_bak_dir_ready:
                                snap_backup.parent.mkdir(parents=True, exist_ok=True)
                                ft_bak_dir_ready = True
                            write_bytes_atomic(snap_backup, ft_snapshot)
                            journal_fulltexts.append({"orig": str(ws_ft_path), "backup": str(snap_backup)})
                            restorable_fulltexts.append((ws_ft_path, snap_backup))
                        _flush_journal()
                    if outcome in ("removed_verified_mirror", "preserved_to_trash"):
                        workspace_copies_removed += 1
                    if outcome == "preserved_to_trash":
                        workspace_copies_preserved += 1
                except Exception as paper_exc:  # noqa: BLE001
                    if not isolate_paper_errors:
                        raise
                    if not dry_run:
                        # Roll back this failed paper's partial mutations so its workspace stays clean
                        _rollback_mutations(
                            rewritten_notes=rewritten_notes[p_rewritten_start:],
                            restorable_fulltexts=restorable_fulltexts[p_fulltext_start:],
                            created_assets=created_assets[p_assets_start:],
                            moved_pairs=[],
                            config_restorer=lambda: None,
                        )
                        del rewritten_notes[p_rewritten_start:]
                        del journal_notes[p_journal_notes_start:]
                        del restorable_fulltexts[p_fulltext_start:]
                        del created_assets[p_assets_start:]
                    paper_errors.append({"key": key, "error": str(paper_exc)})

        final_state = "partial_success" if paper_errors else "completed"
        if not dry_run:
            if not cfg_path.exists():
                bootstrap_config(vault_root)
            set_config(vault_root, "system_dir", ".paperforge")
            config_updated = True

            for leftover in (old_pf, old_sys):
                with contextlib.suppress(OSError):
                    if (
                        safe_is_dir(leftover)
                        and leftover.resolve() != target_pf.resolve()
                        and not safe_iterdir(leftover)
                    ):
                        leftover.rmdir()

            serialized_pairs = [{"src": str(s), "dst": str(d)} for s, d in moved_pairs]
            serialized_notes = list(journal_notes)
            serialized_assets = [str(p) for p in created_assets]
            if backup_dir is not None:
                backup_dir.mkdir(parents=True, exist_ok=True)
                write_json_atomic(backup_dir / "moved-pairs.json", serialized_pairs)
                write_json_atomic(
                    backup_dir / "migration-mutations.json",
                    {
                        "rewritten_notes": serialized_notes,
                        "created_assets": serialized_assets,
                        "preserved_fulltexts": journal_fulltexts,
                    },
                )
            write_json_atomic(
                journal_path,
                {
                    "state": final_state,
                    "mode": "full",
                    "source_engine_dir": str(old_pf),
                    "target_engine_dir": str(target_pf),
                    "previous_system_dir": previous_system_dir,
                    "moved_pairs": serialized_pairs,
                    "rewritten_notes": serialized_notes,
                    "created_assets": serialized_assets,
                    "preserved_fulltexts": journal_fulltexts,
                    "entries_moved": tree_counts["moved"],
                    "conflicts_quarantined": tree_counts["conflicts_quarantined"],
                    "notes_rewritten": notes_rewritten,
                    "workspace_fulltexts_removed": workspace_copies_removed,
                    "workspace_fulltexts_preserved": workspace_copies_preserved,
                    "paper_errors": paper_errors,
                },
            )
    except Exception as exc:  # noqa: BLE001 — any mid-migration failure triggers atomic rollback
        if not dry_run:
            _flush_journal(force=True)
            _rollback_mutations(
                rewritten_notes=rewritten_notes,
                restorable_fulltexts=restorable_fulltexts,
                created_assets=created_assets,
                moved_pairs=moved_pairs,
                config_restorer=_restore_config_if_needed,
            )
            with contextlib.suppress(OSError):
                write_json_atomic(
                    journal_path,
                    {
                        "state": "rolled_back",
                        "error": str(exc),
                        "rolled_back_moves": len(moved_pairs),
                        "rolled_back_notes": len(rewritten_notes),
                        "rolled_back_assets": len(created_assets),
                    },
                )
        raise RuntimeError(f"Storage migration rolled back due to failure: {exc}") from exc

    return {
        "dry_run": dry_run,
        "state": "partial_success" if paper_errors else "completed",
        "target_engine_dir": ".paperforge",
        "entries_moved": tree_counts["moved"],
        "entries_skipped_existing": tree_counts["skipped_existing"],
        "conflicts_quarantined": tree_counts["conflicts_quarantined"],
        "moved_zotero_dir": moved_zotero,
        "zotero_preserved_in_place": zotero_preserved_in_place,
        "visual_assets_materialized": assets_copied,
        "notes_rewritten": notes_rewritten,
        "workspace_fulltexts_removed": workspace_copies_removed,
        "workspace_fulltexts_preserved": workspace_copies_preserved,
        "paper_errors": paper_errors,
        "config_updated": config_updated,
    }
