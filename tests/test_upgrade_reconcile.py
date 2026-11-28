"""Tests for Upgrade Self-Healing (`reconcile_epoch`) subsystem."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.services.upgrade_reconcile import (
    CURRENT_RECONCILE_EPOCH,
    ensure_vault_reconciled,
)
from paperforge.services.vault_engine import read_vault_manifest
from paperforge.services.vault_upgrade import execute_vault_upgrade
from tests.conftest import canonical_test_config


def _seed_legacy_broken_vault(
    vault: Path,
    *,
    with_db: bool = True,
    with_manifest: bool = True,
) -> dict[str, Path | bytes]:
    """Create a realistic legacy vault with stale derived paths, user notes, and sidecars."""
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault, system_dir=".paperforge")

    ws_dir = vault / "Resources" / "Literature" / "Ortho" / "REC00001 - Cartilage Repair"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "paper-meta.json").write_text(
        json.dumps({"zotero_key": "REC00001", "title": "Cartilage Repair"}),
        encoding="utf-8",
    )

    main_note = ws_dir / "REC00001.md"
    main_note_bytes = (
        '---\n'
        'zotero_key: "REC00001"\n'
        'title: "Cartilage Repair"\n'
        'domain: "Ortho"\n'
        'ocr_status: "done"\n'
        'deep_reading_status: "pending"\n'
        'do_ocr: true\n'
        '---\n\n'
        '## My Clinical Hypothesis\n\n'
        'User-written notes with exact spacing and emoji 🧪 must never be altered.\n'
    ).encode("utf-8")
    main_note.write_bytes(main_note_bytes)

    ann_file = ws_dir / "annotations.jsonl"
    ann_bytes = (
        '{"ann_id":"a1","paper_id":"REC00001","page":1,"kind":"highlight","exact_text":"Hydrogel"}\n'
    ).encode("utf-8")
    ann_file.write_bytes(ann_bytes)

    logs_dir = vault / ".paperforge" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reading_log = logs_dir / "reading-log.jsonl"
    reading_log_bytes = (
        '{"id":"rl1","paper_id":"REC00001","section":"Methods","excerpt":"20 um","usage":"method"}\n'
    ).encode("utf-8")
    reading_log.write_bytes(reading_log_bytes)

    idx_dir = vault / ".paperforge" / "indexes"
    idx_dir.mkdir(parents=True, exist_ok=True)

    # Stale formal-library.json with duplicated Resources/Literature/Literature/ paths
    formal_index = idx_dir / "formal-library.json"
    formal_index.write_text(
        json.dumps(
            {
                "schema_version": "2",
                "paper_count": 1,
                "items": [
                    {
                        "zotero_key": "REC00001",
                        "title": "Cartilage Repair",
                        "year": "2025",
                        "journal": "Biomaterials",
                        "impact_factor": 12.8,
                        "domain": "Literature",
                        "paper_root": "Resources/Literature/Literature/REC00001 - Cartilage Repair",
                        "main_note_path": "Resources/Literature/Literature/REC00001 - Cartilage Repair/REC00001.md",
                        "note_path": "Resources/Literature/Literature/REC00001 - Cartilage Repair/REC00001.md",
                        "ocr_md_path": "System/PaperForge/ocr/REC00001/fulltext.md",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Legacy PaperForge .base + custom user .base
    bases_dir = vault / "Bases"
    bases_dir.mkdir(parents=True, exist_ok=True)
    pf_base = bases_dir / "Ortho.base"
    pf_base.write_text(
        "filters:\n"
        "  and:\n"
        '    - file.inFolder("Resources/Literature/Literature/Ortho")\n'
        "    - !zotero_key.isEmpty()\n"
        "views:\n"
        "  - type: table\n"
        '    name: "控制面板"\n'
        "    order:\n"
        "      - title\n",
        encoding="utf-8",
    )
    custom_base = bases_dir / "My Reading Tracker.base"
    custom_base_bytes = (
        "filters:\n"
        "  and:\n"
        '    - file.ext == "md"\n'
        "views:\n"
        "  - type: table\n"
        '    name: "Personal Queue"\n'
        "    order:\n"
        "      - file.name\n"
    ).encode("utf-8")
    custom_base.write_bytes(custom_base_bytes)

    if with_manifest:
        (vault / ".paperforge" / "vault-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "layout_version": 2,
                    "paperforge_version": "2.0.10",
                    "engine_ssot": "sqlite",
                    "created_at": "2026-10-01T00:00:00+00:00",
                    "updated_at": "2026-10-01T00:00:00+00:00",
                    "migration_history": [],
                }
            ),
            encoding="utf-8",
        )

    if with_db:
        db_path = get_memory_db_path(vault)
        conn = get_connection(db_path)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO papers (zotero_key, title, domain, paper_root, main_note_path, note_path, ocr_md_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "REC00001",
                "Cartilage Repair",
                "Literature",
                "Resources/Literature/Literature/REC00001 - Cartilage Repair",
                "Resources/Literature/Literature/REC00001 - Cartilage Repair/REC00001.md",
                "Resources/Literature/Literature/REC00001 - Cartilage Repair/REC00001.md",
                "System/PaperForge/ocr/REC00001/fulltext.md",
            ),
        )
        conn.execute(
            "INSERT INTO workspace_registry (zotero_key, domain, workspace_relpath, main_note_relpath, dir_mtime_ns, identity_source, status, verified_at) "
            "VALUES (?, ?, ?, ?, 0, 'legacy', 'active', '2026-01-01')",
            (
                "REC00001",
                "Literature",
                "Resources/Literature/Literature/REC00001 - Cartilage Repair",
                "Resources/Literature/Literature/REC00001 - Cartilage Repair/REC00001.md",
            ),
        )
        conn.execute(
            "INSERT INTO workspace_registry (zotero_key, domain, workspace_relpath, main_note_relpath, dir_mtime_ns, identity_source, status, verified_at) "
            "VALUES (?, ?, ?, ?, 0, 'legacy', 'active', '2026-01-01')",
            (
                "GHOST999",
                "Ortho",
                "Resources/Literature/Ortho/GHOST999 - Deleted",
                "Resources/Literature/Ortho/GHOST999 - Deleted/GHOST999.md",
            ),
        )
        conn.commit()
        conn.close()

    return {
        "main_note": main_note,
        "main_note_bytes": main_note_bytes,
        "ann_file": ann_file,
        "ann_bytes": ann_bytes,
        "reading_log": reading_log,
        "reading_log_bytes": reading_log_bytes,
        "formal_index": formal_index,
        "pf_base": pf_base,
        "custom_base": custom_base,
        "custom_base_bytes": custom_base_bytes,
    }


def test_legacy_vault_auto_heals_and_preserves_user_files_byte_identical(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    seeded = _seed_legacy_broken_vault(vault, with_db=True, with_manifest=True)

    res = ensure_vault_reconciled(vault)
    assert res["reconciled"] is True
    assert res["skipped"] is False
    assert res["reconcile_epoch"] == CURRENT_RECONCILE_EPOCH
    assert res["db_reconciled"] is True
    assert res["workspace_registry_upserted"] == 1
    assert res["workspace_registry_removed"] == 1
    assert res["index_normalized"] is True
    assert res["state_seq"] >= 1

    # (a1) SQLite workspace_registry & papers healed
    db_path = get_memory_db_path(vault)
    conn = sqlite3.connect(str(db_path))
    reg_rows = conn.execute(
        "SELECT zotero_key, domain, workspace_relpath, main_note_relpath FROM workspace_registry"
    ).fetchall()
    paper_row = conn.execute(
        "SELECT domain, paper_root, main_note_path, note_path, ocr_md_path FROM papers WHERE zotero_key = 'REC00001'"
    ).fetchone()
    conn.close()

    assert reg_rows == [
        (
            "REC00001",
            "Ortho",
            "Resources/Literature/Ortho/REC00001 - Cartilage Repair",
            "Resources/Literature/Ortho/REC00001 - Cartilage Repair/REC00001.md",
        )
    ]
    assert paper_row == (
        "Ortho",
        "Resources/Literature/Ortho/REC00001 - Cartilage Repair",
        "Resources/Literature/Ortho/REC00001 - Cartilage Repair/REC00001.md",
        "Resources/Literature/Ortho/REC00001 - Cartilage Repair/REC00001.md",
        ".paperforge/ocr/REC00001/fulltext.md",
    )

    # (a2) formal-library.json normalized while preserving canonical fields
    idx_data = json.loads((seeded["formal_index"]).read_text(encoding="utf-8"))  # type: ignore[union-attr]
    item = idx_data["items"][0]
    assert item["title"] == "Cartilage Repair"
    assert item["year"] == "2025"
    assert item["journal"] == "Biomaterials"
    assert item["impact_factor"] == 12.8
    assert item["domain"] == "Ortho"
    assert item["paper_root"] == "Resources/Literature/Ortho/REC00001 - Cartilage Repair"
    assert item["main_note_path"] == "Resources/Literature/Ortho/REC00001 - Cartilage Repair/REC00001.md"
    assert item["ocr_md_path"] == ".paperforge/ocr/REC00001/fulltext.md"

    # (a3) PaperForge Base refreshed, custom user Base untouched
    pf_base_text = seeded["pf_base"].read_text(encoding="utf-8")  # type: ignore[union-attr]
    assert "paperforge-base-schema: 2" in pf_base_text
    assert "paperforge-table" in pf_base_text
    assert "控制面板" not in pf_base_text
    assert 'file.inFolder("Resources/Literature/Ortho")' in pf_base_text
    assert seeded["custom_base"].read_bytes() == seeded["custom_base_bytes"]  # type: ignore[union-attr]

    # (a4) vault-manifest.json persisted with reconcile_epoch + metadata
    manifest = read_vault_manifest(vault)
    assert manifest is not None
    assert manifest["reconcile_epoch"] == CURRENT_RECONCILE_EPOCH
    assert manifest["last_reconciled_version"]
    assert manifest["last_reconciled_at"]
    assert manifest["layout_version"] == 2

    # (b) User notes, annotations.jsonl, reading-log.jsonl byte-identical
    assert seeded["main_note"].read_bytes() == seeded["main_note_bytes"]  # type: ignore[union-attr]
    assert seeded["ann_file"].read_bytes() == seeded["ann_bytes"]  # type: ignore[union-attr]
    assert seeded["reading_log"].read_bytes() == seeded["reading_log_bytes"]  # type: ignore[union-attr]


def test_second_pass_is_fast_idempotent_noop_and_force_reruns(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _seed_legacy_broken_vault(vault, with_db=True, with_manifest=True)

    first = ensure_vault_reconciled(vault)
    assert first["reconciled"] is True
    seq_after_first = json.loads(
        (vault / ".paperforge" / "indexes" / ".state-seq.json").read_text(encoding="utf-8")
    )["seq"]
    manifest_before = (vault / ".paperforge" / "vault-manifest.json").read_text(encoding="utf-8")

    # (c) Second pass is an O(1) idempotent no-op
    t0 = time.perf_counter()
    second = ensure_vault_reconciled(vault)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert second["reconciled"] is False
    assert second["skipped"] is True
    assert second["reason"] == "epoch_current"
    assert second["reconcile_epoch"] == CURRENT_RECONCILE_EPOCH
    assert elapsed_ms < 25.0
    assert (vault / ".paperforge" / "vault-manifest.json").read_text(encoding="utf-8") == manifest_before
    seq_after_second = json.loads(
        (vault / ".paperforge" / "indexes" / ".state-seq.json").read_text(encoding="utf-8")
    )["seq"]
    assert seq_after_second == seq_after_first

    # (d) force=True re-runs cleanly
    forced = ensure_vault_reconciled(vault, force=True)
    assert forced["reconciled"] is True
    assert forced["skipped"] is False
    assert forced["reason"] == "forced"
    assert forced["reconcile_epoch"] == CURRENT_RECONCILE_EPOCH
    seq_after_forced = json.loads(
        (vault / ".paperforge" / "indexes" / ".state-seq.json").read_text(encoding="utf-8")
    )["seq"]
    assert seq_after_forced == seq_after_first + 1


def test_does_not_create_empty_db_when_absent_and_skips_uninitialized(tmp_path: Path) -> None:
    # Uninitialized vault -> safe no-op creating zero files
    empty_dir = tmp_path / "uninitialized"
    empty_dir.mkdir()
    res_uninit = ensure_vault_reconciled(empty_dir)
    assert res_uninit["reconciled"] is False
    assert res_uninit["skipped"] is True
    assert res_uninit["reason"] == "vault_not_initialized"
    assert list(empty_dir.iterdir()) == []

    # (e) Initialized vault WITHOUT paperforge.db -> MUST NOT create an empty paperforge.db!
    vault = tmp_path / "no_db_vault"
    _seed_legacy_broken_vault(vault, with_db=False, with_manifest=False)
    db_path = get_memory_db_path(vault)
    assert not db_path.exists()

    res = ensure_vault_reconciled(vault)
    assert res["reconciled"] is True
    assert res["db_reconciled"] is False
    assert not db_path.exists()


def test_manifest_and_state_seq_not_bumped_on_step_failure(tmp_path: Path) -> None:
    vault = tmp_path / "fail_vault"
    _seed_legacy_broken_vault(vault, with_db=True, with_manifest=True)

    with patch(
        "paperforge.services.upgrade_reconcile._reconcile_base_views",
        side_effect=RuntimeError("simulated base failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated base failure"):
            ensure_vault_reconciled(vault)

    manifest = read_vault_manifest(vault)
    assert manifest is not None
    assert "reconcile_epoch" not in manifest
    assert not (vault / ".paperforge" / "indexes" / ".state-seq.json").exists()


def test_cli_doctor_reconcile_and_upgrade_integration(tmp_path: Path, capsys) -> None:
    import paperforge.cli as cli

    vault = tmp_path / "cli_vault"
    _seed_legacy_broken_vault(vault, with_db=True, with_manifest=True)

    code = cli.main(["--vault", str(vault), "doctor", "--reconcile", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["data"]["reconciled"] is True
    assert payload["data"]["reconcile_epoch"] == CURRENT_RECONCILE_EPOCH

    # doctor --fix also runs reconcile
    code_fix = cli.main(["--vault", str(vault), "doctor", "--fix", "--force", "--json"])
    out_fix = capsys.readouterr().out
    payload_fix = json.loads(out_fix)
    assert code_fix in (0, 1)  # runtime pointer may be absent in isolated CI, but reconcile runs
    assert payload_fix["data"]["reconcile"]["reconciled"] is True
    assert payload_fix["data"]["reconcile"]["reason"] == "forced"

    # execute_vault_upgrade (full pass or fast_cutover + progressive heal) stamps reconcile_epoch
    from paperforge.services.vault_upgrade import heal_vault_progressive

    upg_vault = tmp_path / "upg_vault"
    _seed_legacy_broken_vault(upg_vault, with_db=True, with_manifest=False)
    upg_res = execute_vault_upgrade(upg_vault, dry_run=False, fast_cutover=True)
    assert upg_res["applied"] is True
    manifest_pre = read_vault_manifest(upg_vault)
    assert manifest_pre is not None and manifest_pre.get("heal_pending") is True
    heal_res = heal_vault_progressive(upg_vault)
    assert heal_res["reconcile_epoch"]["reconcile_epoch"] == CURRENT_RECONCILE_EPOCH
    manifest = read_vault_manifest(upg_vault)
    assert manifest is not None
    assert manifest.get("reconcile_epoch") == CURRENT_RECONCILE_EPOCH
