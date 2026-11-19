"""Unit tests for safe storage migration, rollback, idempotence, and workspace fulltext preservation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.config import ConfigError, load_config
from paperforge.services.storage_migration import migrate_vault_storage
from paperforge.worker.trash import list_trash, restore_trash
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


def test_modified_workspace_fulltext_is_preserved_in_trash_and_restorable(
    tmp_path: Path,
) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    old_pf = tmp_path / "System" / "PaperForge"
    lit_root = tmp_path / "Resources" / "Literature" / "Ortho"

    # Paper 1: byte-identical machine mirror -> safely removed directly
    ocr1 = old_pf / "ocr" / "MIR001"
    ocr1.mkdir(parents=True)
    mirror_bytes = b"# Machine OCR\n\nUnmodified text.\n"
    (ocr1 / "fulltext.md").write_bytes(mirror_bytes)
    ws1 = lit_root / "MIR001 - Mirror Study"
    ws1.mkdir(parents=True)
    (ws1 / "fulltext.md").write_bytes(mirror_bytes)

    # Paper 2: user-edited workspace fulltext -> preserved in .paperforge/trash/
    ocr2 = old_pf / "ocr" / "EDT002"
    ocr2.mkdir(parents=True)
    (ocr2 / "fulltext.md").write_text("# Original OCR\n", encoding="utf-8")
    ws2 = lit_root / "EDT002 - Edited Study"
    ws2.mkdir(parents=True)
    edited_bytes = b"# Original OCR\n\nUser handwritten notes that must not be lost!\n"
    (ws2 / "fulltext.md").write_bytes(edited_bytes)

    res = migrate_vault_storage(tmp_path, dry_run=False)
    assert res["config_updated"] is True
    assert res["workspace_fulltexts_removed"] == 2
    assert res["workspace_fulltexts_preserved"] == 1
    assert not (ws1 / "fulltext.md").exists()
    assert not (ws2 / "fulltext.md").exists()

    trash_entries = list_trash(tmp_path)
    preserved = [e for e in trash_entries if e.get("paper_key") == "EDT002"]
    assert len(preserved) == 1
    assert preserved[0]["operation"] == "workspace_fulltext_preserve"

    # Non-mirror user-edited copy can be restored losslessly from trash
    restored = restore_trash(tmp_path, preserved[0]["trash_id"])
    assert restored == (ws2 / "fulltext.md").resolve()
    assert (ws2 / "fulltext.md").read_bytes() == edited_bytes


def test_corrupt_config_aborts_migration_before_moving_files(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text("{corrupt json", encoding="utf-8")
    old_meta = tmp_path / "System" / "PaperForge" / "ocr" / "K1" / "meta.json"
    old_meta.parent.mkdir(parents=True)
    old_meta.write_text('{"zotero_key": "K1"}', encoding="utf-8")

    with pytest.raises(ConfigError):
        migrate_vault_storage(tmp_path, dry_run=False)

    # Nothing was moved or mutated before failing closed
    assert old_meta.exists()
    assert not (tmp_path / ".paperforge" / "ocr" / "K1").exists()


def test_config_commit_failure_rolls_back_moved_dirs_and_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    old_meta = tmp_path / "System" / "PaperForge" / "ocr" / "RB01" / "meta.json"
    old_meta.parent.mkdir(parents=True)
    old_meta.write_text('{"zotero_key": "RB01"}', encoding="utf-8")

    ws = tmp_path / "Resources" / "Literature" / "Ortho" / "RB01 - Rollback"
    ws.mkdir(parents=True)
    note = ws / "RB01.md"
    orig_note = "---\ntitle: Rollback\n---\n![[render/figures/figure_001.md]]\n"
    note.write_text(orig_note, encoding="utf-8")

    from paperforge.services import storage_migration

    def _boom(*_a, **_kw):
        raise ConfigError("config.validation_error", {"reason": "injected failure"})

    monkeypatch.setattr(storage_migration, "set_config", _boom)

    with pytest.raises(RuntimeError, match="rolled back"):
        migrate_vault_storage(tmp_path, dry_run=False)

    assert old_meta.exists()
    assert not (tmp_path / ".paperforge" / "ocr" / "RB01" / "meta.json").exists()
    assert note.read_text(encoding="utf-8") == orig_note
    journal = json.loads((tmp_path / ".paperforge" / ".migration-journal.json").read_text(encoding="utf-8"))
    assert journal["state"] == "rolled_back"


def test_interrupted_and_repeat_migration_is_idempotent(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    # Simulate an interrupted prior run where half the data already landed in .paperforge
    old_k1 = tmp_path / "System" / "PaperForge" / "ocr" / "PART1" / "meta.json"
    old_k1.parent.mkdir(parents=True)
    old_k1.write_text('{"zotero_key": "PART1"}', encoding="utf-8")

    already_k2 = tmp_path / ".paperforge" / "ocr" / "PART2" / "meta.json"
    already_k2.parent.mkdir(parents=True)
    already_k2.write_text('{"zotero_key": "PART2"}', encoding="utf-8")

    first = migrate_vault_storage(tmp_path, dry_run=False)
    assert first["config_updated"] is True
    assert (tmp_path / ".paperforge" / "ocr" / "PART1" / "meta.json").exists()
    assert already_k2.exists()
    assert load_config(tmp_path).values["system_dir"].value == ".paperforge"

    # Running a second time must be a safe, clean no-op
    second = migrate_vault_storage(tmp_path, dry_run=False)
    assert second["config_updated"] is True
    assert second["entries_moved"] == 0
    assert already_k2.exists()
