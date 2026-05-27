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
        warnings: list[str] = []
        next_actions: list[dict] = []
        if len(results) == 0:
            plan = enrich_query_plan_with_runtime(build_query_plan(query, "discover"), vault)
            data["query_diagnostic"] = {
                "query_class": plan["query_class"],
                "recommended_primary": plan["recommended_primary"],
                "query_writing_rules": plan["query_writing_rules"],
                "scope_assessment": plan.get("scope_assessment"),
            }
            if plan["query_class"] in {"mixed_query", "author_year"}:
                warnings.append("Zero results may reflect a noncanonical metadata query rather than library absence.")
            next_actions.append(
                {
                    "command": "paperforge query-plan",
                    "reason": "Normalize the query and choose the correct first retrieval command.",
                }
            )
            if plan["recommended_primary"]["command"] != "search":
                next_actions.append(
                    {
                        "command": f"paperforge {plan['recommended_primary']['command']}",
                        "reason": "The planning layer recommends a different first command for this query.",
                    }
                )
        result = PFResult(ok=True, command="search", version=PF_VERSION, data=data, warnings=warnings, next_actions=next_actions)
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
