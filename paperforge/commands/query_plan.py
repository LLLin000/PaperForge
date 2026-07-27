from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime


def run(args: argparse.Namespace) -> int:
    intent = args.intent
    if intent == "known-paper":
        intent = "locate"
    try:
        data = build_query_plan(args.query, intent)
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
            d = result.data
            print(f"Intent: {d['intent']}")
            print(f"Scope: {d.get('scope', 'library')}")
            if d.get('paper_key'):
                print(f"Paper: {d['paper_key']}")
            p = d.get('primary', {})
            print(f"Primary: {p.get('command', '?')} {p.get('args', {})}")
            fb = d.get('fallback')
            if fb:
                print(f"Fallback: {fb.get('command', '?')} (triggers: {fb.get('triggers', [])})")
            rt = d.get('runtime', {})
            print(f"Retrieve available: {rt.get('retrieve_available', False)}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)

    return 0 if result.ok else 1
