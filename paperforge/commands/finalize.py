"""deep-finalize — mark deep reading as done and signal dashboard to refresh."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paperforge import __version__
from paperforge.core.result import PFResult


def _update_frontmatter(text: str, key: str, value: str) -> str:
    """Replace or insert a frontmatter field value."""
    pattern = re.compile(rf"^({re.escape(key)}:\s*)(.*?)$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(rf"\g<1>{value}", text)
    # Insert after the first '---' separator
    fm_end = text.find("---\n", 3)
    if fm_end != -1:
        return text[:fm_end] + f"{key}: {value}\n" + text[fm_end:]
    return text


def run(args: argparse.Namespace) -> int:
    """Mark deep reading as done and refresh the canonical index.

    Called by the AI agent at the end of /pf-deep to signal completion.
    The dashboard watches formal-library.json and will refresh on change.
    """
    vault: Path = getattr(args, "vault_path", None)
    if vault is None:
        from paperforge.config import resolve_vault

        vault = resolve_vault(cli_vault=getattr(args, "vault", None))

    zotero_key: str | None = getattr(args, "zotero_key", None)
    if not zotero_key:
        print("[ERROR] zotero_key is required", file=sys.stderr)
        if getattr(args, "json", False):
            pf = PFResult(ok=False, command="deep-finalize", version=__version__, error="zotero_key is required")
            print(pf.to_json())
        return 1

    # 1. Find and update the formal note frontmatter
    from paperforge.worker._utils import pipeline_paths

    paths = pipeline_paths(vault)
    lit_root = paths["literature"]
    note_updated = False

    if lit_root.exists():
        for note_file in lit_root.rglob("*.md"):
            if note_file.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
                continue
            try:
                text = note_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if re.search(rf'^\s*zotero_key:\s*"{re.escape(zotero_key)}"', text, re.MULTILINE):
                new_text = _update_frontmatter(text, "deep_reading_status", "done")
                note_file.write_text(new_text, encoding="utf-8")
                note_updated = True
                break

    # 2. Refresh the canonical index entry (writes formal-library.json)
    from paperforge.worker.asset_index import refresh_index_entry

    index_ok = refresh_index_entry(vault, zotero_key)

    msg_parts = []
    if note_updated:
        msg_parts.append("frontmatter updated")
    else:
        msg_parts.append("frontmatter not found (index-only refresh)")
    msg_parts.append("index refreshed" if index_ok else "full index rebuild triggered")

    message = f"[OK] deep-finalize {zotero_key}: " + ", ".join(msg_parts)
    print(message)

    if getattr(args, "json", False):
        pf = PFResult(
            ok=True,
            command="deep-finalize",
            version=__version__,
            data={
                "zotero_key": zotero_key,
                "note_updated": note_updated,
                "index_refreshed": index_ok,
            },
        )
        print(pf.to_json())

    return 0
