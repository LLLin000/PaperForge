"""Regression tests for PaperForge 2.0.13 backend sync authorization & migration recovery."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from paperforge.adapters.zotero_sqlite import ZoteroScopeInvalidError, ZoteroScopeRequiredError
from paperforge.config import load_config, set_config
from paperforge.core.errors import ErrorCode
from paperforge.services.sync_service import SyncService
from paperforge.services.vault_engine import (
    VaultOperationLock,
    ensure_current_vault_manifest,
    read_vault_manifest,
    write_vault_manifest,
)
from paperforge.services.vault_upgrade import (
    detect_vault_provenance,
    execute_vault_upgrade,
    heal_vault_progressive,
    inspect_vault_upgrade,
    rollback_vault_upgrade,
)
from tests.conftest import canonical_test_config


def _create_two_collection_zotero_dir(base: Path) -> Path:
    zdir = base / "ZoteroData"
    zdir.mkdir(parents=True, exist_ok=True)
    for att_key, pdf_name in (("ATT00001", "hydrogel.pdf"), ("ATT00002", "biomech.pdf")):
        st = zdir / "storage" / att_key
        st.mkdir(parents=True, exist_ok=True)
        (st / pdf_name).write_bytes(b"%PDF-1.4\n%mock\n")

    conn = sqlite3.connect(str(zdir / "zotero.sqlite"))
    conn.executescript(
        """
        CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT);
        CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INTEGER, key TEXT);
        CREATE TABLE deletedItems (itemID INTEGER PRIMARY KEY);
        CREATE TABLE fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT);
        CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value TEXT);
        CREATE TABLE itemData (itemID INTEGER, fieldID INTEGER, valueID INTEGER);
        CREATE TABLE creators (creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT, fieldMode INTEGER);
        CREATE TABLE creatorTypes (creatorTypeID INTEGER PRIMARY KEY, creatorType TEXT);
        CREATE TABLE itemCreators (itemID INTEGER, creatorID INTEGER, creatorTypeID INTEGER, orderIndex INTEGER);
        CREATE TABLE collections (collectionID INTEGER PRIMARY KEY, collectionName TEXT, parentCollectionID INTEGER, key TEXT);
        CREATE TABLE deletedCollections (collectionID INTEGER PRIMARY KEY);
        CREATE TABLE collectionItems (collectionID INTEGER, itemID INTEGER);
        CREATE TABLE itemAttachments (itemID INTEGER PRIMARY KEY, parentItemID INTEGER, linkMode INTEGER, contentType TEXT, path TEXT);

        INSERT INTO itemTypes VALUES (1, 'journalArticle'), (2, 'attachment');
        INSERT INTO items VALUES
            (10, 1, 'ZOTKEY01'), (11, 2, 'ATT00001'),
            (20, 1, 'ZOTKEY02'), (21, 2, 'ATT00002');

        INSERT INTO fields VALUES (1, 'title'), (2, 'date'), (3, 'citationKey');
        INSERT INTO itemDataValues VALUES
            (1, 'Cartilage Hydrogel Scaffolds'),
            (2, '2025-04-01'),
            (3, 'linCartilage2025'),
            (4, 'Rotator Cuff Fixation'),
            (5, '2025-05-01'),
            (6, 'linRotator2025');
        INSERT INTO itemData VALUES
            (10,1,1), (10,2,2), (10,3,3),
            (20,1,4), (20,2,5), (20,3,6);

        INSERT INTO creatorTypes VALUES (1, 'author');
        INSERT INTO creators VALUES (1, 'Wei', 'Lin', 0);
        INSERT INTO itemCreators VALUES (10, 1, 1, 0), (20, 1, 1, 0);

        INSERT INTO collections VALUES
            (100, 'BoneRegen', NULL, 'COLTOP01'),
            (200, 'SportsMed', NULL, 'COL_SPRT');
        INSERT INTO collectionItems VALUES (100, 10), (200, 20);

        INSERT INTO itemAttachments VALUES
            (11, 10, 0, 'application/pdf', 'storage:hydrogel.pdf'),
            (21, 20, 0, 'application/pdf', 'storage:biomech.pdf');
        """
    )
    conn.commit()
    conn.close()
    return zdir


def _run_cli(vault: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _setup_modern_vault(tmp_path: Path, zdir: Path, selected: str) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(
        vault,
        system_dir=".paperforge",
        zotero_data_dir=str(zdir),
        zotero_source_mode="sqlite",
        domain_mode="per_collection",
        zotero_selected_collections=selected,
    )
    return vault


def test_sqlite_empty_or_missing_scope_rejected_with_zero_writes(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    for bad_sel in ("", "[]"):
        sub = tmp_path / ("empty" if bad_sel == "" else "brackets")
        sub.mkdir()
        vault = _setup_modern_vault(sub, zdir, bad_sel)
        res = SyncService(vault).run(json_output=True)
        assert res.ok is False
        assert res.error is not None
        assert res.error.code == ErrorCode.ZOTERO_SCOPE_REQUIRED
        assert not list((vault / ".paperforge" / "exports").glob("*.json"))
        assert not (vault / "Resources" / "Literature").exists()

    # CLI also enforces the exact same contract cleanly
    cli_proc = _run_cli(tmp_path / "empty" / "vault", "sync", "--json")
    assert cli_proc.returncode == 1
    payload = json.loads(cli_proc.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == ErrorCode.ZOTERO_SCOPE_REQUIRED.value


def test_sqlite_explicit_wildcard_and_cli_all_collections_succeed(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)

    v1 = _setup_modern_vault(tmp_path / "wild", zdir, '["*"]')
    res1 = SyncService(v1).run(json_output=True)
    assert res1.ok is True
    assert (v1 / ".paperforge" / "exports" / "BoneRegen.json").is_file()
    assert (v1 / ".paperforge" / "exports" / "SportsMed.json").is_file()

    (tmp_path / "cli_all").mkdir()
    v2 = _setup_modern_vault(tmp_path / "cli_all", zdir, "")
    proc = _run_cli(v2, "sync", "--all-collections", "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert (v2 / ".paperforge" / "exports" / "BoneRegen.json").is_file()
    assert (v2 / ".paperforge" / "exports" / "SportsMed.json").is_file()


def test_sqlite_specific_collection_exports_only_authorized_slice(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = _setup_modern_vault(tmp_path, zdir, '["COLTOP01"]')
    res = SyncService(vault).run(json_output=True)
    assert res.ok is True
    assert (vault / ".paperforge" / "exports" / "BoneRegen.json").is_file()
    assert not (vault / ".paperforge" / "exports" / "SportsMed.json").exists()
    assert (vault / "Resources" / "Literature" / "BoneRegen").is_dir()
    assert not (vault / "Resources" / "Literature" / "SportsMed").exists()


def test_sqlite_invalid_or_expired_collection_key_fails_closed(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = _setup_modern_vault(tmp_path, zdir, '["EXPIRED_COL_KEY"]')
    res = SyncService(vault).run(json_output=True)
    assert res.ok is False
    assert res.error is not None
    assert res.error.code == ErrorCode.ZOTERO_SCOPE_INVALID
    assert not list((vault / ".paperforge" / "exports").glob("*.json"))


def test_unmigrated_veteran_legacy_and_rescue_rejected_zero_writes(tmp_path: Path) -> None:
    # (a) veteran_legacy: System/PaperForge + paperforge.json, no vault-manifest.json
    zdir = _create_two_collection_zotero_dir(tmp_path)
    leg = tmp_path / "legacy"
    (leg / "System" / "PaperForge" / "exports").mkdir(parents=True)
    canonical_test_config(
        leg,
        system_dir="System",
        zotero_data_dir=str(zdir),
        zotero_selected_collections='["*"]',
    )
    assert detect_vault_provenance(leg)["state"] == "veteran_legacy"

    res_leg = SyncService(leg).run(json_output=True)
    assert res_leg.ok is False
    assert res_leg.error is not None
    assert res_leg.error.code == ErrorCode.VAULT_UPGRADE_REQUIRED
    assert not (leg / ".paperforge").exists()

    cli_leg = _run_cli(leg, "sync", "--json")
    assert cli_leg.returncode == 1
    assert json.loads(cli_leg.stdout)["error"]["code"] == ErrorCode.VAULT_UPGRADE_REQUIRED.value
    assert not (leg / ".paperforge").exists()

    # (b) veteran_rescue: 4-key PaperForge note without paperforge.json or .paperforge
    rescue = tmp_path / "rescue"
    note_dir = rescue / "Resources" / "Literature" / "Ortho" / "ZOT00001 - Paper"
    note_dir.mkdir(parents=True)
    (note_dir / "ZOT00001.md").write_text(
        "---\nzotero_key: ZOT00001\nocr_status: done\ndeep_reading_status: pending\ndo_ocr: false\n---\n",
        encoding="utf-8",
    )
    assert detect_vault_provenance(rescue)["state"] == "veteran_rescue"
    res_rescue = SyncService(rescue).run(json_output=True)
    assert res_rescue.ok is False
    assert res_rescue.error is not None
    assert res_rescue.error.code == ErrorCode.VAULT_UPGRADE_REQUIRED
    assert not (rescue / ".paperforge").exists()


def test_interrupted_cutover_migration_journal_rejects_sync(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = _setup_modern_vault(tmp_path, zdir, '["COLTOP01"]')
    (vault / ".paperforge" / ".migration-journal.json").write_text(
        json.dumps({"state": "in_progress", "mode": "fast_cutover"}),
        encoding="utf-8",
    )
    res = SyncService(vault).run(json_output=True)
    assert res.ok is False
    assert res.error is not None
    assert res.error.code == ErrorCode.VAULT_UPGRADE_REQUIRED


def test_vault_operation_lock_contention_returns_structured_codes(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = _setup_modern_vault(tmp_path, zdir, '["COLTOP01"]')

    for op, expected_code in (
        ("upgrade.heal", ErrorCode.VAULT_HEALING_IN_PROGRESS),
        ("upgrade.cutover", ErrorCode.OPERATION_CONFLICT),
    ):
        acquired = threading.Event()
        release = threading.Event()

        def _hold() -> None:
            with VaultOperationLock(vault, operation=op, timeout=2.0, create_dir=True):
                acquired.set()
                release.wait(timeout=10.0)

        t = threading.Thread(target=_hold, daemon=True)
        t.start()
        assert acquired.wait(timeout=5.0)
        try:
            res = SyncService(vault).run(json_output=True)
            assert res.ok is False
            assert res.error is not None
            assert res.error.code == expected_code
        finally:
            release.set()
            t.join(timeout=5.0)


def test_heal_pending_blocks_sync_until_heal_cletes_then_clears_flags(tmp_path: Path) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = _setup_modern_vault(tmp_path, zdir, '["COLTOP01"]')
    write_vault_manifest(vault, heal_pending=True, post_upgrade_sync_pending=True)

    blocked = SyncService(vault).run(json_output=True)
    assert blocked.ok is False
    assert blocked.error is not None
    assert blocked.error.code == ErrorCode.VAULT_HEALING_IN_PROGRESS

    heal_vault_progressive(vault)
    mf_after_heal = read_vault_manifest(vault)
    assert mf_after_heal is not None
    assert mf_after_heal.get("heal_pending") is False

    synced = SyncService(vault).run(json_output=True)
    assert synced.ok is True
    mf_after_sync = read_vault_manifest(vault)
    assert mf_after_sync is not None
    assert mf_after_sync.get("post_upgrade_sync_pending") is False


def test_atomic_cutover_commits_zotero_config_and_crash_before_manifest_stays_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = tmp_path / "vault"
    (vault / "System" / "PaperForge" / "exports").mkdir(parents=True)
    canonical_test_config(
        vault,
        system_dir="System",
        zotero_source_mode="bbt",
        zotero_selected_collections="",
    )

    # 1. Crash before write_vault_manifest -> must STILL require upgrade (never half-standard)
    monkeypatch.setattr(
        "paperforge.services.vault_engine.write_vault_manifest",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("simulated crash")),
    )
    res_crash = execute_vault_upgrade(
        vault,
        dry_run=False,
        fast_cutover=True,
        zotero_source_mode="sqlite",
        zotero_selected_collections='["COLTOP01"]',
        zotero_data_dir=str(zdir),
    )
    assert any(e["step"] == "write_vault_manifest" for e in res_crash["errors"])
    assert detect_vault_provenance(vault)["needs_upgrade"] is True

    # Restore write_vault_manifest and run cleanly on a fresh legacy vault
    monkeypatch.undo()
    v2 = tmp_path / "vault2"
    (v2 / "System" / "PaperForge" / "exports").mkdir(parents=True)
    canonical_test_config(
        v2,
        system_dir="System",
        zotero_source_mode="bbt",
        zotero_selected_collections="",
    )
    res_ok = execute_vault_upgrade(
        v2,
        dry_run=False,
        fast_cutover=True,
        zotero_source_mode="sqlite",
        zotero_selected_collections='["COLTOP01"]',
        zotero_data_dir=str(zdir),
    )
    assert res_ok["applied"] is True
    assert not res_ok["errors"]
    assert any(s.get("step") == "zotero_config_commit" for s in res_ok["executed_steps"])

    snap_cfg = json.loads((Path(res_ok["backup_dir"]) / "paperforge.json").read_text(encoding="utf-8"))
    assert snap_cfg.get("zotero_source_mode") == "bbt"

    live_snap = load_config(v2)
    assert live_snap.values["zotero_source_mode"].value == "sqlite"
    assert live_snap.values["zotero_selected_collections"].value == '["COLTOP01"]'
    assert live_snap.values["zotero_data_dir"].value == str(zdir)

    plan = inspect_vault_upgrade(v2, fast_summary=True)
    assert plan["provenance"]["needs_upgrade"] is False
    assert plan["manifest_state"]["heal_pending"] is True
    assert plan["manifest_state"]["post_upgrade_sync_pending"] is True


def test_rollback_restores_pre_upgrade_config_and_preserves_post_cutover_user_data(
    tmp_path: Path,
) -> None:
    zdir = _create_two_collection_zotero_dir(tmp_path)
    vault = tmp_path / "vault"
    (vault / "System" / "PaperForge" / "exports").mkdir(parents=True)
    ws_dir = vault / "Resources" / "Literature" / "BoneRegen" / "ZOTKEY01 - Cartilage Hydrogel Scaffolds"
    ws_dir.mkdir(parents=True)
    note_path = ws_dir / "ZOTKEY01.md"
    note_path.write_text("---\nzotero_key: ZOTKEY01\n---\n\n# Initial Note\n", encoding="utf-8")

    plugin_data = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    plugin_data.parent.mkdir(parents=True, exist_ok=True)
    orig_plugin_data = json.dumps({"zotero_source_mode": "bbt", "_setup_complete": True})
    plugin_data.write_text(orig_plugin_data, encoding="utf-8")

    canonical_test_config(vault, system_dir="System", zotero_source_mode="bbt")

    up_res = execute_vault_upgrade(
        vault,
        dry_run=False,
        fast_cutover=True,
        zotero_source_mode="sqlite",
        zotero_selected_collections='["COLTOP01"]',
        zotero_data_dir=str(zdir),
    )
    assert up_res["applied"] is True and not up_res["errors"]

    # Simulate user adding research notes & annotations after upgrade
    edited_note = "---\nzotero_key: ZOTKEY01\n---\n\n# Initial Note\n\n## My New Clinical Thought\n"
    note_path.write_text(edited_note, encoding="utf-8")
    ann_path = ws_dir / "annotations.jsonl"
    ann_content = json.dumps({"id": "ann_1", "page": 1, "comment": "Keep forever"}) + "\n"
    ann_path.write_text(ann_content, encoding="utf-8")

    rb = rollback_vault_upgrade(vault)
    assert rb["rolled_back"] is True

    restored_cfg = load_config(vault)
    assert restored_cfg.values["system_dir"].value == "System"
    assert restored_cfg.values["zotero_source_mode"].value == "bbt"
    assert plugin_data.read_text(encoding="utf-8") == orig_plugin_data
    assert (vault / "System" / "PaperForge" / "exports").is_dir()
    assert detect_vault_provenance(vault)["needs_upgrade"] is True

    # User note edit + sidecar annotations MUST remain 100% intact
    assert note_path.read_text(encoding="utf-8") == edited_note
    assert ann_path.read_text(encoding="utf-8") == ann_content


def test_fast_cutover_skips_sync_reconcile_and_quarantine_only_never_triggers_cutover(
    tmp_path: Path, monkeypatch
) -> None:
    """v2.0.14 regression:
    1. `fast_cutover=True` leaves `ensure_vault_reconciled` to background `upgrade.heal` (keeps cutover O(1)).
    2. `quarantine_only=True` moves ONLY selected residuals to `.paperforge/trash/` without running storage cutover.
    """
    from paperforge.services.storage_migration import _files_same_content
    from paperforge.services.vault_upgrade import detect_vault_provenance, execute_vault_upgrade

    vault = tmp_path / "veteran"
    (vault / "System" / "PaperForge" / "indexes").mkdir(parents=True)
    skill_dir = vault / ".agents" / "skills" / "paperforge"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Old skill copy\n", encoding="utf-8")
    canonical_test_config(vault, system_dir="System")

    # 1. quarantine_only=True must quarantine ONLY the chosen candidate without cutting over System/PaperForge
    plan = inspect_vault_upgrade(vault, fast_summary=False)
    skill_cands = [c for c in plan["cleanup_candidates"] if "skill" in c["id"]]
    assert skill_cands, "Expected vault-local skill copy as cleanup candidate"

    q_res = execute_vault_upgrade(
        vault,
        dry_run=False,
        quarantine_only=True,
        quarantine_ids=[skill_cands[0]["id"]],
    )
    assert q_res["applied"] is True
    assert q_res["mode"] == "quarantine_only"
    assert q_res["executed_steps"] == [{"step": "quarantine_residuals", "quarantined": 1}]
    assert not skill_dir.exists()
    assert (vault / "System" / "PaperForge").is_dir()
    assert detect_vault_provenance(vault)["needs_upgrade"] is True

    # 2. fast_cutover=True must NOT invoke heavy synchronous ensure_vault_reconciled
    called_reconcile = []
    monkeypatch.setattr(
        "paperforge.services.upgrade_reconcile.ensure_vault_reconciled",
        lambda *_args, **_kwargs: called_reconcile.append(True) or {},
    )
    up_res = execute_vault_upgrade(vault, dry_run=False, fast_cutover=True)
    assert up_res["applied"] is True
    assert called_reconcile == []

    # 3. Streaming content compare distinguishes equal vs different files without loading whole files
    fa = tmp_path / "a.bin"
    fb = tmp_path / "b.bin"
    fc = tmp_path / "c.bin"
    fa.write_bytes(b"hello-paperforge" * 1024)
    fb.write_bytes(b"hello-paperforge" * 1024)
    fc.write_bytes(b"hello-different" * 1024)
    assert _files_same_content(fa, fb, chunk_bytes=128) is True
    assert _files_same_content(fa, fc, chunk_bytes=128) is False
