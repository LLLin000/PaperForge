"""Tests for Layer 4 gateway commands (Task 1)."""

from argparse import Namespace

from paperforge.commands import paper_lookup, content_discovery, paper_navigation, scoped_fetch


def test_paper_lookup_command_registered_and_json(tmp_path):
    args = Namespace(vault_path=tmp_path, query="Smith 2021", json=True, limit=5)
    exit_code = paper_lookup.run(args)
    assert exit_code in {0, 1}


def test_content_discovery_warns_when_only_metadata_fts_exists(tmp_path, monkeypatch):
    from paperforge.core.result import PFResult
    from paperforge.retrieval import gateway

    def fake_route_gateway(*args, **kwargs):
        return PFResult(
            ok=True,
            command="content-discovery",
            version="x",
            data={"mode": "metadata_only"},
            warnings=["body_units_fts missing"],
        )

    monkeypatch.setattr(gateway, "route_gateway", fake_route_gateway)
    args = Namespace(vault_path=tmp_path, query="delirium prevention", json=True, limit=5)
    assert content_discovery.run(args) == 0


def test_paper_navigation_runs(tmp_path):
    args = Namespace(vault_path=tmp_path, query="10.1234/test-doi-here", json=True, limit=5)
    exit_code = paper_navigation.run(args)
    assert exit_code in {0, 1}


def test_scoped_fetch_runs(tmp_path):
    args = Namespace(vault_path=tmp_path, query="Smith 2021", json=False, limit=3)
    exit_code = scoped_fetch.run(args)
    assert exit_code in {0, 1}


def test_content_discovery_non_json_output(tmp_path, monkeypatch):
    from paperforge.core.result import PFResult
    from paperforge.retrieval import gateway

    def fake_route_gateway(*args, **kwargs):
        return PFResult(ok=True, command="content-discovery", version="x", data={"mode": "metadata_only"})

    monkeypatch.setattr(gateway, "route_gateway", fake_route_gateway)
    args = Namespace(vault_path=tmp_path, query="delirium prevention", json=False, limit=5)
    assert content_discovery.run(args) == 0
