"""Prune command — standalone orphan paper cleanup."""
from __future__ import annotations

import argparse
import logging

from paperforge import __version__
from paperforge.core.result import PFResult
from paperforge.worker.asset_index import read_index

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    dry_run = not getattr(args, "force", False)
    json_output = getattr(args, "json", False)

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

    result_data = prune_orphan_papers(vault, fresh_index=fresh_index, dry_run=dry_run)

    if json_output:
        result = PFResult(
            ok=True, command="prune", version=__version__, data={"dry_run": dry_run, **result_data},
        )
        print(result.to_json())
        return 0

    preview = result_data.get("preview", [])
    if not preview:
        print("[OK] No orphan papers found.")
        return 0

    print(f"[PRUNE] Found {len(preview)} orphan paper(s):")
    for p in preview:
        extras = []
        if p.get("ocr_dir"):
            extras.append("OCR")
        print(f"  {p['key']} ({p['domain']}) — workspace + {' + '.join(extras)}")

    if dry_run:
        print(f"\n--- Dry run (pass --force to actually delete) ---")
    else:
        counts = result_data.get("counts", {})
        print(f"\n[PRUNE] Deleted {len(result_data.get('deleted', []))} paper(s)")
        print(f"  workspaces: {counts.get('workspace', 0)}")
        print(f"  OCR dirs:   {counts.get('ocr', 0)}")
        print(f"  vectors:    {counts.get('vectors', 0)}")
        if counts.get("failed", 0):
            print(f"  failed:     {counts['failed']}")
        print(f"\n  To restore: paperforge sync  (re-adds entry to index)")
        print(f"  To recover: paperforge ocr run  (re-OCR)")
        print(f"  To rebuild: paperforge embed build --resume  (re-embed)")

    return 0
