from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.embedding import retrieve_chunks
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

    # Check if vector index exists
    from paperforge.embedding import get_embed_status

    status = get_embed_status(vault)
    if not status.get("healthy", True):
        plan = enrich_query_plan_with_runtime(build_query_plan(query, "content"), vault)
        result = PFResult(
            ok=False,
            command="retrieve",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Vector index is unreadable. Rebuild vectors before retrieving.",
            ),
            data={
                "next_action": "paperforge embed build --force",
                "details": status.get("error", ""),
                "interactive_fallback_required": plan.get("interactive_fallback_required", False),
                "scope_assessment": plan.get("scope_assessment"),
                "suggested_modes": plan.get("suggested_modes", []),
            },
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    if status.get("chunk_count", 0) == 0:
        plan = enrich_query_plan_with_runtime(build_query_plan(query, "content"), vault)
        result = PFResult(
            ok=False,
            command="retrieve",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message="Vector index is empty. Run paperforge embed build first.",
            ),
            data={
                "next_action": "paperforge embed build",
                "interactive_fallback_required": plan.get("interactive_fallback_required", False),
                "scope_assessment": plan.get("scope_assessment"),
                "suggested_modes": plan.get("suggested_modes", []),
            },
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    try:
        chunks = retrieve_chunks(vault, query, limit=limit, expand=args.expand)
    except Exception as e:
        result = PFResult(
            ok=False,
            command="retrieve",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(e)),
        )
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
                        (c["paper_id"],),
                    ).fetchone()
                    if row:
                        c["citation_key"] = row["citation_key"]
                        c["title"] = row["title"]
                        c["year"] = row["year"]
                        c["first_author"] = row["first_author"]
            finally:
                conn.close()

    data = {
        "query": query,
        "chunks": chunks,
        "count": len(chunks),
        "route_explanation": {
            "primary_arm": "vector_retrieve",
            "compatibility_mode": False,
        },
    }
    warnings: list[str] = []
    next_actions: list[dict] = []
    if len(chunks) == 0:
        plan = enrich_query_plan_with_runtime(build_query_plan(query, "content"), vault)
        data["query_diagnostic"] = {
            "scope_assessment": plan.get("scope_assessment"),
            "interactive_fallback_required": plan.get("interactive_fallback_required", False),
            "suggested_modes": plan.get("suggested_modes", []),
        }
        warnings.append(
            "Semantic retrieval returned no chunks. This does not prove the content is absent from the library."
        )
        next_actions.append(
            {
                "command": "paperforge query-plan",
                "reason": "Review the fallback modes for content lookup and fulltext verification.",
            }
        )
        try:
            ocr_root = vault / "System" / "PaperForge" / "ocr"
            ocr_papers = 0
            if ocr_root.exists():
                ocr_papers = sum(
                    1
                    for paper_dir in ocr_root.iterdir()
                    if paper_dir.is_dir() and (paper_dir / "index" / "role-index.json").exists()
                )
            data["ocr_evidence_available"] = ocr_papers
            if ocr_papers > 0:
                next_actions.append(
                    {
                        "command": "paperforge search",
                        "reason": f"OCR evidence available for {ocr_papers} paper(s)",
                    }
                )
        except Exception:
            pass
    elif _is_low_confidence_semantic_result(chunks):
        plan = enrich_query_plan_with_runtime(build_query_plan(query, "content"), vault)
        data["query_diagnostic"] = {
            "scope_assessment": plan.get("scope_assessment"),
            "interactive_fallback_required": True,
            "suggested_modes": plan.get("suggested_modes", []),
            "reason": "Top semantic hits look generic or weakly related to the query.",
        }
        warnings.append(
            "Semantic retrieval returned low-confidence hits. Verify with fulltext grep or narrow the scope before treating these as evidence."
        )
        next_actions.append(
            {
                "command": "paperforge query-plan",
                "reason": "Inspect fallback modes for exact fulltext verification.",
            }
        )
    result = PFResult(
        ok=True, command="retrieve", version=PF_VERSION, data=data, warnings=warnings, next_actions=next_actions
    )

    if args.json:
        print(result.to_json())
    else:
        print(f"{len(chunks)} chunks for: {query}")
        for c in chunks:
            print(
                f"  [{c.get('section', '')}] {c.get('citation_key', '')} p{c.get('page_number', 0)}: {c['chunk_text'][:80]}..."
            )
    return 0
