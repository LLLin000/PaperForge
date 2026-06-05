from __future__ import annotations


def test_evidence_query_routes_to_ocr_evidence_search() -> None:
    from paperforge.query_planning import build_query_plan

    plan = build_query_plan("electric field parameters mammalian cells", "evidence")

    assert plan["query_class"] == "evidence_query"
    assert plan["recommended_primary"]["command"] in ("ocr-evidence", "search")
    assert "evidence" in str(plan.get("suggested_modes", [])).lower() or "ocr" in str(plan.get("suggested_modes", [])).lower()


def test_metadata_query_still_routes_to_search() -> None:
    from paperforge.query_planning import build_query_plan

    plan = build_query_plan("Lin 2024 electrical stimulation", "discover")

    assert plan["query_class"] != "evidence_query"
    assert plan["recommended_primary"]["command"] == "search"


def test_vague_content_query_still_routes_to_retrieve() -> None:
    from paperforge.query_planning import build_query_plan

    plan = build_query_plan("how do cells respond to electric fields", "content")

    assert plan["query_class"] != "evidence_query"
    assert plan["recommended_primary"]["command"] == "retrieve"
