from __future__ import annotations

import argparse
import sys

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.context import get_agent_context
from paperforge import __version__ as PF_VERSION

COMMANDS = {
    "paper-status": {
        "usage": "paperforge paper-status <zotero_key|citation_key|doi|title> --json",
        "purpose": "Look up one paper's full status and recommended next action",
    },
    "search": {
        "usage": "paperforge search <query> --json [--collection NAME] [--domain NAME] [--ocr done|pending] [--year-from N] [--year-to N] [--limit N]",
        "purpose": "Full-text search with optional collection/domain/lifecycle filters",
    },
    "retrieve": {
        "usage": "paperforge retrieve <query> --json [--limit N]",
        "purpose": "Search OCR fulltext chunks for evidence paragraphs (coming soon)",
    },
    "deep": {
        "usage": "/pf-deep <zotero_key>",
        "purpose": "Full three-pass deep reading with chart analysis",
    },
    "ocr": {
        "usage": "/pf-ocr",
        "purpose": "Run OCR on papers marked do_ocr:true",
    },
    "sync": {
        "usage": "/pf-sync",
        "purpose": "Sync Zotero and regenerate formal notes + index",
    },
}

RULES = [
    "Use paperforge.db via CLI commands before reading individual files.",
    "Do not infer paper state from stale frontmatter when memory status is fresh.",
    "Read source files only after resolving candidates via paper-status or search.",
    "To locate a paper: start with collection scope if known, then expand to full library search.",
]


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

    context = get_agent_context(vault)
    if context is None:
        result = PFResult(
            ok=False,
            command="agent-context",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message="Memory database not found or query failed. Run paperforge memory build.",
            ),
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    data = {
        "paperforge": {
            "version": PF_VERSION,
            "vault": str(vault),
            "memory_db": "ready",
        },
        "library": context["library"],
        "collections": context["collections"],
        "commands": COMMANDS,
        "rules": RULES,
    }

    result = PFResult(
        ok=True,
        command="agent-context",
        version=PF_VERSION,
        data=data,
    )

    if args.json:
        print(result.to_json())
    else:
        lib = data["library"]
        print(f"Papers: {lib['paper_count']} total")
        print(f"Domains: {lib['domain_counts']}")
        print(f"Lifecycle: {lib['lifecycle_counts']}")
        for c in data.get("collections", []):
            subs = f" ({len(c['sub'])} sub)" if c["sub"] else ""
            print(f"  [{c['count']:3}] {c['name']}{subs}")

    return 0 if result.ok else 1
