"""Prune command — standalone orphan paper cleanup."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from paperforge import __version__
from paperforge.core.result import PFResult
from paperforge.worker.asset_index import read_index

logger = logging.getLogger(__name__)


def _interactive_select(preview: list[dict]) -> set[int]:
    selected = set(range(len(preview)))

    while True:
        for i, p in enumerate(preview):
            marker = "[x]" if i in selected else "[ ]"
            extras = []
            if p.get("ocr_dir"):
                extras.append("OCR")
            print(f"  {i+1:2d}. {marker} {p['key']} ({p['domain']}) — workspace + {' + '.join(extras)}")

        print()
        cmd = input("Commands: [1-N] toggle  [a] select all  [n] none  [d] delete selected > ").strip().lower()

        if cmd == "d":
            if not selected:
                print("Nothing selected. Aborting.\n")
                continue
            confirm = input(f"Delete {len(selected)} paper(s)? (y/N): ").strip().lower()
            if confirm == "y":
                return selected
            print("Cancelled.\n")
            continue
        elif cmd == "a":
            selected = set(range(len(preview)))
        elif cmd == "n":
            selected = set()
        else:
            parts = cmd.replace(",", " ").split()
            for p in parts:
                try:
                    idx = int(p) - 1
                    if 0 <= idx < len(preview):
                        if idx in selected:
                            selected.remove(idx)
                        else:
                            selected.add(idx)
                except ValueError:
                    pass


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    force = getattr(args, "force", False)
    json_output = getattr(args, "json", False)
    keys_filter = getattr(args, "keys", None) or []

    try:
        fresh_index = read_index(vault)
    except Exception as e:
        logger.error("prune: failed to read canonical index: %s", e)
        if json_output:
            result = PFResult(
                ok=False, command="prune", version=__version__,
                data={"error": f"cannot read index: {e}"},
            )
            print(result.to_json())
        else:
            print(f"[FAIL] Cannot read canonical index: {e}")
        return 1

    from paperforge.worker.prune import prune_orphan_papers

    result_data = prune_orphan_papers(vault, fresh_index=fresh_index, dry_run=True)

    preview = result_data.get("preview", [])
    if keys_filter:
        keys_set = set(keys_filter)
        preview = [p for p in preview if p["key"] in keys_set]

    if not preview:
        if json_output:
            result = PFResult(ok=True, command="prune", version=__version__, data={"preview": [], "deleted": [], "counts": {}})
            print(result.to_json())
        else:
            msg = "[OK] No orphan papers found." if not keys_filter else "[OK] No matching orphan papers found."
            print(msg)
        return 0

    if json_output and force:
        candidates = [
            {
                "key": p["key"],
                "domain": p["domain"],
                "workspace_dir": Path(p["workspace"]),
                "ocr_dir": Path(p["ocr_dir"]) if p.get("ocr_dir") else None,
            }
            for p in preview
        ]
        result_data = prune_orphan_papers(vault, fresh_index=fresh_index, dry_run=False, _candidates=candidates)
        result = PFResult(ok=True, command="prune", version=__version__, data=result_data)
        print(result.to_json())
        return 0

    if json_output:
        data_out = dict(result_data)
        data_out["dry_run"] = not force
        data_out["preview"] = preview
        result = PFResult(
            ok=True, command="prune", version=__version__, data=data_out,
        )
        print(result.to_json())
        return 0

    print(f"[PRUNE] Found {len(preview)} orphan paper(s):")
    for p in preview:
        extras = []
        if p.get("ocr_dir"):
            extras.append("OCR")
        print(f"  {p['key']} ({p['domain']}) — workspace + {' + '.join(extras)}")

    if not force:
        print("\n--- Dry run (pass --force to enter interactive selection) ---")
        return 0

    print("\nSelect papers to delete:")
    selected_indices = _interactive_select(preview)

    candidates = [
        {
            "key": preview[i]["key"],
            "domain": preview[i]["domain"],
            "workspace_dir": Path(preview[i]["workspace"]),
            "ocr_dir": Path(preview[i]["ocr_dir"]) if preview[i].get("ocr_dir") else None,
        }
        for i in selected_indices
    ]

    result_data = prune_orphan_papers(vault, fresh_index=fresh_index, dry_run=False, _candidates=candidates)

    counts = result_data.get("counts", {})
    print(f"\n[PRUNE] Deleted {len(result_data.get('deleted', []))} paper(s)")
    print(f"  workspaces: {counts.get('workspace', 0)}")
    print(f"  OCR dirs:   {counts.get('ocr', 0)}")
    print(f"  vectors:    {counts.get('vectors', 0)}")
    if counts.get("failed", 0):
        print(f"  failed:     {counts['failed']}")
    print("\n  To restore: paperforge sync  (re-adds entry to index)")
    print("  To recover: paperforge ocr run  (re-OCR)")
    print("  To rebuild: paperforge embed build --resume  (re-embed)")

    return 0
