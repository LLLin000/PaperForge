from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.fts import search_papers
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime


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

    from paperforge.memory.db import open_live_reader
    reader = open_live_reader(vault, db_path)
    conn = reader.__enter__()
    try:
        results = search_papers(
            conn,
            query,
            limit=args.limit,
            domain=args.domain or "",
            year_from=args.year_from or 0,
            year_to=args.year_to or 0,
            ocr_status=args.ocr or "",
            deep_status=args.deep or "",
            lifecycle=args.lifecycle or "",
            next_step=args.next_step or "",
        )
        # Normalize to unified PFResult match format
        unified: list[dict] = []
        for r in results:
            body_count = r.get("body_units_count", 0) or 0
            unified.append({
                "zotero_key": r.get("zotero_key", ""),
                "title": r.get("title", ""),
                "first_author": r.get("first_author", ""),
                "year": r.get("year", ""),
                "journal": r.get("journal", ""),
                "domain": r.get("domain", ""),
                "abstract": r.get("abstract", ""),
                "score": r.get("rank", 0),
                "text": r.get("abstract", ""),
                "heading": "",
                "source": "fts",
                "fulltext_available": body_count > 0,
                "body_units_count": body_count,
                "ocr_status": r.get("ocr_status", ""),
            })
        results = unified
        data: dict
        if getattr(args, "evidence", False):
            data = {
                "query": query,
                "evidence_status": "metadata_only",
                "fulltext_verified": False,
                "metadata_candidates": results,
                "count": len(results),
            }
        else:
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
                "route_explanation": {
                    "primary_arm": "paper_fts",
                    "compatibility_mode": False,
                },
            }
        warnings: list[str] = []
        next_actions: list[dict] = []
        if len(results) == 0:
            plan = enrich_query_plan_with_runtime(build_query_plan(query, "discover"), vault)
            if not getattr(args, "evidence", False):
                data["query_diagnostic"] = {
                    "recommended_primary": plan.get("primary"),
                    "recommended_fallback": plan.get("fallback"),
                }
            if plan.get("primary", {}).get("command") != "search":
                # T9 (#170): diagnostic, never a command-string action wire.
                data["query_diagnostic"]["recommended_command_id"] = (
                    plan.get("primary", {}).get("command")
                )
        result = PFResult(
            ok=True, command="search", version=PF_VERSION, data=data, warnings=warnings
        )
    except Exception as exc:
        result = PFResult(
            ok=False,
            command="search",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
    finally:
        conn.close()
        reader.__exit__(None, None, None)

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            if getattr(args, "evidence", False):
                candidates = result.data.get("metadata_candidates", [])
                print(f"Evidence mode — {len(candidates)} metadata candidates for: {query}")
                for m in candidates:
                    ft = "✓" if m.get("fulltext_available") else "✗"
                    print(f"  [{ft}] {m['zotero_key']} | {m['year']} | {m['first_author']} | {m['title'][:60]}")
            else:
                matches = result.data.get("matches", [])
                print(f"Found {len(matches)} results for: {query}")
                for m in matches:
                    print(f"  {m['zotero_key']} | {m['year']} | {m['first_author']} | {m['title'][:60]}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
    return 0 if result.ok else 1
