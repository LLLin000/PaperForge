from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.embedding import hybrid_search, merge_retrieve, retrieve_chunks
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime


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
    generic_top = sum(1 for chunk in chunks[:5] if _looks_generic_chunk(chunk.get("chunk_text", "")))
    max_score = max(float(chunk.get("score", 0) or 0) for chunk in chunks[:5])
    return generic_top >= 3 or max_score < 0.62


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query
    limit = args.limit or 5
    deep = getattr(args, "deep", False)
    paper_key = getattr(args, "paper", None)

    from paperforge.embedding import get_embed_status

    # ── @ Deep Search mode: query rewrite + hybrid retrieval ──────
    if deep:
        try:
            raw_chunks = hybrid_search(vault, query, limit=limit, paper_id=paper_key)
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

    # Paper-scoped availability check
    if paper_key:
        db_path = get_memory_db_path(vault)
        fulltext_unavailable = False
        if db_path.exists():
            conn = get_connection(db_path, read_only=True)
            try:
                # 1. Check paper exists
                paper_exists = conn.execute("SELECT 1 FROM papers WHERE zotero_key=?", (paper_key,)).fetchone()
                if not paper_exists:
                    _output(args, PFResult(ok=False, command="retrieve", version=PF_VERSION,
                        error=PFError(code=ErrorCode.PATH_NOT_FOUND, message=f"Paper not found: {paper_key}"),
                        data={"scoped_paper": paper_key}), query)
                    return 1 if not args.json else 0

                # 2. Check fulltext availability
                bc = conn.execute(
                    "SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1",
                    (paper_key,),
                ).fetchone()[0]
                if bc == 0:
                    fulltext_unavailable = True

                # 3. Check per-paper valid vectors
                valid_for_paper = conn.execute(
                    "SELECT COUNT(*) FROM vec_body_meta WHERE paper_id=? AND unit_id<>''",
                    (paper_key,),
                ).fetchone()[0]
                valid_for_paper += conn.execute(
                    "SELECT COUNT(*) FROM vec_objects_meta WHERE paper_id=? AND unit_id<>''",
                    (paper_key,),
                ).fetchone()[0]
            finally:
                conn.close()

        if fulltext_unavailable:
            result = PFResult(
                ok=True, command="retrieve", version=PF_VERSION,
                data={"query": query, "matches": [], "count": 0, "fulltext_unavailable": True, "scoped_paper": paper_key},
            )
            _output(args, result, query)
            return 0

        if bc > 0 and valid_for_paper == 0:
            # Has body_units but no valid vectors — check if vectors ever existed
            had_vecs = conn.execute(
                "SELECT COUNT(*) FROM vec_body_meta WHERE paper_id=?",
                (paper_key,),
            ).fetchone()[0] if db_path.exists() else 0
            vec_state = "stale" if had_vecs > 0 else "not_built"
            result = PFResult(
                ok=False, command="retrieve", version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR,
                    message=f"Vectors for {paper_key} are {vec_state}. {'Rebuild required.' if vec_state == 'stale' else 'Build vectors first.'}"),
                data={"vector_state": vec_state, "scoped_paper": paper_key},
            )
            _output(args, result, query)
            return 1
        # For paper-scoped, skip global valid_total check — use per-paper result
        if valid_for_paper > 0:
            try:
                chunks = merge_retrieve(vault, query, limit=limit, expand=args.expand, paper_id=paper_key)
            except Exception as e:
                result = PFResult(ok=False, command="retrieve", version=PF_VERSION,
                    error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)))
                _output(args, result, query)
                return 1
            matches = _normalize_matches(chunks)
            data = {"query": query, "matches": matches, "count": len(matches),
                    "route_explanation": {"primary_arm": "vector_retrieve", "compatibility_mode": False},
                    "scoped_paper": paper_key}
            result = _build_result(query, data, matches, vault)
            _output(args, result, query)
            return 0

    valid_total = status.get("valid_total_chunks", 0)
    if valid_total == 0:
        avail = status.get("vector_state", "not_built")
        plan = enrich_query_plan_with_runtime(build_query_plan(query, "content"), vault)
        result = PFResult(
            ok=False,
            command="retrieve",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Vector index is {avail}. {'Rebuild vectors before retrieving.' if avail == 'not_built' else 'Rebuild required.'}",
            ),
            data={
                "next_action": "paperforge embed build" if avail == "not_built" else "paperforge embed build --force",
                "vector_state": avail,
            },
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    try:
        chunks = merge_retrieve(vault, query, limit=limit, expand=args.expand, paper_id=paper_key)
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
    seen_zotero: set[str] = set()
    for c in chunks:
        zkey = c.get("paper_id", c.get("zotero_key", ""))
        # Avoid duplicates
        if zkey in seen_zotero and not c.get("unit_id"):
            continue
        seen_zotero.add(zkey)
        match = {
            "zotero_key": zkey,
            "unit_id": c.get("unit_id", ""),
            "title": c.get("title", ""),
            "first_author": c.get("first_author", ""),
            "year": c.get("year", ""),
            "journal": c.get("journal", ""),
            "domain": c.get("domain", ""),
            "abstract": "",
            "score": c.get("score", 0),
            "text": c.get("chunk_text", c.get("text", "")),
            "heading": c.get("section_path", c.get("heading", "")),
            "source": source_prefix or c.get("source", "vector"),
            "node_id": c.get("node_id", ""),
            "structure_path": c.get("structure_path", []),
            "structure_version": c.get("structure_version", ""),
            "structure_resolved": c.get("structure_resolved", False),
        }
        if c.get("object_kind"):
            match["object_kind"] = c["object_kind"]
        matches.append(match)
    return matches


def _build_result(query: str, data: dict, matches: list[dict], vault: Path) -> PFResult:
    """Build PFResult with warnings and next actions."""
    warnings: list[str] = []
    next_actions: list[dict] = []
    if not matches:
        plan = enrich_query_plan_with_runtime(build_query_plan(query, "content"), vault)
        warnings.append("Retrieval returned no results for the query.")
        next_actions.append({"command": "paperforge query-plan", "reason": "Review fallback modes."})
    else:
        # Check if any results have low confidence
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
                print(f"  [{m.get('source', '?')}] {m.get('zotero_key', '')}: {path} — {m.get('text', '')[:60]}...")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
