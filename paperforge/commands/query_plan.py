from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime


def run(args: argparse.Namespace) -> int:
    try:
        data = build_query_plan(args.query, args.intent)
        data = enrich_query_plan_with_runtime(data, args.vault_path)
        result = PFResult(ok=True, command="query-plan", version=PF_VERSION, data=data)
    except Exception as exc:
        result = PFResult(
            ok=False,
            command="query-plan",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            primary = result.data["recommended_primary"]
            print(f"Intent: {result.data['intent']}")
            print(f"Query class: {result.data['query_class']}")
            print(f"Primary: {primary['command']}")
            print(f"Args: {primary['args']}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)

    return 0 if result.ok else 1
