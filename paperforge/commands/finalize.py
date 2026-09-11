"""Mark a validated deep-reading note complete and refresh its index."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

_SKIP_NOTE_NAMES = {"fulltext.md", "deep-reading.md", "discussion.md"}


def _failure(args: argparse.Namespace, message: str) -> int:
    result = PFResult(
        ok=False,
        command="deep-finalize",
        version=__version__,
        error=PFError(code=ErrorCode.VALIDATION_ERROR, message=message),
    )
    if getattr(args, "json", False):
        print(result.to_json())
    else:
        print(f"[ERROR] {message}", file=sys.stderr)
    return 1


def _find_note(vault: Path, key: str) -> tuple[Path, str] | None:
    from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict
    from paperforge.worker._utils import pipeline_paths

    literature = pipeline_paths(vault)["literature"]
    if not literature.exists():
        return None
    for note_path in sorted(literature.rglob("*.md")):
        if note_path.name in _SKIP_NOTE_NAMES:
            continue
        try:
            with note_path.open(encoding="utf-8", newline="") as handle:
                text = handle.read()
            frontmatter = cast(dict[str, object], read_frontmatter_dict(text))
        except (OSError, UnicodeError, ValueError):
            continue
        if str(frontmatter.get("zotero_key", "")).strip() == key:
            return note_path, text
    return None


def run(args: argparse.Namespace) -> int:
    """Validate deep-reading content, mark it done, and refresh the index."""
    vault = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    key = str(getattr(args, "zotero_key", "") or "").strip()
    if not key:
        return _failure(args, "zotero_key is required")

    found = _find_note(vault, key)
    if found is None:
        return _failure(args, f"formal note not found for {key}")
    note_path, text = found

    from paperforge.adapters.obsidian_frontmatter import (
        has_deep_reading_content,
        read_frontmatter_dict,
        split_frontmatter_block,
        update_frontmatter_field,
    )

    if split_frontmatter_block(text) is None:
        return _failure(args, f"note has no valid frontmatter block: {note_path}")
    frontmatter = cast(dict[str, object], read_frontmatter_dict(text))
    if str(frontmatter.get("zotero_key", "")).strip() != key:
        return _failure(args, f"note key mismatch: {note_path}")
    if not has_deep_reading_content(text):
        return _failure(args, f"deep-reading content is incomplete: {note_path}")

    updated = update_frontmatter_field(text, "deep_reading_status", "done")
    note_updated = updated != text
    if note_updated:
        try:
            _ = note_path.write_text(updated, encoding="utf-8", newline="")
        except OSError as exc:
            return _failure(args, f"could not update note: {exc}")

    try:
        from paperforge.worker.asset_index import refresh_index_entry

        index_refreshed = refresh_index_entry(vault, key)
    except Exception as exc:  # noqa: BLE001 — note is already the authority
        index_refreshed = False
        index_error = str(exc)
    else:
        index_error = ""

    note_rel = str(note_path.relative_to(vault)).replace("\\", "/")
    data = {
        "zotero_key": key,
        "note_path": note_rel,
        "content_validated": True,
        "note_updated": note_updated,
        "index_refreshed": index_refreshed,
    }
    if index_error:
        data["index_error"] = index_error
    result = PFResult(
        ok=True,
        command="deep-finalize",
        version=__version__,
        data=data,
    )
    if getattr(args, "json", False):
        print(result.to_json())
    else:
        status = "updated" if note_updated else "already done"
        index = "refreshed" if index_refreshed else "refresh deferred"
        print(f"[OK] deep-finalize {key}: {status}, index {index}")
    return 0
