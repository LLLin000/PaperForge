from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.chunker import chunk_fulltext
from paperforge.memory.vector_db import (
    delete_paper_vectors,
    embed_paper,
    get_embed_status,
    get_vector_db_path,
)
from paperforge.worker.asset_index import read_index
from paperforge import __version__ as PF_VERSION


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub = getattr(args, "embed_subcommand", "build")

    if sub == "status":
        status = get_embed_status(vault)
        result = PFResult(ok=True, command="embed status", version=PF_VERSION, data=status)
        if args.json:
            print(result.to_json())
        else:
            for k, v in status.items():
                print(f"  {k}: {v}")
        return 0

    # Build
    envelope = read_index(vault)
    if not envelope:
        result = PFResult(ok=False, command="embed build", version=PF_VERSION,
                         error=PFError(code=ErrorCode.PATH_NOT_FOUND,
                                       message="Canonical index not found. Run paperforge sync first."))
        print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
        return 1

    items = envelope if isinstance(envelope, list) else envelope.get("items", [])
    done_papers = [e for e in items if e.get("ocr_status") == "done"]

    if args.force:
        db_path = get_vector_db_path(vault)
        if db_path.exists():
            import shutil
            shutil.rmtree(str(db_path), ignore_errors=True)

    papers_embedded = 0
    chunks_embedded = 0
    for entry in done_papers:
        key = entry.get("zotero_key")
        fulltext_rel = entry.get("fulltext_path", "")
        if not fulltext_rel:
            continue
        fulltext_path = vault / fulltext_rel
        chunks = chunk_fulltext(fulltext_path)
        if not chunks:
            continue
        try:
            delete_paper_vectors(vault, key)
            n = embed_paper(vault, key, chunks)
            chunks_embedded += n
            papers_embedded += 1
        except Exception as e:
            result = PFResult(ok=False, command="embed build", version=PF_VERSION,
                             error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)))
            print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
            return 1

    data = {
        "papers_embedded": papers_embedded,
        "chunks_embedded": chunks_embedded,
        "model": get_embed_status(vault)["model"],
        "mode": get_embed_status(vault)["mode"],
    }
    result = PFResult(ok=True, command="embed build", version=PF_VERSION, data=data)
    if args.json:
        print(result.to_json())
    else:
        print(f"Embedded {papers_embedded} papers ({chunks_embedded} chunks)")
    return 0
