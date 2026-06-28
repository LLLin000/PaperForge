from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

VAULT = Path(r"D:\L\OB\Literature-hub")


pytestmark = pytest.mark.skipif(not VAULT.exists(), reason="Local Literature-hub vault not available")


def _run_json(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(VAULT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def test_mixed_author_year_query_returns_search_diagnostic() -> None:
    payload = _run_json("search", "Lin 2024 Electrical Stimulation", "--json", "--limit", "10")
    assert payload["ok"] is True
    assert payload["data"]["count"] == 0
    diagnostic = payload["data"]["query_diagnostic"]
    assert diagnostic["query_class"] == "mixed_query"
    assert diagnostic["recommended_primary"]["args"]["query"] == "Lin"
    assert diagnostic["recommended_primary"]["args"]["year_from"] == 2024


def test_content_query_prefers_retrieve() -> None:
    payload = _run_json("query-plan", "galvanotaxis", "--intent", "content", "--json")
    assert payload["ok"] is True
    assert payload["data"]["recommended_primary"]["command"] == "retrieve"


def test_domain_inventory_query_prefers_context() -> None:
    payload = _run_json("query-plan", "骨科 里有什么", "--intent", "discover", "--json")
    assert payload["ok"] is True
    assert payload["data"]["recommended_primary"]["command"] == "context"
    assert payload["data"]["recommended_primary"]["args"]["domain"] == "骨科"


def test_doi_paper_context_resolves_known_paper() -> None:
    payload = _run_json("paper-context", "10.1016/j.heliyon.2024.e38112", "--json")
    assert payload["ok"] is True
    assert payload["data"]["paper"]["zotero_key"] == "L6ALWJFP"
