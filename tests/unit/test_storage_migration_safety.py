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


def test_force_rebuild_and_single_entry_refresh_preserve_modified_fulltext_and_sibling_notes(
    tmp_path: Path,
) -> None:
    from paperforge.worker.asset_index import build_index, refresh_index_entry

    canonical_test_config(tmp_path, system_dir=".paperforge")
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "exports").mkdir(parents=True, exist_ok=True)
    ocr_dir = pf_dir / "ocr" / "RBFT01"
    ocr_dir.mkdir(parents=True, exist_ok=True)
    (ocr_dir / "fulltext.md").write_text("# Official OCR Text\n", encoding="utf-8")
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key": "RBFT01", "ocr_status": "done"}', encoding="utf-8"
    )
    (pf_dir / "exports" / "Ortho.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "key": "RBFT01",
                        "citationKey": "rbft2026",
                        "title": "Preserved Fulltext Study",
                        "date": "2026",
                        "publicationTitle": "J Bone",
                        "creators": [{"creatorType": "author", "lastName": "Lin"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert build_index(tmp_path) == 1
    domain_dir = tmp_path / "Resources" / "Literature" / "Ortho"
    ws = next(domain_dir.glob("RBFT01 - *"))

    # Sibling user note whose name shares the key prefix must not be touched
    sibling_note = domain_dir / "RBFT01_reading_scratch.md"
    sibling_note.write_text("# Keep me\n", encoding="utf-8")

    # Case 1: force_rebuild=True moves user-modified fulltext into trash (restorable)
    edited_rebuild = b"# Official OCR Text\n\nCustom user edits during rebuild.\n"
    (ws / "fulltext.md").write_bytes(edited_rebuild)
    assert build_index(tmp_path, force_rebuild=True) == 1
    assert not (ws / "fulltext.md").exists()
    assert sibling_note.read_text(encoding="utf-8") == "# Keep me\n"

    trashed_after_rebuild = [e for e in list_trash(tmp_path) if e.get("paper_key") == "RBFT01"]
    assert len(trashed_after_rebuild) == 1
    assert trashed_after_rebuild[0]["operation"] == "workspace_fulltext_preserve"
    first_trash_id = trashed_after_rebuild[0]["trash_id"]
    assert restore_trash(tmp_path, first_trash_id) == (ws / "fulltext.md").resolve()
    assert (ws / "fulltext.md").read_bytes() == edited_rebuild

    # Case 2: single-entry refresh_index_entry also preserves modified fulltext in trash
    edited_refresh = b"# Official OCR Text\n\nCustom user edits during refresh.\n"
    (ws / "fulltext.md").write_bytes(edited_refresh)
    assert refresh_index_entry(tmp_path, "RBFT01") is True
    assert not (ws / "fulltext.md").exists()
    assert sibling_note.read_text(encoding="utf-8") == "# Keep me\n"

    trashed_after_refresh = [
        e
        for e in list_trash(tmp_path)
        if e.get("paper_key") == "RBFT01" and e.get("trash_id") != first_trash_id
    ]
    assert len(trashed_after_refresh) == 1
    assert restore_trash(tmp_path, trashed_after_refresh[0]["trash_id"]) == (ws / "fulltext.md").resolve()
    assert (ws / "fulltext.md").read_bytes() == edited_refresh


def test_migration_fault_injection_rolls_back_on_nth_move_asset_note_or_journal_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from paperforge.services import storage_migration
    from paperforge.services.storage_migration import rollback_incomplete_migration

    # --- Fault 1: fail on 2nd tree entry move -> 1st move must roll back ---
    vault1 = tmp_path / "v1"
    vault1.mkdir()
    canonical_test_config(vault1, system_dir="System")
    m1 = vault1 / "System" / "PaperForge" / "ocr" / "A01" / "meta.json"
    m2 = vault1 / "System" / "PaperForge" / "indexes" / "state.json"
    m1.parent.mkdir(parents=True)
    m2.parent.mkdir(parents=True)
    m1.write_text('{"zotero_key": "A01"}', encoding="utf-8")
    m2.write_text('{"ok": true}', encoding="utf-8")

    orig_move = storage_migration.shutil.move
    forward_moves = 0

    def _fail_second_move(src: str, dst: str) -> str:
        nonlocal forward_moves
        if ".paperforge" in Path(dst).parts:
            forward_moves += 1
            if forward_moves >= 2:
                raise OSError("injected move failure")
        return orig_move(src, dst)

    monkeypatch.setattr(storage_migration.shutil, "move", _fail_second_move)
    with pytest.raises(RuntimeError, match="rolled back"):
        migrate_vault_storage(vault1, dry_run=False)
    monkeypatch.undo()
    assert m1.exists()
    assert m2.exists()
    assert load_config(vault1).values["system_dir"].value == "System"
    assert json.loads((vault1 / ".paperforge" / ".migration-journal.json").read_text(encoding="utf-8"))["state"] == "rolled_back"

    # --- Fault 2: fail on 2nd visual asset materialization -> 1st asset & moved dir roll back ---
    vault2 = tmp_path / "v2"
    vault2.mkdir()
    canonical_test_config(vault2, system_dir="System")
    for k in ("B01", "B02"):
        fig = vault2 / "System" / "PaperForge" / "ocr" / k / "assets" / "figures" / "figure_001.jpg"
        fig.parent.mkdir(parents=True)
        fig.write_bytes(k.encode())
        ws = vault2 / "Resources" / "Literature" / "Ortho" / f"{k} - Paper"
        ws.mkdir(parents=True)

    orig_sync_assets = storage_migration.sync_workspace_visual_assets
    asset_calls = 0

    def _fail_second_asset(paper_ocr_dir: Path, ws_dir: Path, key: str) -> list[str]:
        nonlocal asset_calls
        asset_calls += 1
        if asset_calls == 2:
            raise OSError("disk full during asset copy")
        return orig_sync_assets(paper_ocr_dir, ws_dir, key)

    monkeypatch.setattr(storage_migration, "sync_workspace_visual_assets", _fail_second_asset)
    with pytest.raises(RuntimeError, match="rolled back"):
        migrate_vault_storage(vault2, dry_run=False)
    monkeypatch.undo()
    assert not (
        vault2 / "Resources" / "Literature" / "Ortho" / "B01 - Paper" / "assets" / "B01_figure_001.jpg"
    ).exists()
    assert (vault2 / "System" / "PaperForge" / "ocr" / "B01" / "assets" / "figures" / "figure_001.jpg").exists()

    # --- Fault 3: fail on 2nd note rewrite -> 1st note restored cleanly ---
    vault3 = tmp_path / "v3"
    vault3.mkdir()
    canonical_test_config(vault3, system_dir="System")
    notes_orig: dict[Path, str] = {}
    for k in ("C01", "C02"):
        ws = vault3 / "Resources" / "Literature" / "Ortho" / f"{k} - Paper"
        ws.mkdir(parents=True)
        n = ws / f"{k}.md"
        txt = f"---\ntitle: {k}\n---\n![[render/figures/figure_001.md]]\n"
        n.write_text(txt, encoding="utf-8")
        notes_orig[n] = txt
    (vault3 / "System" / "PaperForge" / "ocr" / "C01").mkdir(parents=True)

    orig_write_text = storage_migration.write_text_atomic
    write_calls = 0

    def _fail_second_note(path: Path, text: str) -> None:
        nonlocal write_calls
        write_calls += 1
        if write_calls == 2:
            raise OSError("injected note write failure")
        orig_write_text(path, text)

    monkeypatch.setattr(storage_migration, "write_text_atomic", _fail_second_note)
    with pytest.raises(RuntimeError, match="rolled back"):
        migrate_vault_storage(vault3, dry_run=False)
    monkeypatch.undo()
    for note_p, expected_txt in notes_orig.items():
        assert note_p.read_text(encoding="utf-8") == expected_txt

    # --- Fault 4: hard-crash journal recovery via rollback_incomplete_migration() ---
    vault4 = tmp_path / "v4"
    vault4.mkdir()
    canonical_test_config(vault4, system_dir="System")
    src_meta = vault4 / "System" / "PaperForge" / "ocr" / "D01" / "meta.json"
    dst_meta = vault4 / ".paperforge" / "ocr" / "D01" / "meta.json"
    dst_meta.parent.mkdir(parents=True)
    dst_meta.write_text('{"zotero_key": "D01"}', encoding="utf-8")
    ws4_note = vault4 / "Resources" / "Literature" / "Ortho" / "D01 - Paper" / "D01.md"
    ws4_note.parent.mkdir(parents=True)
    ws4_note.write_text("![[D01_figure_001.jpg]]\n", encoding="utf-8")
    journal4 = vault4 / ".paperforge" / ".migration-journal.json"
    journal4.write_text(
        json.dumps(
            {
                "state": "in_progress",
                "previous_system_dir": "System",
                "moved_pairs": [{"src": str(src_meta.parent), "dst": str(dst_meta.parent)}],
                "rewritten_notes": [
                    {"path": str(ws4_note), "original_text": "![[render/figures/figure_001.md]]\n"}
                ],
                "created_assets": [],
            }
        ),
        encoding="utf-8",
    )

    rec = rollback_incomplete_migration(vault4)
    assert rec["recovered"] is True
    assert rec["state"] == "rolled_back"
    assert src_meta.exists()
    assert not dst_meta.exists()
    assert ws4_note.read_text(encoding="utf-8") == "![[render/figures/figure_001.md]]\n"
    assert json.loads(journal4.read_text(encoding="utf-8"))["state"] == "rolled_back"


def test_full_upgrade_promotes_isolated_paper_errors_to_partial_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When isolate_paper_errors=True hits a per-paper failure, journal & upgrade settle as partial_success
    and promote the paper error into top-level `errors` instead of silently reporting completed."""
    from paperforge.services import storage_migration
    from paperforge.services.vault_upgrade import execute_vault_upgrade

    vault = tmp_path / "v_partial"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")
    for k in ("P01", "P02"):
        fig = vault / "System" / "PaperForge" / "ocr" / k / "assets" / "figures" / "figure_001.jpg"
        fig.parent.mkdir(parents=True)
        fig.write_bytes(k.encode())
        ws = vault / "Resources" / "Literature" / "Ortho" / f"{k} - Paper"
        ws.mkdir(parents=True)
        (ws / f"{k}.md").write_text(f"---\nzotero_key: {k}\n---\n![[render/figures/figure_001.md]]\n", encoding="utf-8")

    orig_cleanup = storage_migration.cleanup_or_preserve_workspace_fulltext

    def _fail_p02(ws_dir: Path, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs.get("paper_key") == "P02":
            raise OSError("simulated locked fulltext for P02")
        return orig_cleanup(ws_dir, **kwargs)

    monkeypatch.setattr(storage_migration, "cleanup_or_preserve_workspace_fulltext", _fail_p02)
    # 1. Verify migrate_vault_storage rolls back P02's partial note rewrite on per-paper failure
    sres = migrate_vault_storage(vault, dry_run=False, isolate_paper_errors=True)
    assert sres["state"] == "partial_success"
    assert len(sres["paper_errors"]) == 1
    assert sres["paper_errors"][0]["key"] == "P02"
    p02_note = (vault / "Resources" / "Literature" / "Ortho" / "P02 - Paper" / "P02.md").read_text(encoding="utf-8")
    assert "render/figures/figure_001.md" in p02_note

    # 2. Verify execute_vault_upgrade promotes isolated paper errors into top-level `errors` & `partial_success`
    vault2 = tmp_path / "v_partial_upgrade"
    vault2.mkdir()
    canonical_test_config(vault2, system_dir="System")
    for k in ("P01", "P02"):
        fig = vault2 / "System" / "PaperForge" / "ocr" / k / "assets" / "figures" / "figure_001.jpg"
        fig.parent.mkdir(parents=True)
        fig.write_bytes(k.encode())
        ws = vault2 / "Resources" / "Literature" / "Ortho" / f"{k} - Paper"
        ws.mkdir(parents=True)
        (ws / f"{k}.md").write_text(f"---\nzotero_key: {k}\n---\n![[render/figures/figure_001.md]]\n", encoding="utf-8")

    res = execute_vault_upgrade(vault2, dry_run=False, fast_cutover=False, rebuild_db=False)
    monkeypatch.undo()

    assert res["applied"] is True
    assert res["status"] == "partial_success"
    assert any("P02" in str(e.get("step", "")) for e in res["errors"])
    journal = json.loads((vault2 / ".paperforge" / ".migration-journal.json").read_text(encoding="utf-8"))
    assert journal["state"] == "partial_success"
    assert len(journal["paper_errors"]) == 1


def test_zotero_online_backup_snapshot_is_consistent_under_concurrent_wal_writes(tmp_path: Path) -> None:
    """SQLite Online Backup API captures a transactionally consistent snapshot while a live writer
    continuously mutates and checkpoints a WAL-mode zotero.sqlite, without altering the source DB."""
    import sqlite3
    import threading
    import time

    from paperforge.adapters.zotero_sqlite import open_zotero_snapshot_ro

    zdir = tmp_path / "Zotero"
    zdir.mkdir()
    db_path = zdir / "zotero.sqlite"

    init_conn = sqlite3.connect(str(db_path))
    init_conn.execute("PRAGMA journal_mode=WAL")
    init_conn.execute("CREATE TABLE items (itemID INTEGER PRIMARY KEY, key TEXT, batch INTEGER)")
    init_conn.executemany("INSERT INTO items VALUES (?, ?, 0)", [(i, f"K{i:04d}") for i in range(1, 51)])
    init_conn.commit()
    init_conn.close()

    stop_ev = threading.Event()
    writer_errors: list[Exception] = []

    def _writer() -> None:
        w = sqlite3.connect(str(db_path), timeout=5.0)
        try:
            batch = 1
            while not stop_ev.is_set() and batch <= 40:
                w.execute("BEGIN IMMEDIATE")
                # Every committed transaction inserts an atomic pair sharing the same batch id
                base = batch * 100
                w.execute("INSERT INTO items VALUES (?, ?, ?)", (base + 1, f"B{batch}_A", batch))
                w.execute("INSERT INTO items VALUES (?, ?, ?)", (base + 2, f"B{batch}_B", batch))
                w.commit()
                if batch % 5 == 0:
                    w.execute("PRAGMA wal_checkpoint(PASSIVE)")
                batch += 1
                time.sleep(0.005)
        except Exception as exc:  # noqa: BLE001
            writer_errors.append(exc)
        finally:
            w.close()

    t = threading.Thread(target=_writer, daemon=True)
    t.start()
    try:
        for _ in range(5):
            with open_zotero_snapshot_ro(zdir) as (snap_conn, _):
                qc = snap_conn.execute("PRAGMA quick_check").fetchone()
                assert qc and str(qc[0]).lower() == "ok"
                # Every non-zero batch seen in the snapshot MUST have both rows (no torn transaction!)
                counts = snap_conn.execute(
                    "SELECT batch, COUNT(*) FROM items WHERE batch > 0 GROUP BY batch"
                ).fetchall()
                for row in counts:
                    assert row[1] == 2, f"Torn transaction detected for batch {row[0]}: count={row[1]}"
            time.sleep(0.01)
    finally:
        stop_ev.set()
        t.join(timeout=5.0)

    assert not writer_errors, f"Writer failed: {writer_errors}"


def test_rollback_incomplete_migration_rejects_out_of_vault_paths(tmp_path: Path) -> None:
    """PF-SEC-008: tampered .migration-journal.json paths outside vault_root must fail closed."""
    from paperforge.services.storage_migration import rollback_incomplete_migration
    from paperforge.worker.trash import DangerousPathError

    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("sensitive", encoding="utf-8")

    journal = vault / ".paperforge" / ".migration-journal.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        json.dumps(
            {
                "state": "in_progress",
                "moved_pairs": [],
                "rewritten_notes": [{"path": str(vault / ".." / "outside.txt"), "original_text": "pwned"}],
                "created_assets": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(DangerousPathError):
        rollback_incomplete_migration(vault)
    assert outside.read_text(encoding="utf-8") == "sensitive"
