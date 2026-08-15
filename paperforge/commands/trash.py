"""`paperforge trash` — recoverable-deletion management.

Since the 2026-08-14 incident every PaperForge delete MOVES user data into
``.paperforge/trash/`` (with a manifest) instead of physically removing it.
This command lists, restores, and (explicitly, age-gated) purges the trash.
"""

from __future__ import annotations

import argparse
import sys

from paperforge.worker.trash import list_trash, purge_trash, restore_trash


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub = args.trash_subcommand

    if sub == "list":
        records = list_trash(vault)
        if not records:
            print("trash: empty")
            return 0
        for r in records:
            print(
                f"{r.get('trash_id')}  {r.get('operation','?')}  "
                f"{r.get('paper_key') or '-'}  {r.get('trashed_at','?')}  "
                f"{r.get('original_path','?')}"
            )
        return 0

    if sub == "restore":
        trash_id = getattr(args, "trash_id", None) or ""
        if not trash_id:
            print("usage: paperforge trash restore <trash-id>", file=sys.stderr)
            return 2
        try:
            original = restore_trash(vault, trash_id)
        except KeyError as exc:
            print(f"trash: {exc}", file=sys.stderr)
            return 2
        except (FileExistsError, FileNotFoundError) as exc:
            print(f"trash: restore failed: {exc}", file=sys.stderr)
            return 1
        print(f"restored -> {original}")
        return 0

    if sub == "purge":
        older_than = getattr(args, "older_than", None)
        purged = purge_trash(vault, older_than_days=older_than)
        print(f"trash: purged {purged} item(s)")
        return 0

    print(f"unknown trash subcommand: {sub}", file=sys.stderr)
    return 2
