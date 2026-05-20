"""CLI parser and JSON contract tests for annotation commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def vault(tmp_path):
    """Minimal vault with paperforge.json."""
    pf_json = tmp_path / "paperforge.json"
    pf_json.write_text('{"vault_config": {"system_dir": "99_System"}}', encoding="utf-8")
    return tmp_path


def _run_cli(vault: Path, args: list[str]):
    """Parse annotation subcommand args with vault_path injection."""
    import argparse
    from paperforge.cli import build_parser

    parser = build_parser()
    full_args = ["annotation", *args]
    ns = parser.parse_args(full_args)
    ns.vault_path = vault
    return ns


class TestParser:
    """Unit tests for argparse parsing only (no DB)."""

    def test_import(self, vault):
        ns = _run_cli(vault, ["import", "--dry-run"])
        assert ns.command == "annotation"
        assert ns.annotation_subcommand == "import"
        assert ns.dry_run is True

    def test_list(self, vault):
        ns = _run_cli(vault, ["list", "PAPER001", "--page", "2", "--json"])
        assert ns.annotation_subcommand == "list"
        assert ns.paper_key == "PAPER001"
        assert ns.page == 2
        assert ns.json is True

    def test_create(self, vault):
        ns = _run_cli(vault, [
            "create", "--paper", "PAPER001", "--type", "highlight",
            "--page-index", "3", "--selected-text", "foo", "--comment", "bar",
        ])
        assert ns.annotation_subcommand == "create"
        assert ns.paper == "PAPER001"
        assert ns.ann_type == "highlight"
        assert ns.page_index == 3

    def test_patch(self, vault):
        ns = _run_cli(vault, ["patch", "ann123", "--comment", "new"])
        assert ns.annotation_subcommand == "patch"
        assert ns.annotation_id == "ann123"
        assert ns.comment == "new"

    def test_delete(self, vault):
        ns = _run_cli(vault, ["delete", "ann123", "--hard"])
        assert ns.annotation_subcommand == "delete"
        assert ns.annotation_id == "ann123"
        assert ns.hard is True

    def test_export(self, vault):
        ns = _run_cli(vault, ["export", "PAPER001", "--format", "markdown"])
        assert ns.annotation_subcommand == "export"
        assert ns.paper_key == "PAPER001"

    def test_status(self, vault):
        ns = _run_cli(vault, ["status", "--json"])
        assert ns.annotation_subcommand == "status"

    def test_import_zotero_db_flag(self, vault):
        ns = _run_cli(vault, ["import", "--zotero-db", "/custom/path.sqlite"])
        assert ns.zotero_db == "/custom/path.sqlite"


class TestIntegration:
    """Tests that exercise commands against a real vault + annotations.db."""

    def test_status_json_envelope(self, vault):
        from paperforge.commands.annotation import run as ann_run
        from paperforge.cli import build_parser

        parser = build_parser()
        ns = parser.parse_args(["annotation", "status", "--json"])
        ns.vault_path = vault

        import io, sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            exit_code = ann_run(ns)
        finally:
            sys.stdout = old_stdout

        assert exit_code == 0
        output = json.loads(captured.getvalue())
        assert output["ok"] is True
        assert output["command"] == "annotation status"
        assert "data" in output
        assert output["data"]["db_exists"] is False

    def test_create_and_list(self, vault):
        """Create an annotation then list it."""
        from paperforge.commands.annotation import run as ann_run
        from paperforge.cli import build_parser

        def _run(sub_args: list[str]):
            parser = build_parser()
            ns = parser.parse_args(["annotation", *sub_args])
            ns.vault_path = vault
            import io, sys
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                code = ann_run(ns)
            finally:
                sys.stdout = old_stdout
            return code, captured.getvalue()

        # Create
        code, out = _run([
            "create", "--paper", "PAPER001", "--type", "highlight",
            "--page-index", "2", "--selected-text", "hello", "--json",
        ])
        assert code == 0
        created = json.loads(out)
        assert created["data"]["paper_id"] == "PAPER001"
        ann_id = created["data"]["id"]

        # List
        code, out = _run(["list", "PAPER001", "--json"])
        assert code == 0
        listed = json.loads(out)
        assert listed["data"]["count"] >= 1

        # Patch
        code, out = _run(["patch", ann_id, "--comment", "updated", "--json"])
        assert code == 0
        patched = json.loads(out)
        assert patched["data"]["comment"] == "updated"

        # Delete
        code, out = _run(["delete", ann_id, "--json"])
        assert code == 0
