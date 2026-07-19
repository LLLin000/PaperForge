from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.context import get_agent_context

COMMANDS = {
    "query-plan": {
        "usage": "paperforge query-plan <query> --intent discover|content|known-paper --json",
        "purpose": "Classify the query, choose the best first retrieval command, and explain fallback rules",
    },
    "paper-status": {
        "usage": "paperforge paper-status <zotero_key|citation_key|doi|title> --json",
        "purpose": "Look up one paper's full status and recommended next action",
    },
    "search": {
        "usage": "paperforge search <query> --json [--domain NAME] [--ocr done|pending|failed|processing] [--year-from N] [--year-to N] [--limit N] [--lifecycle indexed|pdf_ready|fulltext_ready|deep_read_done]",
        "purpose": "Metadata FTS search over title, abstract, authors, journal, domain, and collection fields",
    },
    "retrieve": {
        "usage": "paperforge retrieve <query> --json [--limit N]",
        "purpose": "Semantic content retrieval across OCR fulltext — use this first when the user wants something inside papers",
    },
    "context": {
        "usage": "paperforge context <key> | --domain D | --collection P | --all",
        "purpose": "List all papers in a collection/domain (no truncation) or get single paper context pack",
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
    "Use paperforge CLI commands before reading individual files — never grep/glob the vault directly.",
    "Do not infer paper state from stale frontmatter when memory status is fresh.",
    "Read source files only after resolving candidates via paper-status, search, retrieve, or context.",
    "To locate a paper: start with collection scope if known, then expand to full library search.",
    "Paper discovery must use multi-arm strategy: retrieve (body text) + search (metadata) + context --collection (inventory). Never rely on a single search tool.",
    "Use query-plan before freeform retrieval when the query mixes author/year/title/content signals.",
    "For known-paper lookup, DOI/zotero_key/citation_key are higher-signal than title words; author+year first-pass search should exclude title terms.",
    "For content lookup, start with retrieve. Search is not semantic fulltext discovery.",
    "When a search returns > 20 results, present the count to the user and offer to narrow — never silently skip large result sets.",
    "A raw zero-result search does not prove library absence when the query is noncanonical for metadata search.",
    "Check embed status --json (db_exists + chunk_count) before calling retrieve; skip retrieve if vector index is unavailable.",
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
