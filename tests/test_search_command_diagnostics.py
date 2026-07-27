from __future__ import annotations


def test_evidence_query_routes_to_content_retrieve() -> None:
    from paperforge.query_planning import build_query_plan
    plan = build_query_plan("electric field parameters mammalian cells", "content")
    assert plan["primary"]["command"] == "retrieve"
    assert plan["fallback"]["command"] == "search"


def test_metadata_query_still_routes_to_search() -> None:
    from paperforge.query_planning import build_query_plan
    plan = build_query_plan("Lin 2024 electrical stimulation", "discover")
    assert plan["primary"]["command"] == "search"


def test_vague_content_query_still_routes_to_retrieve() -> None:
    from paperforge.query_planning import build_query_plan
    plan = build_query_plan("how do cells respond to electric fields", "content")
    assert plan["primary"]["command"] == "retrieve"
