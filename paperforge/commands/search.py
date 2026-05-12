from __future__ import annotations

import argparse
import sys

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.fts import search_papers
from paperforge import __version__ as PF_VERSION


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        result = PFResult(
            ok=False,
            command="search",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message="Memory database not found. Run paperforge memory build.",
            ),
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    conn = get_connection(db_path, read_only=True)
    try:
        results = search_papers(
            conn, query,
            limit=args.limit,
            domain=args.domain or "",
            year_from=args.year_from or 0,
            year_to=args.year_to or 0,
            ocr_status=args.ocr or "",
            deep_status=args.deep or "",
            lifecycle=args.lifecycle or "",
            next_step=args.next_step or "",
        )
        data = {
            "query": query,
            "matches": results,
            "count": len(results),
            "filters_applied": {
                "domain": args.domain,
                "year_from": args.year_from,
                "year_to": args.year_to,
                "ocr": args.ocr,
                "deep": args.deep,
                "lifecycle": args.lifecycle,
                "next_step": args.next_step,
            },
        }
        result = PFResult(ok=True, command="search", version=PF_VERSION, data=data)
    except Exception as exc:
        result = PFResult(
            ok=False, command="search", version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
    finally:
        conn.close()

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            matches = result.data["matches"]
            print(f"Found {len(matches)} results for: {query}")
            for m in matches:
                rank_val = m.get("rank", "")
                print(f"  [{m['lifecycle']:16}] {m['zotero_key']} | {m['year']} | {m['first_author']} | {m['title'][:60]}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
    return 0 if result.ok else 1
