"""PBAF v2.1 Chaos, Recovery Drill, Concurrency, Cross-OS & Retention Tests."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import time
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.conftest import canonical_test_config

pytestmark = pytest.mark.chaos


def _assert_isolated(vault: Path) -> None:
    low = str(vault).lower()
    assert any(tok in low for tok in ("tmp", "temp")), f"Vault must reside in tmp: {vault}"


def test_p12_upgrade_mid_cutover_failure_triggers_full_rollback_and_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restore drill: mid-upgrade failure auto-rolls back legacy DB, config, and JSONL logs losslessly."""
    from paperforge.memory.db import get_connection
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.vault_upgrade import execute_vault_upgrade

    vault = tmp_path / "vault_drill"
    vault.mkdir(parents=True)
    _assert_isolated(vault)
    canonical_test_config(vault, system_dir="System")

    old_pf = vault / "System" / "PaperForge"
    (old_pf / "indexes").mkdir(parents=True)
    (old_pf / "memory").mkdir(parents=True)
    (vault / "Resources" / "Literature" / "Ortho" / "DRIL0001 - Paper").mkdir(parents=True)
    (vault / "Resources" / "Literature" / "Ortho" / "DRIL0001 - Paper" / "DRIL0001.md").write_text(
        '---\nzotero_key: "DRIL0001"\ntitle: "Restore Drill Paper"\n---\n\nUser note body.\n',
        encoding="utf-8",
    )

    legacy_db = old_pf / "indexes" / "paperforge.db"
    conn = get_connection(legacy_db)
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO papers(zotero_key, citation_key, title) VALUES (?, ?, ?)",
            ("DRIL0001", "dril2026", "Restore Drill Paper"),
        )
        conn.execute(
            "INSERT INTO reading_log(id, paper_id, section, excerpt, usage, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "rl-drill-1",
                "DRIL0001",
                "Methods",
                "Tier-0 immutable insight",
                "primary",
                "Verified user insight",
                "2026-11-28T00:00:00Z",
            ),
        )
        conn.execute(
            "INSERT INTO body_units(unit_id, paper_id, section_path, unit_text, page_span_json, "
            "block_span_json, token_estimate, indexable, veto_reason, quality_hints_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("DRIL0001:b:1", "DRIL0001", "Methods", "randomized trial outcome", "[1]", "[0]", 4, 1, "", "[]"),
        )
        conn.commit()
    finally:
        conn.close()

    pre_reading_log = '{"paper_id":"DRIL0001","entry_type":"note","content":"important"}\n'
    (old_pf / "memory" / "reading-log.jsonl").write_text(pre_reading_log, encoding="utf-8")
    pre_cfg = (vault / "paperforge.json").read_text(encoding="utf-8")

    # Force post-cutover G4 verification failure to exercise automatic rollback
    import paperforge.services.vault_upgrade as vu_mod

    monkeypatch.setattr(
        vu_mod,
        "verify_vault_upgrade",
        lambda *_a, **_kw: {
            "ok": False,
            "checks": {
                "tier0_ocr_preserved": True,
                "tier0_db_sovereignty_preserved": False,
                "sidecars_preserved": True,
            },
            "failures": ["injected_g4_sovereignty_fault"],
        },
    )

    res = execute_vault_upgrade(vault, dry_run=False, fast_cutover=False)
    assert res["applied"] is False
    assert res["status"] == "rolled_back"
    assert res["rollback"]["rolled_back"] is True
    assert legacy_db.is_file()
    assert (vault / "paperforge.json").read_text(encoding="utf-8") == pre_cfg
    assert (old_pf / "memory" / "reading-log.jsonl").read_text(encoding="utf-8") == pre_reading_log

    chk = sqlite3.connect(f"file:{legacy_db.as_posix()}?mode=ro", uri=True)
    try:
        assert chk.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 1
        assert chk.execute("SELECT excerpt FROM reading_log").fetchone()[0] == "Tier-0 immutable insight"
        assert chk.execute("SELECT COUNT(*) FROM body_units").fetchone()[0] == 1
        assert chk.execute("SELECT COUNT(*) FROM body_units_fts").fetchone()[0] == 1
    finally:
        chk.close()


def test_p6_sqlite_wal_concurrent_readers_and_writer(tmp_path: Path) -> None:
    """Concurrent WAL readers via open_live_reader must run cleanly alongside writer commits."""
    from paperforge.memory.db import get_connection, open_live_reader
    from paperforge.memory.schema import ensure_schema

    vault = tmp_path / "wal_conc"
    vault.mkdir(parents=True)
    _assert_isolated(vault)
    canonical_test_config(vault, system_dir=".paperforge")

    db_path = vault / ".paperforge" / "indexes" / "paperforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    init_c = get_connection(db_path)
    try:
        ensure_schema(init_c)
        init_c.execute(
            "INSERT INTO papers(zotero_key, citation_key, title) VALUES (?, ?, ?)",
            ("WAL00001", "wal2026", "WAL Concurrency"),
        )
        init_c.commit()
    finally:
        init_c.close()

    errors: list[str] = []
    stop_flag = threading.Event()

    def _writer() -> None:
        wc = get_connection(db_path)
        try:
            for idx in range(25):
                wc.execute(
                    "INSERT INTO body_units(unit_id, paper_id, section_path, unit_text, page_span_json, "
                    "block_span_json, token_estimate, indexable, veto_reason, quality_hints_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"WAL00001:b:{idx}",
                        "WAL00001",
                        "Results",
                        f"synovium signal sample {idx}",
                        "[1]",
                        "[0]",
                        4,
                        1,
                        "",
                        "[]",
                    ),
                )
                wc.commit()
                time.sleep(0.003)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"writer: {exc!r}")
        finally:
            wc.close()
            stop_flag.set()

    def _reader(worker_id: int) -> None:
        try:
            while not stop_flag.is_set():
                with open_live_reader(vault, db_path=db_path) as rc:
                    rc.execute("SELECT COUNT(*) FROM body_units").fetchone()
                    rc.execute(
                        "SELECT COUNT(*) FROM body_units_fts WHERE body_units_fts MATCH 'synovium'"
                    ).fetchone()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"reader-{worker_id}: {exc!r}")

    threads = [threading.Thread(target=_writer)] + [
        threading.Thread(target=_reader, args=(i,)) for i in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert not errors, f"Concurrency errors observed: {errors}"
    chk = get_connection(db_path, read_only=True)
    try:
        bu = chk.execute("SELECT COUNT(*) FROM body_units").fetchone()[0]
        fts = chk.execute("SELECT COUNT(*) FROM body_units_fts").fetchone()[0]
        assert bu == 25
        assert fts == 25
    finally:
        chk.close()


def test_p10_live_zotero_wal_contention_snapshot_ro(tmp_path: Path) -> None:
    """open_zotero_snapshot_ro captures a consistent snapshot while Zotero holds an active WAL txn."""
    from paperforge.adapters.zotero_sqlite import open_zotero_snapshot_ro

    zdir = tmp_path / "zotero_live"
    zdir.mkdir(parents=True)
    _assert_isolated(zdir)
    zdb = zdir / "zotero.sqlite"

    c1 = sqlite3.connect(str(zdb))
    c1.execute("PRAGMA journal_mode=WAL")
    c1.execute("CREATE TABLE items(itemID INTEGER PRIMARY KEY, key TEXT)")
    c1.execute("INSERT INTO items VALUES (1, 'LIVEZOT1')")
    c1.commit()
    # Keep an active uncheckpointed write transaction open while reading snapshot
    c1.execute("BEGIN IMMEDIATE")
    c1.execute("INSERT INTO items VALUES (2, 'UNCOMMITTED2')")
    try:
        with open_zotero_snapshot_ro(zdir) as (snap_conn, _bbt):
            rows = [r["key"] for r in snap_conn.execute("SELECT key FROM items ORDER BY itemID").fetchall()]
            assert rows == ["LIVEZOT1"]
    finally:
        c1.rollback()
        c1.close()


def test_p4_linux_lowercase_legacy_dir_and_nfd_asset_matching(tmp_path: Path) -> None:
    """Case-insensitive legacy engine discovery, NFD->NFC asset matching, and cross-OS Zotero paths."""
    from paperforge.pdf_resolver import resolve_pdf_path
    from paperforge.services.storage_migration import migrate_vault_storage
    from paperforge.services.vault_upgrade import _find_legacy_engine_dirs, detect_vault_provenance

    vault = tmp_path / "vault_xplat"
    vault.mkdir(parents=True)
    _assert_isolated(vault)

    # Lowercase legacy engine directory structure (critical on Linux case-sensitive ext4)
    low_pf = vault / "system" / "paperforge"
    (low_pf / "indexes").mkdir(parents=True)
    (low_pf / "indexes" / "state.json").write_text('{"papers": {}}', encoding="utf-8")

    found = _find_legacy_engine_dirs(vault)
    assert len(found) == 1
    assert found[0].resolve() == low_pf.resolve()

    prov = detect_vault_provenance(vault)
    assert prov["state"] == "veteran_legacy"
    assert prov["needs_upgrade"] is True

    # APFS NFD asset embed normalization -> NFC target under .paperforge/ocr/<key>/assets/
    nfd_name = unicodedata.normalize("NFD", "figure_1_café.jpg")
    ocr_assets = low_pf / "ocr" / "XPLAT001" / "assets"
    ocr_assets.mkdir(parents=True)
    (ocr_assets / nfd_name).write_bytes(b"fakejpg")

    ws = vault / "Resources" / "Literature" / "General" / "XPLAT001"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text('{"zotero_key": "XPLAT001"}', encoding="utf-8")
    (ws / "XPLAT001.md").write_text(
        '---\nzotero_key: "XPLAT001"\n---\n\n![[figure_1.md]]\n',
        encoding="utf-8",
    )

    mig = migrate_vault_storage(vault, dry_run=False)
    assert mig["state"] in ("completed", "partial_success")
    assert (vault / ".paperforge" / "indexes" / "state.json").is_file()

    # Cross-OS synced Zotero pdf_path resolution using explicit local Zotero mirror
    zdir = tmp_path / "LocalZotero"
    target_dir = zdir / "storage" / "ABC99999"
    target_dir.mkdir(parents=True)
    pdf_file = target_dir / "paper.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n")

    foreign_path = "/Volumes/ResearchSSD/Zotero/storage/ABC99999/paper.pdf" if os.name == "nt" else r"X:\Zotero\storage\ABC99999\paper.pdf"
    resolved = resolve_pdf_path(foreign_path, True, vault, zotero_dir=zdir)
    assert resolved is not None
    assert Path(resolved) == pdf_file


def test_p11_bounded_backup_and_trash_retention_fail_closed(tmp_path: Path) -> None:
    """prune_old_backups and purge_trash keep newest N, prune aged dirs, and never touch outside paths."""
    from paperforge.services.vault_engine import prune_old_backups
    from paperforge.worker.trash import purge_trash

    vault = tmp_path / "vault_ret"
    vault.mkdir(parents=True)
    _assert_isolated(vault)
    canonical_test_config(vault, system_dir=".paperforge")

    b_cat = vault / ".paperforge" / "backups" / "vault-upgrade"
    b_cat.mkdir(parents=True)
    outside = tmp_path / "outside_precious"
    outside.mkdir()
    (outside / "keep.txt").write_text("do not delete", encoding="utf-8")

    old_ts = time.time() - 40 * 86400
    for i in range(4):
        d = b_cat / f"2026010{i}T000000Z"
        d.mkdir()
        (d / "marker.txt").write_text(f"b{i}", encoding="utf-8")
        if i < 2:
            os.utime(d, (old_ts + i, old_ts + i))

    removed_backups = prune_old_backups(vault, keep_latest=2, max_age_days=7)
    assert removed_backups == 2
    assert len([p for p in b_cat.iterdir() if p.is_dir()]) == 2
    assert (outside / "keep.txt").is_file()

    # Trash retention with aged vs fresh timestamp buckets
    t_root = vault / ".paperforge" / "trash"
    (t_root / "20200101T000000Z").mkdir(parents=True)
    (t_root / "20990101T000000Z").mkdir(parents=True)
    purged = purge_trash(vault, older_than_days=30)
    assert purged == 1
    assert not (t_root / "20200101T000000Z").exists()
    assert (t_root / "20990101T000000Z").is_dir()


def test_p5_doctor_single_subprocess_env_probe_and_ocr_doctor_ttl_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doctor uses a single batched env probe subprocess; ocr_doctor caches non-live checks."""
    from paperforge import ocr_diagnostics
    from paperforge.worker.status import _query_resolved_environment

    _assert_isolated(tmp_path)
    env_info = _query_resolved_environment(sys.executable, [], ["json"])
    assert isinstance(env_info, dict)
    assert isinstance(env_info.get("version_tuple"), list) and len(env_info["version_tuple"]) == 3
    assert isinstance(env_info.get("modules"), dict) and env_info["modules"].get("json") is not None

    calls = {"post": 0}

    def _fake_post(*_a, **_kw):
        calls["post"] += 1
        return SimpleNamespace(status_code=400, text="Bad Request")

    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_OCR__DEFAULT", "tok-cache-test-0001")
    monkeypatch.delenv("PAPERFORGE_OCR_DOCTOR_NOCACHE", raising=False)
    monkeypatch.setattr(ocr_diagnostics.requests, "post", _fake_post)

    cache_file = tmp_path / "state" / "ocr-doctor-cache.json"
    r1 = ocr_diagnostics.ocr_doctor(config=None, live=False, cache_path=cache_file, cache_ttl_seconds=120.0)
    r2 = ocr_diagnostics.ocr_doctor(config=None, live=False, cache_path=cache_file, cache_ttl_seconds=120.0)
    assert r1["passed"] is True and r2["passed"] is True
    assert calls["post"] == 1

    # Model change invalidates cache fingerprint
    r3 = ocr_diagnostics.ocr_doctor(
        config={"paddleocr_model": "OtherModel-2.0"},
        live=False,
        cache_path=cache_file,
        cache_ttl_seconds=120.0,
    )
    assert r3["passed"] is True
    assert calls["post"] == 2
