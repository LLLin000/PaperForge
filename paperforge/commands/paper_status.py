from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.query import get_paper_status


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query

    try:
        status = get_paper_status(vault, query)
        if status is None:
            result = PFResult(
                ok=False,
                command="paper-status",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.PATH_NOT_FOUND,
                    message=f"No paper found for: {query}",
                ),
                next_actions=[
                    {
                        "command": "paperforge search",
                        "reason": "Search for papers by keyword",
                    }
                ],
            )
        else:
            result = PFResult(
                ok=True,
                command="paper-status",
                version=PF_VERSION,
                data=status,
            )
    except Exception as exc:
        result = PFResult(
            ok=False,
            command="paper-status",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
            ),
        )

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            data = result.data
            if data.get("resolved"):
                print(f"Zotero Key:   {data.get('zotero_key', '')}")
                print(f"Title:        {data.get('title', '')}")
                print(f"Year:         {data.get('year', '')}")
                print(f"Lifecycle:    {data.get('lifecycle', '')}")
                print(f"Next Step:    {data.get('next_step', '')}")
            if data.get("candidates"):
                print(f"\nMultiple candidates: {len(data['candidates'])}")
                for c in data["candidates"]:
                    print(f"  - {c['zotero_key']}: {c['title']} ({c['year']})")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)

    return 0 if result.ok else 1
