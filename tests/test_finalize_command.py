from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperforge.worker._utils import pipeline_paths
from tests.conftest import canonical_test_config

KEY = "FINAL123"


def _note_text(*, complete: bool) -> str:
    deep = (
        "## 🔍 精读\n\n"
        "- **Clarity**（清晰度）：方法和结论清楚。\n\n"
        "**Figure 导读**\n"
        "- Figure 1：展示研究流程。\n\n"
        "**遗留问题**\n"
        "- 外部队列验证仍需补充。\n"
        if complete
        else "## 🔍 精读\n\n（待补充）\n"
    )
    return (
        "---\n"
        f'zotero_key: "{KEY}"\n'
        'deep_reading_status: "pending"\n'
        "---\n\n"
        "# Finalize test\n\n"
        + deep
    )


def _make_vault(tmp_path: Path, *, complete: bool) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="CustomSystem")
    literature = pipeline_paths(vault)["literature"]
    note = literature / "domain" / f"{KEY} - Finalize test.md"
    note.parent.mkdir(parents=True)
    note.write_text(_note_text(complete=complete), encoding="utf-8")
    return vault, note


def _args(vault: Path) -> argparse.Namespace:
    return argparse.Namespace(
        vault=str(vault),
        vault_path=vault,
        zotero_key=KEY,
        json=True,
    )


def test_deep_finalize_updates_note_and_emits_one_json_result(tmp_path, monkeypatch, capsys):
    from paperforge.commands.finalize import run

    vault, note = _make_vault(tmp_path, complete=True)
    monkeypatch.setattr(
        "paperforge.worker.asset_index.refresh_index_entry",
        lambda _vault, _key: True,
    )

    assert run(_args(vault)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["content_validated"] is True
    assert payload["data"]["note_updated"] is True
    assert payload["data"]["index_refreshed"] is True
    assert 'deep_reading_status: "done"' in note.read_text(encoding="utf-8")


def test_deep_finalize_cli_dispatches_real_command(tmp_path, monkeypatch, capsys):
    from paperforge.cli import main

    vault, note = _make_vault(tmp_path, complete=True)
    monkeypatch.setattr(
        "paperforge.worker.asset_index.refresh_index_entry",
        lambda _vault, _key: True,
    )

    assert main(["--vault", str(vault), "deep-finalize", KEY, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "deep-finalize"
    assert payload["data"]["note_path"] == str(note.relative_to(vault)).replace("\\", "/")


def test_deep_finalize_refuses_incomplete_content_without_writing(tmp_path, monkeypatch, capsys):
    from paperforge.commands.finalize import run

    vault, note = _make_vault(tmp_path, complete=False)
    before = note.read_bytes()
    monkeypatch.setattr(
        "paperforge.worker.asset_index.refresh_index_entry",
        lambda _vault, _key: (_ for _ in ()).throw(AssertionError("index must not refresh")),
    )

    assert run(_args(vault)) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "incomplete" in payload["error"]["message"]
    assert note.read_bytes() == before
