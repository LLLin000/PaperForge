from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from pathlib import Path
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.embedding import hybrid_search, merge_retrieve



def _looks_generic_chunk(text: str) -> bool:
    compact = (text or "").strip().lower()
    if not compact:
        return True
    if compact in {
        "[figure]",
        "none.",
        "or",
        "### keywords",
        "### abbreviations",
        "### reference",
        "### conclusion",
        "### references",
    }:
        return True
    if len(compact) <= 12:
        return True
    return False


def _is_low_confidence_semantic_result(chunks: list[dict]) -> bool:
    if not chunks:
        return False
    generic_top = sum(1 for chunk in chunks[:5] if _looks_generic_chunk(chunk.get("text", chunk.get("chunk_text", ""))))
    max_score = max(float(chunk.get("score", 0) or 0) for chunk in chunks[:5])
    return generic_top >= 3 or max_score < 0.62

def _paper_scope_check(vault, paper_key: str, allow_bm25_only: bool = False) -> dict | None:
    """Check paper existence, fulltext availability, and vector status.

    Returns a result dict to short-circuit on failure, or None to proceed.
    """
    from paperforge.memory.db import get_memory_db_path, open_live_reader
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None
    with open_live_reader(vault, db_path) as conn:
        return _check_paper_scope_locked(conn, paper_key, allow_bm25_only)


def _check_paper_scope_locked(conn, paper_key: str, allow_bm25_only: bool) -> dict | None:
    """Paper-scope availability check against an open reader connection."""
    paper_exists = conn.execute("SELECT 1 FROM papers WHERE zotero_key=?", (paper_key,)).fetchone()
    if not paper_exists:
        return {"error": "paper_not_found", "message": f"Paper not found: {paper_key}"}

    bc = conn.execute(
        "SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1",
        (paper_key,),
    ).fetchone()[0]
    if bc == 0:
        return {"fulltext_unavailable": True}

    valid_body = conn.execute(
        "SELECT COUNT(*) FROM vec_body_meta WHERE paper_id=? AND unit_id<>''",
        (paper_key,),
    ).fetchone()[0]
    valid_object = conn.execute(
        "SELECT COUNT(*) FROM vec_objects_meta WHERE paper_id=? AND unit_id<>''",
        (paper_key,),
    ).fetchone()[0]
    if valid_body + valid_object == 0:
        if allow_bm25_only:
            return None  # BM25-only mode: vectors optional
        old_body = conn.execute(
            "SELECT COUNT(*) FROM vec_body_meta WHERE paper_id=?", (paper_key,),
        ).fetchone()[0]
        old_object = conn.execute(
            "SELECT COUNT(*) FROM vec_objects_meta WHERE paper_id=?", (paper_key,),
        ).fetchone()[0]
        raw_total = old_body + old_object
        vs = "stale" if raw_total > 0 else "not_built"
        return {"vector_state": vs}
    return None


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query
    limit = args.limit or 5
    deep = getattr(args, "deep", False)
    paper_key = getattr(args, "paper", None)

    # Paper-scoped availability check (applies to both deep and standard paths)
    if paper_key:
        scope = _paper_scope_check(vault, paper_key, allow_bm25_only=deep)
        if scope is not None:
            if "error" in scope:
                result = PFResult(ok=False, command="retrieve", version=PF_VERSION,
                    error=PFError(code=ErrorCode.PATH_NOT_FOUND if scope["error"] == "paper_not_found" else ErrorCode.INTERNAL_ERROR,
                        message=scope["message"]),
                    data={"scoped_paper": paper_key})
                _output(args, result, query)
                return 1
            if scope.get("fulltext_unavailable"):
                result = PFResult(ok=True, command="retrieve", version=PF_VERSION,
                    data={"query": query, "matches": [], "count": 0, "fulltext_unavailable": True, "scoped_paper": paper_key})
                _output(args, result, query)
                return 0
            if "vector_state" in scope:
                vs = scope["vector_state"]
                result = PFResult(ok=False, command="retrieve", version=PF_VERSION,
                    error=PFError(code=ErrorCode.INTERNAL_ERROR,
                        message=f"Vectors for {paper_key} are {vs}. {'Rebuild required.' if vs == 'stale' else 'Build vectors first.'}"),
                    data={"vector_state": vs, "scoped_paper": paper_key})
                _output(args, result, query)
                return 1

    from paperforge.embedding import get_embed_status
    # ── @ Deep Search mode: query rewrite + hybrid retrieval ──────
    if deep:
        try:
            raw_chunks = hybrid_search(vault, query, limit=limit, paper_id=paper_key)
            # #159 §6 reader gate: never serve a mismatched/unknown chain.
            from paperforge.reader_gate import filter_readable

            raw_chunks = filter_readable(vault, raw_chunks, require_vector=True)
        except Exception as e:
            result = PFResult(
                ok=False,
                command="retrieve",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
            )
            print(result.to_json() if args.json else result.error.message, file=sys.stderr if not args.json else sys.stdout)
            return 1

        matches = _normalize_matches(raw_chunks, source_prefix="deep")
        data = {
            "query": query,
            "matches": matches,
            "count": len(matches),
            "deep": True,
            "route_explanation": {"primary_arm": "deep_search", "query_rewrite": True, "hybrid": True},
        }
        if paper_key:
            data["scoped_paper"] = paper_key
        result = _build_result(query, data, matches, vault)
        _output(args, result, query)
        return 0

    # ── Standard vector retrieve ──────────────────────────────────
    status = get_embed_status(vault)
    valid_total = status.get("valid_total_chunks", 0)
    if valid_total == 0:
        state = status.get("vector_state", "not_built")
        result = PFResult(
            ok=False,
            command="retrieve",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Vector index is {state}. {'Rebuild vectors before retrieving.' if state == 'not_built' else 'Rebuild required.'}",
            ),
            data={
                "next_action": "paperforge embed build" if state == "not_built" else "paperforge embed build --force",
                "vector_state": state,
            },
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    try:
        chunks = merge_retrieve(vault, query, limit=limit, expand=args.expand, paper_id=paper_key)
        # #159 §6 reader gate: never serve a mismatched/unknown chain.
        from paperforge.reader_gate import filter_readable

        chunks = filter_readable(vault, chunks, require_vector=True)
    except Exception as e:
        result = PFResult(
            ok=False,
            command="retrieve",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    matches = _normalize_matches(chunks)
    data = {
        "query": query,
        "matches": matches,
        "count": len(matches),
        "route_explanation": {"primary_arm": "vector_retrieve", "compatibility_mode": False},
    }
    if paper_key:
        data["scoped_paper"] = paper_key
    result = _build_result(query, data, matches, vault)
    _output(args, result, query)
    return 0
def _normalize_matches(chunks: list[dict], source_prefix: str = "") -> list[dict]:
    """Normalize retrieval chunks to unified PFResult match format."""
    matches: list[dict] = []
    for c in chunks:
        zkey = c.get("paper_id", c.get("zotero_key", ""))
        base_source = source_prefix or c.get("source", "vector")
        match = {
            "zotero_key": zkey,
            "unit_id": c.get("unit_id", ""),
            "source_kind": c.get("source_kind", c.get("source", "vector")),
            "retrieval_mode": base_source if source_prefix else "standard",
            "title": c.get("title", ""),
            "first_author": c.get("first_author", ""),
            "year": c.get("year", ""),
            "journal": c.get("journal", ""),
            "domain": c.get("domain", ""),
            "abstract": "",
            "score": c.get("score", 0),
            "text": c.get("chunk_text", c.get("text", "")),
            "heading": c.get("section_path", c.get("heading", "")),
            "node_id": c.get("node_id", ""),
            "structure_path": c.get("structure_path", []),
            "structure_version": c.get("structure_version", ""),
            "structure_resolved": c.get("structure_resolved", False),
            "section_title": c.get("section_title", ""),
            "section_level": c.get("section_level", 0),
            "part_ordinal": c.get("part_ordinal", 0),
        }
        if c.get("object_kind"):
            match["object_kind"] = c["object_kind"]
        if c.get("object_label"):
            match["object_label"] = c["object_label"]
        if c.get("caption_text"):
            match["caption_text"] = c["caption_text"]
        if "page_span" in c:
            match["page_span"] = c["page_span"]
        matches.append(match)
    return matches


def _build_result(query: str, data: dict, matches: list[dict], vault: Path) -> PFResult:
    """Build PFResult with warnings and next actions."""
    warnings: list[str] = []
    next_actions: list[dict] = []
    is_scoped = bool(data.get("scoped_paper"))
    if not matches:
        if not is_scoped:
            warnings.append("Retrieval returned no results for the query.")
            next_actions.append({"command": "paperforge query-plan", "reason": "Review fallback modes."})
    else:
        if _is_low_confidence_semantic_result(matches):
            warnings.append("Low-confidence hits — verify with fulltext grep before treating as evidence.")
    return PFResult(
        ok=True, command="retrieve", version=PF_VERSION, data=data, warnings=warnings, next_actions=next_actions
    )

def _output(args: argparse.Namespace, result: PFResult, query: str) -> None:
    """Print result in JSON or human-readable format."""
    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            matches = result.data.get("matches", [])
            scoped = result.data.get("scoped_paper", "")
            prefix = f" [{scoped}]" if scoped else ""
            print(f"{len(matches)} matches{prefix} for: {query}")
            for m in matches:
                path = "/".join(m.get("structure_path", [])) or m.get("heading", "")
                print(f"  [{m.get('source_kind', '?')}] {m.get('zotero_key', '')}: {path} — {m.get('text', '')[:60]}...")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
