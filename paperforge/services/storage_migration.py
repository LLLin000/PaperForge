"""Vault storage migration from visible System/PaperForge to hidden .paperforge/."""
from __future__ import annotations

import contextlib
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from paperforge.config import bootstrap_config, load_config, resolve_paths, set_config
from paperforge.core.io import write_json_atomic, write_text_atomic
from paperforge.worker.asset_index import cleanup_or_preserve_workspace_fulltext, sync_workspace_visual_assets

logger = logging.getLogger(__name__)

_VISUAL_MD_EMBED_RE = re.compile(
    r"!\[\[(?:[^\[\]|]*/)?((?:figure|table)_\d+)\.(?:md|jpg)(\|[^\[\]]*)?\]\]",
    re.IGNORECASE,
)


def rewrite_visual_embeds_for_key(markdown: str, zotero_key: str) -> tuple[str, int]:
    """Rewrite legacy object embeds to ``![[<KEY>_figure_001.jpg]]`` inside one note."""
    replacements = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal replacements
        obj_stem = match.group(1)
        alias = match.group(2) or ""
        prefix = f"{zotero_key}_"
        stem = obj_stem if obj_stem.startswith(prefix) else f"{prefix}{obj_stem}"
        target = f"![[{stem}.jpg{alias}]]"
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
    on_progress=None,
) -> dict[str, int]:
    """Move directories and files from *src_dir* into *dst_dir* without overwriting existing entries."""
    counts = {"moved": 0, "skipped_existing": 0}
    if not src_dir.exists() or src_dir.resolve() == dst_dir.resolve():
        return counts
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_dir.iterdir()):
        target = dst_dir / child.name
        if not target.exists():
            if not dry_run:
                shutil.move(str(child), str(target))
                if moved_pairs is not None:
                    moved_pairs.append((child, target))
                if on_progress is not None:
                    on_progress()
            counts["moved"] += 1
        elif child.is_dir() and target.is_dir():
            sub = _move_tree_entries(
                child,
                target,
                dry_run=dry_run,
                moved_pairs=moved_pairs,
                on_progress=on_progress,
            )
            counts["moved"] += sub["moved"]
            counts["skipped_existing"] += sub["skipped_existing"]
            if not dry_run:
                with contextlib.suppress(OSError):
                    if not any(child.iterdir()):
                        child.rmdir()
        else:
            counts["skipped_existing"] += 1
    if not dry_run:
        with contextlib.suppress(OSError):
            if src_dir.exists() and not any(src_dir.iterdir()):
                src_dir.rmdir()
    return counts


def _rollback_mutations(
    *,
    rewritten_notes: list[tuple[Path, str]],
    restorable_fulltexts: list[tuple[Path, bytes]],
    created_assets: list[Path],
    moved_pairs: list[tuple[Path, Path]],
    config_restorer=None,
) -> None:
    """Best-effort reverse rollback of all filesystem mutations recorded during migration."""
    if config_restorer is not None:
        with contextlib.suppress(Exception):
            config_restorer()
    for ft_path, raw_bytes in reversed(restorable_fulltexts):
        with contextlib.suppress(OSError):
            ft_path.parent.mkdir(parents=True, exist_ok=True)
            ft_path.write_bytes(raw_bytes)
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


def rollback_incomplete_migration(vault: Path) -> dict[str, Any]:
    """Roll back an interrupted ``in_progress`` migration using ``.migration-journal.json``."""
    import json

    vault_root = Path(vault).expanduser().resolve()
    journal_path = vault_root / ".paperforge" / ".migration-journal.json"
    if not journal_path.is_file():
        return {"recovered": False, "state": "no_journal"}
    data = json.loads(journal_path.read_text(encoding="utf-8"))
    if data.get("state") != "in_progress":
        return {"recovered": False, "state": str(data.get("state") or "unknown")}

    moved_pairs = [
        (Path(item["src"]), Path(item["dst"]))
        for item in (data.get("moved_pairs") or [])
        if isinstance(item, dict) and item.get("src") and item.get("dst")
    ]
    rewritten_notes = [
        (Path(item["path"]), str(item["original_text"]))
        for item in (data.get("rewritten_notes") or [])
        if isinstance(item, dict) and item.get("path") and "original_text" in item
    ]
    created_assets = [Path(p) for p in (data.get("created_assets") or [])]

    prev_sys = data.get("previous_system_dir")

    def _restore_cfg() -> None:
        if prev_sys and (vault_root / "paperforge.json").is_file():
            set_config(vault_root, "system_dir", str(prev_sys))

    _rollback_mutations(
        rewritten_notes=rewritten_notes,
        restorable_fulltexts=[],
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


def migrate_vault_storage(vault: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Transactionally migrate an existing vault to `.paperforge/` with full-stage rollback."""
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

    target_pf = vault_root / ".paperforge"
    journal_path = target_pf / ".migration-journal.json"
    moved_pairs: list[tuple[Path, Path]] = []
    rewritten_notes: list[tuple[Path, str]] = []
    created_assets: list[Path] = []
    restorable_fulltexts: list[tuple[Path, bytes]] = []
    config_updated = False

    def _flush_journal() -> None:
        if dry_run:
            return
        write_json_atomic(
            journal_path,
            {
                "state": "in_progress",
                "source_engine_dir": str(old_pf),
                "target_engine_dir": str(target_pf),
                "previous_system_dir": previous_system_dir,
                "moved_pairs": [{"src": str(s), "dst": str(d)} for s, d in moved_pairs],
                "rewritten_notes": [
                    {"path": str(p), "original_text": txt} for p, txt in rewritten_notes
                ],
                "created_assets": [str(p) for p in created_assets],
            },
        )

    def _restore_config_if_needed() -> None:
        if config_updated and previous_system_dir and cfg_path.is_file():
            set_config(vault_root, "system_dir", previous_system_dir)

    _flush_journal()

    moved_zotero = False
    ocr_root = target_pf / "ocr" if not dry_run or not old_pf.exists() else old_pf / "ocr"
    assets_copied = 0
    notes_rewritten = 0
    workspace_copies_removed = 0
    workspace_copies_preserved = 0
    tree_counts = {"moved": 0, "skipped_existing": 0}

    try:
        tree_counts = _move_tree_entries(
            old_pf,
            target_pf,
            dry_run=dry_run,
            moved_pairs=moved_pairs,
            on_progress=_flush_journal,
        )

        old_zotero = old_sys / "Zotero"
        target_zotero = target_pf / "Zotero"
        if (
            old_zotero.exists()
            and not old_zotero.is_symlink()
            and old_zotero.resolve() != target_zotero.resolve()
            and not target_zotero.exists()
        ):
            moved_zotero = True
            if not dry_run:
                target_pf.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_zotero), str(target_zotero))
                moved_pairs.append((old_zotero, target_zotero))
                _flush_journal()

        if lit_root.exists():
            for domain_dir in sorted(lit_root.iterdir()):
                if not domain_dir.is_dir():
                    continue
                for ws_dir in sorted(domain_dir.iterdir()):
                    if not ws_dir.is_dir() or " - " not in ws_dir.name:
                        continue
                    key = ws_dir.name.split(" - ", 1)[0].strip()
                    if not key:
                        continue
                    paper_ocr_dir = ocr_root / key
                    if paper_ocr_dir.exists():
                        if dry_run:
                            assets_src = paper_ocr_dir / "assets"
                            if assets_src.exists():
                                for sub in ("figures", "tables"):
                                    if (assets_src / sub).exists():
                                        assets_copied += sum(1 for _ in (assets_src / sub).glob("*.jpg"))
                        else:
                            ws_assets_dir = ws_dir / "assets"
                            existing_before = (
                                {p.name for p in ws_assets_dir.iterdir()} if ws_assets_dir.is_dir() else set()
                            )
                            copied = sync_workspace_visual_assets(paper_ocr_dir, ws_dir, key)
                            assets_copied += len(copied)
                            for fname in copied:
                                if fname not in existing_before:
                                    created_assets.append(ws_assets_dir / fname)
                    seen_notes: set[Path] = set()
                    for candidate_note in (
                        ws_dir / f"{key}.md",
                        ws_dir / f"{ws_dir.name}.md",
                        domain_dir / f"{key}.md",
                    ):
                        if candidate_note.exists() and candidate_note.is_file():
                            resolved_note = candidate_note.resolve()
                            if resolved_note in seen_notes:
                                continue
                            seen_notes.add(resolved_note)
                            original = candidate_note.read_text(encoding="utf-8")
                            updated, count = rewrite_visual_embeds_for_key(original, key)
                            if count > 0:
                                notes_rewritten += 1
                                if not dry_run:
                                    rewritten_notes.append((candidate_note, original))
                                    _flush_journal()
                                    write_text_atomic(candidate_note, updated)
                    ocr_dir_for_verify = (
                        paper_ocr_dir
                        if paper_ocr_dir.exists()
                        else ((old_pf / "ocr" / key) if (old_pf / "ocr" / key).exists() else None)
                    )
                    ws_ft_path = ws_dir / "fulltext.md"
                    ft_snapshot = ws_ft_path.read_bytes() if (not dry_run and ws_ft_path.is_file()) else None
                    outcome = cleanup_or_preserve_workspace_fulltext(
                        ws_dir,
                        vault=vault_root,
                        ocr_paper_dir=ocr_dir_for_verify,
                        lit_root=lit_root,
                        paper_key=key,
                        dry_run=dry_run,
                    )
                    if ft_snapshot is not None and outcome in ("removed_verified_mirror", "preserved_to_trash"):
                        restorable_fulltexts.append((ws_ft_path, ft_snapshot))
                    if outcome in ("removed_verified_mirror", "preserved_to_trash"):
                        workspace_copies_removed += 1
                    if outcome == "preserved_to_trash":
                        workspace_copies_preserved += 1

        if not dry_run:
            if not cfg_path.exists():
                bootstrap_config(vault_root)
            set_config(vault_root, "system_dir", ".paperforge")
            config_updated = True

            for leftover in (old_pf, old_sys):
                with contextlib.suppress(OSError):
                    if (
                        leftover.exists()
                        and leftover.is_dir()
                        and leftover.resolve() != target_pf.resolve()
                        and not any(leftover.iterdir())
                    ):
                        leftover.rmdir()

            write_json_atomic(
                journal_path,
                {
                    "state": "completed",
                    "entries_moved": tree_counts["moved"],
                    "notes_rewritten": notes_rewritten,
                    "workspace_fulltexts_removed": workspace_copies_removed,
                    "workspace_fulltexts_preserved": workspace_copies_preserved,
                },
            )
    except Exception as exc:  # noqa: BLE001 — any mid-migration failure triggers atomic rollback
        if not dry_run:
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
        "target_engine_dir": ".paperforge",
        "entries_moved": tree_counts["moved"],
        "entries_skipped_existing": tree_counts["skipped_existing"],
        "moved_zotero_dir": moved_zotero,
        "visual_assets_materialized": assets_copied,
        "notes_rewritten": notes_rewritten,
        "workspace_fulltexts_removed": workspace_copies_removed,
        "workspace_fulltexts_preserved": workspace_copies_preserved,
        "config_updated": config_updated,
    }
