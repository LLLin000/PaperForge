from __future__ import annotations

import argparse
import sys
import json

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.vector_db import retrieve_chunks
from paperforge import __version__ as PF_VERSION


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query
    limit = args.limit or 5

    try:
        chunks = retrieve_chunks(vault, query, limit=limit, expand=args.expand)
    except Exception as e:
        result = PFResult(ok=False, command="retrieve", version=PF_VERSION,
                         error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)))
        print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
        return 1

    # Enrich with paper metadata from memory DB
    if chunks:
        db_path = get_memory_db_path(vault)
        if db_path.exists():
            conn = get_connection(db_path, read_only=True)
            try:
                for c in chunks:
                    row = conn.execute(
                        "SELECT citation_key, title, year, first_author FROM papers WHERE zotero_key=?",
                        (c["paper_id"],)
                    ).fetchone()
                    if row:
                        c["citation_key"] = row["citation_key"]
                        c["title"] = row["title"]
                        c["year"] = row["year"]
                        c["first_author"] = row["first_author"]
            finally:
                conn.close()

    data = {"query": query, "chunks": chunks, "count": len(chunks)}
    result = PFResult(ok=True, command="retrieve", version=PF_VERSION, data=data)

    if args.json:
        print(result.to_json())
    else:
        print(f"{len(chunks)} chunks for: {query}")
        for c in chunks:
            print(f"  [{c.get('section','')}] {c.get('citation_key','')} p{c.get('page_number',0)}: {c['chunk_text'][:80]}...")
    return 0
