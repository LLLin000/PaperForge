from __future__ import annotations

import argparse
import json

from paperforge import __version__ as PF_VERSION
from paperforge.core.result import PFResult
from paperforge.core.io import read_json
from paperforge.retrieval.structure_tree import summarize_role_index


def _resolve_paper_root(vault_path, query: str):
    """Resolve a paper query to its OCR root directory."""
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.memory.query import lookup_paper
    from paperforge.worker._utils import pipeline_paths

    db_path = get_memory_db_path(vault_path)
    if not db_path or not db_path.exists():
        return None
    conn = get_connection(db_path, read_only=True)
    try:
        entries = lookup_paper(conn, query)
        if entries:
            ocr_root = pipeline_paths(vault_path)["ocr"]
            return ocr_root / entries[0]["zotero_key"]
    finally:
        conn.close()
    return None


def run(args: argparse.Namespace) -> int:
    paper_root = _resolve_paper_root(args.vault_path, args.query)
    if paper_root is None:
        data = {"mode": "not_found", "paper_id": args.query, "error": "Paper not found in vault"}
        if args.json:
            print(PFResult(ok=False, command="paper-navigation", version=PF_VERSION, data=data).to_json())
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1

    tree_path = paper_root / "index" / "structure-tree.json"
    if tree_path.exists():
        tree = read_json(tree_path)
        payload = {"mode": "structure_tree", "paper_id": tree.get("paper_id", ""), "nodes": tree.get("nodes", [])}
    else:
        role_index_path = paper_root / "index" / "role-index.json"
        if role_index_path.exists():
            role_index = read_json(role_index_path)
            summary = summarize_role_index(role_index)
            payload = {"mode": "role_index_summary", "paper_id": args.query, "summary": summary}
        else:
            payload = {"mode": "no_index", "paper_id": args.query}

    result = PFResult(ok=True, command="paper-navigation", version=PF_VERSION, data=payload)
    if args.json:
        print(result.to_json())
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
