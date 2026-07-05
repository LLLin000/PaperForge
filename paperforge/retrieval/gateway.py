"""paperforge.retrieval.gateway — Layer 4 gateway command routing.

Provides the core `route_gateway()` function that all gateway commands
route through. Each intent is routed to the correct real data source.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.io import read_json
from paperforge.core.result import PFResult
from paperforge.memory.db import get_connection, get_memory_db_path

logger = logging.getLogger(__name__)

# Map gateway intent names to build_query_plan intent strings
INTENTS: dict[str, str] = {
    "paper-lookup": "known-paper",
    "content-discovery": "content",
    "paper-navigation": "known-paper",
    "scoped-fetch": "known-paper",
}


def route_gateway(
    vault: Path,
    intent: str,
    query: str,
    *,
    json_mode: bool,  # noqa: ARG001
    limit: int = 5,
) -> PFResult:
    """Route a gateway command to the real Layer 4 data source.

    Parameters
    ----------
    vault : Path
        PaperForge vault root.
    intent : str
        Gateway intent name (``"paper-lookup"``, ``"content-discovery"``,
        ``"paper-navigation"``, or ``"scoped-fetch"``).
    query : str
        Free-text or structured query.
    json_mode : bool
        Whether the caller expects JSON output (passed through to callers).
    limit : int, optional
        Maximum result count (default 5).

    Returns
    -------
    PFResult
        Result packet with data from the real source of truth for the intent.
    """
    if intent == "paper-lookup":
        return _run_paper_lookup(vault, query, limit=limit)
    if intent == "content-discovery":
        if _body_units_fts_exists(vault):
            return _run_body_unit_discovery(vault, query, limit=limit)
        return _run_compat_content_discovery(vault, query, limit=limit)
    if intent == "paper-navigation":
        return _run_paper_navigation(vault, query)
    if intent == "scoped-fetch":
        return _run_scoped_fetch(vault, query)
    raise ValueError(f"Unsupported Layer 4 intent: {intent}")


# ---------------------------------------------------------------------------
# FTS helpers
# ---------------------------------------------------------------------------


def _tokenize_for_fts(q: str) -> str:
    """Tokenize a query string into safe FTS5 match terms."""
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", q)
    if not tokens:
        return q
    return " OR ".join(f'"{t}"' for t in tokens)


def _body_units_fts_exists(vault: Path) -> bool:
    """Check whether the body_units_fts table exists and has rows."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False
    conn = get_connection(db_path, read_only=True)
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM body_units_fts").fetchone()
        return row["cnt"] > 0
    except Exception:
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Paper root resolution (shared by navigation & scoped-fetch)
# ---------------------------------------------------------------------------


def _resolve_paper_root(vault: Path, query: str) -> Path | None:
    """Resolve a paper query to its OCR root directory."""
    from paperforge.config import paperforge_paths
    from paperforge.memory.query import lookup_paper

    db_path = get_memory_db_path(vault)
    if not db_path or not db_path.exists():
        return None
    conn = get_connection(db_path, read_only=True)
    try:
        entries = lookup_paper(conn, query)
        if entries:
            ocr_root = paperforge_paths(vault)["ocr"]
            return ocr_root / entries[0]["zotero_key"]
    finally:
        conn.close()
    return None


# ---------------------------------------------------------------------------
# Intent: paper-lookup
# ---------------------------------------------------------------------------


def _run_paper_lookup(vault: Path, query: str, *, limit: int = 5) -> PFResult:
    """Route paper-lookup intent through ``lookup_paper()``."""
    from paperforge.memory.query import lookup_paper

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return PFResult(
            ok=False,
            command="paper-lookup",
            version=PF_VERSION,
            data={
                "intent": "paper-lookup",
                "query": query,
                "results": [],
                "route_explanation": {
                    "primary_arm": "lookup_paper",
                    "error": "database_not_found",
                },
            },
        )
    conn = get_connection(db_path, read_only=True)
    try:
        entries = lookup_paper(conn, query)
        limited = entries[:limit]
        return PFResult(
            ok=True,
            command="paper-lookup",
            version=PF_VERSION,
            data={
                "intent": "paper-lookup",
                "query": query,
                "results": limited,
                "count": len(limited),
                "route_explanation": {
                    "primary_arm": "lookup_paper",
                    "matched": len(limited) > 0,
                    "compatibility_mode": False,
                },
            },
        )
    except Exception as exc:
        logger.exception("paper-lookup failed")
        return PFResult(
            ok=False,
            command="paper-lookup",
            version=PF_VERSION,
            data={
                "intent": "paper-lookup",
                "query": query,
                "results": [],
                "route_explanation": {
                    "primary_arm": "lookup_paper",
                    "error": str(exc),
                },
            },
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Intent: content-discovery
# ---------------------------------------------------------------------------


def _run_body_unit_discovery(
    vault: Path, query: str, *, limit: int = 5
) -> PFResult:
    """Search ``body_units_fts`` for content-level discovery."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return PFResult(
            ok=False,
            command="content-discovery",
            version=PF_VERSION,
            data={
                "intent": "content-discovery",
                "query": query,
                "results": [],
                "route_explanation": {
                    "primary_arm": "body_units_fts",
                    "error": "database_not_found",
                },
            },
        )
    conn = get_connection(db_path, read_only=True)
    try:
        fts_query = _tokenize_for_fts(query)
        rows = conn.execute(
            """SELECT unit_id, paper_id, section_path, unit_text, rank
               FROM body_units_fts
               WHERE body_units_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()
        results = [dict(r) for r in rows]
        return PFResult(
            ok=True,
            command="content-discovery",
            version=PF_VERSION,
            data={
                "intent": "content-discovery",
                "query": query,
                "results": results,
                "count": len(results),
                "route_explanation": {
                    "primary_arm": "body_units_fts",
                    "fallback_arms": ["vector_retrieve"],
                    "compatibility_mode": False,
                },
            },
        )
    except Exception as exc:
        logger.exception("body_units_fts query failed, falling back")
        return _run_compat_content_discovery(
            vault, query, limit=limit, explanation_note=str(exc)
        )
    finally:
        conn.close()


def _run_compat_content_discovery(
    vault: Path,
    query: str,
    *,
    limit: int = 5,
    explanation_note: str = "",
) -> PFResult:
    """Fallback content discovery using ``paper_fts`` (metadata-only)."""
    from paperforge.memory.fts import search_papers

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return PFResult(
            ok=False,
            command="content-discovery",
            version=PF_VERSION,
            data={
                "intent": "content-discovery",
                "query": query,
                "results": [],
                "route_explanation": {
                    "primary_arm": "paper_fts",
                    "error": "database_not_found",
                },
            },
        )
    conn = get_connection(db_path, read_only=True)
    try:
        results = search_papers(conn, query, limit=limit)
        return PFResult(
            ok=True,
            command="content-discovery",
            version=PF_VERSION,
            data={
                "intent": "content-discovery",
                "query": query,
                "results": results,
                "count": len(results),
                "route_explanation": {
                    "primary_arm": "paper_fts",
                    "compatibility_mode": True,
                    "note": (
                        explanation_note
                        or "body_units_fts unavailable, using metadata FTS"
                    ),
                },
            },
        )
    except Exception as exc:
        return PFResult(
            ok=False,
            command="content-discovery",
            version=PF_VERSION,
            data={
                "intent": "content-discovery",
                "query": query,
                "results": [],
                "route_explanation": {
                    "primary_arm": "paper_fts",
                    "error": str(exc),
                },
            },
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Intent: paper-navigation
# ---------------------------------------------------------------------------


def _run_paper_navigation(vault: Path, query: str) -> PFResult:
    """Read structure-tree.json (or fall back to role-index) for navigation."""
    paper_root = _resolve_paper_root(vault, query)
    if paper_root is None:
        return PFResult(
            ok=False,
            command="paper-navigation",
            version=PF_VERSION,
            data={
                "intent": "paper-navigation",
                "query": query,
                "mode": "not_found",
                "route_explanation": {
                    "primary_arm": "structure_tree",
                    "note": "paper not found",
                },
            },
        )

    tree_path = paper_root / "index" / "structure-tree.json"
    if tree_path.exists():
        tree = read_json(tree_path)
        return PFResult(
            ok=True,
            command="paper-navigation",
            version=PF_VERSION,
            data={
                "intent": "paper-navigation",
                "query": query,
                "mode": "structure_tree",
                "paper_id": tree.get("paper_id", ""),
                "nodes": tree.get("nodes", []),
                "route_explanation": {
                    "primary_arm": "structure_tree",
                    "fallback": False,
                },
            },
        )

    # Fallback: role-index summary
    role_index_path = paper_root / "index" / "role-index.json"
    if role_index_path.exists():
        from paperforge.retrieval.structure_tree import summarize_role_index

        role_index = read_json(role_index_path)
        summary = summarize_role_index(role_index)
        return PFResult(
            ok=True,
            command="paper-navigation",
            version=PF_VERSION,
            data={
                "intent": "paper-navigation",
                "query": query,
                "mode": "role_index_summary",
                "paper_id": query,
                "summary": summary,
                "route_explanation": {
                    "primary_arm": "structure_tree",
                    "fallback_arm": "role_index",
                    "note": "structure-tree.json not found, using role-index",
                },
            },
        )

    return PFResult(
        ok=False,
        command="paper-navigation",
        version=PF_VERSION,
        data={
            "intent": "paper-navigation",
            "query": query,
            "mode": "no_index",
            "route_explanation": {
                "primary_arm": "structure_tree",
                "note": "no index found for paper",
            },
        },
    )


# ---------------------------------------------------------------------------
# Intent: scoped-fetch
# ---------------------------------------------------------------------------


def _run_scoped_fetch(vault: Path, query: str) -> PFResult:
    """Fetch body units scoped by paper, optionally filtered by section or node.

    The *query* is treated as a paper identifier (author, title, DOI, etc.).
    An optional ``:section_path`` or ``#node_id`` suffix narrows the results.
    """
    from paperforge.memory.query import lookup_paper

    # Parse optional section / node filter from query suffix
    base_query: str = query
    section_filter: str | None = None
    node_filter: str | None = None
    if ":" in query and not query.startswith(":"):
        parts = query.split(":", 1)
        base_query = parts[0]
        section_filter = parts[1].strip()
    elif "#" in query:
        parts = query.split("#", 1)
        base_query = parts[0]
        node_filter = parts[1].strip()

    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return PFResult(
            ok=False,
            command="scoped-fetch",
            version=PF_VERSION,
            data={
                "intent": "scoped-fetch",
                "query": query,
                "body_units": [],
                "route_explanation": {
                    "primary_arm": "body_units",
                    "error": "database_not_found",
                },
            },
        )

    conn = get_connection(db_path, read_only=True)
    try:
        entries = lookup_paper(conn, base_query)
        if not entries:
            return PFResult(
                ok=False,
                command="scoped-fetch",
                version=PF_VERSION,
                data={
                    "intent": "scoped-fetch",
                    "query": query,
                    "body_units": [],
                    "route_explanation": {
                        "primary_arm": "body_units",
                        "note": "paper not found",
                    },
                },
            )

        paper_id = entries[0].get("zotero_key", "")

        if section_filter:
            rows = conn.execute(
                """SELECT unit_id, paper_id, section_path, unit_text,
                          page_span_json, block_span_json
                   FROM body_units
                   WHERE paper_id = ? AND section_path LIKE ?
                   ORDER BY unit_id""",
                (paper_id, f"%{section_filter}%"),
            ).fetchall()
        elif node_filter:
            rows = conn.execute(
                """SELECT unit_id, paper_id, section_path, unit_text,
                          page_span_json, block_span_json
                   FROM body_units
                   WHERE paper_id = ? AND unit_id LIKE ?
                   ORDER BY unit_id""",
                (paper_id, f"%{node_filter}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT unit_id, paper_id, section_path, unit_text,
                          page_span_json, block_span_json
                   FROM body_units
                   WHERE paper_id = ?
                   ORDER BY unit_id""",
                (paper_id,),
            ).fetchall()

        units = [dict(r) for r in rows]

        # Attach manifest if available
        manifest_row = conn.execute(
            "SELECT value FROM meta WHERE key = ?",
            (f"manifest:{paper_id}",),
        ).fetchone()
        manifest_data: dict | None = (
            json.loads(manifest_row["value"]) if manifest_row else None
        )

        return PFResult(
            ok=True,
            command="scoped-fetch",
            version=PF_VERSION,
            data={
                "intent": "scoped-fetch",
                "query": query,
                "paper_id": paper_id,
                "body_units": units,
                "count": len(units),
                "manifest": manifest_data,
                "route_explanation": {
                    "primary_arm": "body_units",
                    "section_filter": bool(section_filter),
                    "node_filter": bool(node_filter),
                },
            },
        )
    except Exception as exc:
        logger.exception("scoped-fetch failed")
        return PFResult(
            ok=False,
            command="scoped-fetch",
            version=PF_VERSION,
            data={
                "intent": "scoped-fetch",
                "query": query,
                "body_units": [],
                "route_explanation": {
                    "primary_arm": "body_units",
                    "error": str(exc),
                },
            },
        )
    finally:
        conn.close()
