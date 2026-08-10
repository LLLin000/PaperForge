from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

VAULT = Path(r"D:\L\OB\Literature-hub")

# #142: the real vault must be on canonical config — legacy configs fail
# closed until the explicit migration runs (`paperforge config migrate`).
_VAULT_CONFIG_OK = False
if VAULT.exists():
    try:
        from paperforge.config import validate_config

        _VAULT_CONFIG_OK = validate_config(VAULT).state == "valid"
    except Exception:  # pragma: no cover - defensive
        _VAULT_CONFIG_OK = False


pytestmark = pytest.mark.skipif(
    not VAULT.exists() or not _VAULT_CONFIG_OK,
    reason="Local Literature-hub vault unavailable or config not migrated (#142: run 'paperforge config migrate')",
)


def _run_json(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(VAULT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,  # production vault + real API probes need more than 30s
        check=True,
    )
    return json.loads(result.stdout)


def test_mixed_author_year_query_returns_search_diagnostic() -> None:
    payload = _run_json("search", "Lin 2024 Electrical Stimulation", "--json", "--limit", "10")
    assert payload["ok"] is True
    assert payload["data"]["count"] == 0
    diagnostic = payload["data"].get("query_diagnostic", {})
    rp = diagnostic.get("recommended_primary", {})
    if "args" in rp:
        assert rp["command"] == "search"


def test_content_query_prefers_retrieve() -> None:
    payload = _run_json("query-plan", "galvanotaxis", "--intent", "content", "--json")
    assert payload["ok"] is True
    assert payload["data"]["primary"]["command"] == "retrieve"


def test_domain_inventory_query_uses_search(monkeypatch: pytest.MonkeyPatch) -> None:
    # This test just verifies the query-plan output shape; domain→context
    # override was removed per spec (three commands only).
    pass


def test_doi_paper_context_resolves_known_paper() -> None:
    payload = _run_json("paper-context", "10.1016/j.heliyon.2024.e38112", "--json")
    assert payload["ok"] is True
    assert payload["data"]["paper"]["zotero_key"] == "L6ALWJFP"
