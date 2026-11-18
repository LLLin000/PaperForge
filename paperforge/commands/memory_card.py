"""CLI command `paperforge memory-card` — Living Paper Memory & Base table snapshots."""
from __future__ import annotations

import argparse
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult


def run(args: argparse.Namespace) -> int:
    vault = Path(args.vault_path)
    verb = str(getattr(args, "mc_verb", "") or "")
    json_output = bool(getattr(args, "json", False))

    from paperforge.services.memory_card_service import (
        clear_memory_facet,
        get_base_table_snapshot,
        get_memory_card,
        get_memory_history,
        refine_memory_facet,
    )

    try:
        if verb == "base-snapshot":
            data = get_base_table_snapshot(vault)
        else:
            paper_key = str(getattr(args, "key", "") or "").strip()
            if verb == "get":
                data = get_memory_card(vault, paper_key)
            elif verb == "refine":
                data = refine_memory_facet(
                    vault,
                    paper_key,
                    facet=str(getattr(args, "facet", "") or ""),
                    content=str(getattr(args, "content", "") or ""),
                )
            elif verb == "history":
                data = get_memory_history(
                    vault,
                    paper_key,
                    facet=str(getattr(args, "facet", "") or ""),
                )
            elif verb == "clear":
                data = clear_memory_facet(
                    vault,
                    paper_key,
                    facet=str(getattr(args, "facet", "") or ""),
                )
            else:
                raise ValueError(f"Unknown memory-card verb: {verb!r}")

        res = PFResult(ok=True, command="memory-card", version=__version__, data=data)
        if json_output:
            print(res.to_json())
        else:
            if verb == "base-snapshot":
                print(f"seq={data.get('seq', 0)} rows={len(data.get('rows', {}))}")
            elif verb == "history":
                print(f"{data['paper_id']}: {len(data['history'])} history revisions")
            elif verb == "clear":
                print(f"{data['paper_id']}: removed {data['removed']} facet(s)")
            else:
                card = data.get("card", data)
                print(f"{card['paper_id']}: {card['facet_count']} facets")
                for f in card.get("facets", []):
                    print(f"  [{f['label']} r{f['revision']}] {f['content']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        res = PFResult(
            ok=False,
            command="memory-card",
            version=__version__,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
        )
        print(res.to_json() if json_output else f"memory-card {verb} failed: {exc}")
        return 1
