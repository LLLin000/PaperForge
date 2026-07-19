from __future__ import annotations

from pathlib import Path

import pytest

from paperforge.commands.query_plan import run as query_plan_run
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime


class _Args:
    def __init__(self, query: str, intent: str, vault_path: Path, json: bool = True) -> None:
        self.query = query
        self.intent = intent
        self.vault_path = vault_path
        self.json = json


def test_query_plan_identifier_exact_prefers_paper_context() -> None:
    plan = build_query_plan("10.1016/j.heliyon.2024.e38112", "known-paper")
    assert plan["query_class"] == "identifier_exact"
    assert plan["recommended_primary"]["command"] == "paper-context"


def test_query_plan_mixed_author_year_rewrites_to_author_year_search() -> None:
    plan = build_query_plan("Lin 2024 Electrical Stimulation", "discover")
    primary = plan["recommended_primary"]
    assert plan["query_class"] == "mixed_query"
    assert primary["command"] == "search"
    assert primary["args"]["query"] == "Lin"
    assert primary["args"]["year_from"] == 2024
    assert primary["args"]["year_to"] == 2024


def test_query_plan_content_prefers_retrieve() -> None:
    plan = build_query_plan("galvanotaxis", "content")
    assert plan["query_class"] == "content_term"
    assert plan["recommended_primary"]["command"] == "retrieve"
    assert any(step["action"] == "interactive_fulltext_fallback" for step in plan["fallback_plan"])


def test_query_plan_runtime_enrichment_without_retrieve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "paperforge.commands.query_plan.enrich_query_plan_with_runtime",
        lambda plan, vault: {
            **plan,
            "runtime": {"retrieve_available": False, "vector_status": {"db_exists": False, "chunk_count": 0, "healthy": True, "error": ""}},
            "scope_assessment": {
                "source": "library",
                "label": "full library",
                "estimated_paper_count": 120,
                "fulltext_ready_count": 80,
                "recommended_mode": "ask_user_before_broad_grep",
            },
            "interactive_fallback_required": True,
            "suggested_modes": [
                {"mode": "ask_for_scope_limit", "description": "Ask first."},
                {"mode": "fulltext_rg_or_grep", "description": "Search fulltext."},
            ],
        },
    )
    args = _Args("galvanotaxis", "content", tmp_path)
    assert query_plan_run(args) == 0
    out = capsys.readouterr().out
    assert '"interactive_fallback_required": true' in out.lower()
    assert '"mode": "ask_for_scope_limit"' in out


def test_query_plan_discover_prefers_context_for_known_domain(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan = build_query_plan("骨科 里有什么", "discover")
    monkeypatch.setattr("paperforge.embedding.get_embed_status", lambda vault: {"db_exists": False, "chunk_count": 0, "healthy": True, "error": ""})
    monkeypatch.setattr(
        "paperforge.worker.asset_index.read_index",
        lambda vault: {"items": [{"domain": "骨科", "lifecycle": "fulltext_ready", "collections": []} for _ in range(5)]},
    )
    enriched = enrich_query_plan_with_runtime(plan, tmp_path)
    assert enriched["recommended_primary"]["command"] == "context"
    assert enriched["recommended_primary"]["args"]["domain"] == "骨科"
