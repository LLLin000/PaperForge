"""paperforge.retrieval.gateway — Layer 4 gateway command routing.

Provides the core `route_gateway()` function that all gateway commands
route through. Currently delegates to existing capabilities; later tasks
will upgrade routing to use real Layer 4 artifacts.
"""

from __future__ import annotations

from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.result import PFResult
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime

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
    json_mode: bool,
    limit: int = 5,
) -> PFResult:
    """Route a gateway command through the query planning pipeline.

    Parameters
    ----------
    vault : Path
        PaperForge vault root.
    intent : str
        Gateway intent name (e.g. ``"paper-lookup"``).
    query : str
        Free-text or structured query.
    json_mode : bool
        Whether the caller expects JSON output.
    limit : int, optional
        Maximum result count (default 5).

    Returns
    -------
    PFResult
        Result packet with the route plan and intent metadata.
    """
    plan = enrich_query_plan_with_runtime(
        build_query_plan(query, INTENTS[intent]),
        vault,
    )
    return PFResult(
        ok=True,
        command=intent,
        version=PF_VERSION,
        data={
            "intent": intent,
            "query": query,
            "route_plan": plan,
            "limit": limit,
        },
    )
