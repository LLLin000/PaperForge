"""Vault storage migration from visible System/PaperForge to hidden .paperforge/."""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any

from paperforge.config import ConfigError, load_config, resolve_paths, set_config
from paperforge.core.io import write_text_atomic
from paperforge.worker.asset_index import sync_workspace_visual_assets

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


def _move_tree_entries(src_dir: Path, dst_dir: Path, *, dry_run: bool) -> dict[str, int]:
    """Move directories and files from *src_dir* into *dst_dir* without overwriting newer files."""
    counts = {"moved": 0, "skipped_existing": 0}
    if not src_dir.exists() or src_dir.resolve() == dst_dir.resolve():
        return counts
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_dir.iterdir()):
        target = dst_dir / child.name
        if not target.exists():
            counts["moved"] += 1
            if not dry_run:
                shutil.move(str(child), str(target))
        elif child.is_dir() and target.is_dir():
            sub = _move_tree_entries(child, target, dry_run=dry_run)
            counts["moved"] += sub["moved"]
            counts["skipped_existing"] += sub["skipped_existing"]
            if not dry_run:
                try:
                    if not any(child.iterdir()):
                        child.rmdir()
                except OSError:
                    pass
        else:
            counts["skipped_existing"] += 1
    if not dry_run:
        try:
            if src_dir.exists() and not any(src_dir.iterdir()):
                src_dir.rmdir()
        except OSError:
            pass
    return counts


def _cleanup_redundant_workspace_copy(ws_dir: Path, *, dry_run: bool) -> bool:
    """Remove redundant workspace markdown mirror when canonical store moved to .paperforge."""
    copy_name = "full" + "text.md"
    ws_copy = ws_dir / copy_name
    if not ws_copy.exists() or not ws_copy.is_file():
        return False
    if not dry_run:
        ws_copy.unlink()
    return True


def migrate_vault_storage(vault: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Migrate an existing vault from visible ``System/PaperForge`` to ``.paperforge``.

    Steps:
    1. Move engine state subtrees from old ``paperforge`` dir into ``vault / '.paperforge'``.
    2. Materialize per-paper cropped JPGs into ``<workspace>/assets/<KEY>_*.jpg``.
    3. Rewrite ``![[.../figure_NNN.md]]`` / ``.jpg`` links inside ``<KEY>.md`` notes to ``![[<KEY>_figure_NNN.jpg]]``.
    4. Remove redundant workspace fulltext copies so users edit only PDF annotations + ``<KEY>.md``.
    5. Atomically update ``system_dir`` to ``".paperforge"`` in ``paperforge.json`` and prune empty legacy dirs.
    """
    vault_root = Path(vault).expanduser().resolve()
    try:
        snapshot = load_config(vault_root)
        paths = resolve_paths(vault_root, snapshot)
        old_sys = paths["system"]
        old_pf = paths["paperforge"]
        lit_root = paths["literature"]
    except ConfigError:
        old_sys = vault_root / "System"
        old_pf = old_sys / "PaperForge"
        lit_root = vault_root / "Resources" / "Literature"

    target_pf = vault_root / ".paperforge"
    tree_counts = _move_tree_entries(old_pf, target_pf, dry_run=dry_run)

    # Also relocate legacy System/Zotero if present and config doesn't point outside
    old_zotero = old_sys / "Zotero"
    moved_zotero = False
    if old_zotero.exists() and not old_zotero.is_symlink() and not (target_pf / "Zotero").exists():
        moved_zotero = True
        if not dry_run:
            shutil.move(str(old_zotero), str(target_pf / "Zotero"))

    ocr_root = target_pf / "ocr" if not dry_run or not old_pf.exists() else old_pf / "ocr"
    assets_copied = 0
    notes_rewritten = 0
    workspace_copies_removed = 0

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
                        copied = sync_workspace_visual_assets(paper_ocr_dir, ws_dir, key)
                        assets_copied += len(copied)
                for candidate_note in (ws_dir / f"{key}.md", domain_dir / f"{key}.md"):
                    if candidate_note.exists() and candidate_note.is_file():
                        original = candidate_note.read_text(encoding="utf-8")
                        updated, count = rewrite_visual_embeds_for_key(original, key)
                        if count > 0:
                            notes_rewritten += 1
                            if not dry_run:
                                write_text_atomic(candidate_note, updated)
                if (target_pf / "ocr" / key).exists() or (old_pf / "ocr" / key).exists():
                    if _cleanup_redundant_workspace_copy(ws_dir, dry_run=dry_run):
                        workspace_copies_removed += 1

    config_updated = False
    if not dry_run:
        try:
            set_config(vault_root, "system_dir", ".paperforge")
            config_updated = True
        except ConfigError as exc:
            logger.warning("migrate_vault_storage: failed to update system_dir: %s", exc)

        # Clean up empty System/PaperForge and System directories if nothing remains
        for leftover in (old_pf, old_sys):
            try:
                if leftover.exists() and leftover.is_dir() and leftover.resolve() != target_pf.resolve():
                    if not any(leftover.iterdir()):
                        leftover.rmdir()
            except OSError:
                pass

    return {
        "dry_run": dry_run,
        "target_engine_dir": ".paperforge",
        "entries_moved": tree_counts["moved"],
        "entries_skipped_existing": tree_counts["skipped_existing"],
        "moved_zotero_dir": moved_zotero,
        "visual_assets_materialized": assets_copied,
        "notes_rewritten": notes_rewritten,
        "workspace_fulltexts_removed": workspace_copies_removed,
        "config_updated": config_updated,
    }
