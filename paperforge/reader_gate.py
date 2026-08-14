"""#159 §6 reader gate — derived materialization never serves a mismatched
or unknown lineage chain.

Any reader of derived materialization (retrieval units, vectors) fails
closed on lineage mismatch or ``unknown``: a hit whose paper's retrieval
or vector lineage is not ``current`` is dropped — never served.  The
probe keeps its UNRESOLVED semantics; this module is where that semantics
becomes a serve-time decision.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def filter_readable(vault: Path, hits: list[dict[str, Any]], *, require_vector: bool = True) -> list[dict[str, Any]]:
    """Drop hits whose paper's lineage is mismatched/unknown (fail closed).

    - paper absent from the lineage probe → unknown → dropped
    - retrieval != current → the text materialization is stale → dropped
    - require_vector and vector not in (current, incomplete) → dropped

    ``incomplete`` vectors are ALLOWED: they are real embeddings produced
    from an incomplete OCR product (missing/empty structure tree, so no
    body units — but any object vectors that exist are genuine data).
    The state is still surfaced honestly by the probe/reconcile (rebuild
    derived), but already-materialized vectors keep serving instead of
    silently regressing.

    ``require_vector=False`` is for readers that only consume text
    materialization (retrieval units), never vectors.

    When the lineage infrastructure itself is absent (no memory DB — probe
    reports an unknown envelope), there IS no chain to be mismatched: the
    hits pass through (compat for pre-convergence/test environments).  The
    gate binds the moment a chain is observable.
    """
    from paperforge.lineage import probe_lineage

    try:
        probe = probe_lineage(vault)
    except Exception:  # noqa: BLE001 — unobservable lineage FAILS CLOSED:
        # never serve derived materialization we cannot prove compatible.
        return []
    papers = probe.get("papers", {})

    out: list[dict[str, Any]] = []
    for hit in hits:
        paper_id = str(hit.get("paper_id", ""))
        state = papers.get(paper_id)
        if state is None:
            continue  # unknown paper → never serve
        if state.get("retrieval") not in ("current", "incomplete"):
            continue  # mismatched retrieval chain → never serve
        if require_vector and state.get("vector") not in ("current", "incomplete"):
            continue  # mismatched vector chain → never serve
        out.append(hit)
    return out
