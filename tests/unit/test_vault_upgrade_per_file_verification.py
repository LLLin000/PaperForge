"""Per-file migration safety, post-upgrade verification, Chroma rebuild convergence, & Skill Hub alignment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.config import load_config, validate_config
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.services.storage_migration import rewrite_visual_embeds_for_key
from paperforge.services.vault_engine import read_vault_manifest
from paperforge.services.vault_upgrade import (
    execute_vault_upgrade,
    heal_vault_progressive,
    inspect_vault_upgrade,
    rollback_vault_upgrade,
    verify_vault_upgrade,
)
from paperforge.worker.trash import list_trash
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


def _write_note(path: Path, key: str, title: str, *, extra_fm: str = "", body: str = "Summary line\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'---\nzotero_key: "{key}"\ntitle: "{title}"\nocr_status: "done"\n{extra_fm}---\n\n{body}',
        encoding="utf-8",
    )


def test_fast_cutover_mid_move_crash_flushes_journal_and_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    old_pf = tmp_path / "System" / "PaperForge"
    f1 = old_pf / "indexes" / "state.json"
    f2 = old_pf / "ocr" / "CRASH01" / "json" / "result.json"
    f1.parent.mkdir(parents=True)
    f2.parent.mkdir(parents=True)
    f1.write_text('{"ok": true}', encoding="utf-8")
    f2.write_text('{"pages": [{"p": 1}]}', encoding="utf-8")

    from paperforge.services import storage_migration

    orig_move = storage_migration.shutil.move
    moves = 0

    def _fail_second_move(src: str, dst: str) -> str:
        nonlocal moves
        if ".paperforge" in Path(dst).parts and "backups" not in Path(dst).parts:
            moves += 1
            if moves >= 2:
                raise OSError("injected fast_cutover mid-move crash")
        return orig_move(src, dst)

    monkeypatch.setattr(storage_migration.shutil, "move", _fail_second_move)
    res = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    monkeypatch.undo()

    assert res["status"] == "partial_success"
    assert any(e["step"] == "storage_migration" for e in res["errors"])

    # Journal & moved-pairs were flushed incrementally BEFORE the crash
    journal = json.loads((tmp_path / ".paperforge" / ".migration-journal.json").read_text(encoding="utf-8"))
    assert journal["state"] == "in_progress"
    assert len(journal["moved_pairs"]) >= 1

    # Rollback cleanly reverses partial moves
    rb = rollback_vault_upgrade(tmp_path)
    assert rb["rolled_back"] is True
    assert rb["restored_moves"] >= 1
    assert f1.exists() or f2.exists()
    assert f1.exists()
    assert f2.exists()


def test_heal_backfills_ocr_before_fulltext_check_and_cleans_flat_notes(tmp_path: Path) -> None:
    from paperforge.worker.ocr_rebuild import backfill_from_result

    canonical_test_config(tmp_path, system_dir=".paperforge")
    pf = tmp_path / ".paperforge"
    ocr_dir = pf / "ocr" / "BF000001"
    (ocr_dir / "json").mkdir(parents=True)
    # Build minimal valid result.json that backfill_from_result can materialize
    sample_result = {
        "pages": [
            {
                "page_index": 0,
                "prunedResult": {
                    "parsing_res_list": [
                        {
                            "block_label": "text",
                            "block_content": "Backfilled paragraph text for verification.",
                            "block_bbox": [10, 10, 200, 40],
                            "block_order": 1,
                        }
                    ]
                },
            }
        ]
    }
    (ocr_dir / "json" / "result.json").write_text(json.dumps(sample_result), encoding="utf-8")

    # Run backfill once in a temp copy or run heal twice? Easier: know what backfill writes by pre-computing
    # fulltext via a second dir OR populate fulltext.md hash? Actually let backfill run first on a sibling helper:
    ws_dir = tmp_path / "Resources" / "Literature" / "Ortho" / "BF000001 - Backfill Paper"
    ws_dir.mkdir(parents=True)
    (ws_dir / "paper-meta.json").write_text('{"zotero_key": "BF000001"}', encoding="utf-8")
    _write_note(ws_dir / "BF000001.md", "BF000001", "Backfill Paper")

    # Probe exact bytes that backfill_from_result writes for BF000001 when note is present
    probe_vault = tmp_path / "_probe"
    probe_ocr = probe_vault / ".paperforge" / "ocr" / "BF000001" / "json"
    probe_ocr.mkdir(parents=True)
    (probe_ocr / "result.json").write_text(json.dumps(sample_result), encoding="utf-8")
    probe_ws = probe_vault / "Resources" / "Literature" / "Ortho" / "BF000001 - Backfill Paper"
    probe_ws.mkdir(parents=True)
    (probe_ws / "paper-meta.json").write_text('{"zotero_key": "BF000001"}', encoding="utf-8")
    _write_note(probe_ws / "BF000001.md", "BF000001", "Backfill Paper")
    canonical_test_config(probe_vault, system_dir=".paperforge")
    backfill_from_result(probe_vault, "BF000001")
    mirror_bytes = (probe_vault / ".paperforge" / "ocr" / "BF000001" / "fulltext.md").read_bytes()
    (ws_dir / "fulltext.md").write_bytes(mirror_bytes)

    # Also remove _probe before scanning tmp_path
    import shutil

    shutil.rmtree(probe_vault)

    # Verified legacy flat note at <lit_root>/<domain>/ (exact match) + ambiguous user clone
    flat_dup = tmp_path / "Resources" / "Literature" / "Ortho" / "BF000001 - Backfill Paper.md"
    _write_note(flat_dup, "BF000001", "Backfill Paper")
    ambiguous_clone = tmp_path / "Resources" / "Literature" / "Ortho" / "BF000001 - My Draft.md"
    _write_note(ambiguous_clone, "BF000001", "My Draft", body="My personal unique notes.\n")

    healed = heal_vault_progressive(tmp_path, backfill_ocr=True)
    assert healed["ocr_backfilled"] == 1
    # Because backfill ran BEFORE workspace fulltext check, the unmodified mirror was safely removed
    # rather than falsely quarantined into trash!
    assert not (ws_dir / "fulltext.md").exists()
    preserved_ft = [
        t for t in list_trash(tmp_path) if t.get("operation") == "workspace_fulltext_preserve"
    ]
    assert preserved_ft == []

    # Verified flat duplicate quarantined; ambiguous user clone preserved untouched
    assert healed["flat_notes_quarantined"] == 1
    assert not flat_dup.exists()
    assert ambiguous_clone.exists()
    assert any(t.get("operation") == "upgrade_clean_legacy_flat" for t in list_trash(tmp_path))


def test_heal_reconciles_custom_system_dir_db_formal_library_and_verifies(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir="00_System")
    old_pf = tmp_path / "00_System" / "PaperForge"
    (old_pf / "indexes").mkdir(parents=True)
    (old_pf / "ocr" / "CUS00001" / "json").mkdir(parents=True)
    (old_pf / "ocr" / "CUS00001" / "json" / "result.json").write_text(
        json.dumps({"pages": [{"p": 1}]}), encoding="utf-8"
    )

    ws = tmp_path / "Resources" / "Literature" / "Ortho" / "CUS00001 - Custom Dir Study"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text(
        json.dumps(
            {
                "zotero_key": "CUS00001",
                "ocr_md_path": "00_System/PaperForge/ocr/CUS00001/fulltext.md",
            }
        ),
        encoding="utf-8",
    )
    (ws / "annotations.jsonl").write_text(
        json.dumps(
            {
                "ann_id": "ann_cus_1",
                "paper_id": "CUS00001",
                "page": 1,
                "kind": "highlight",
                "exact_text": "Key finding",
                "comment": "Important clinical result",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_note(ws / "CUS00001 - Custom Dir Study.md", "CUS00001", "Custom Dir Study")

    db_path = old_pf / "indexes" / "paperforge.db"
    conn = get_connection(db_path)
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO papers (zotero_key, title, main_note_path, note_path, paper_root, ocr_md_path, ocr_json_path, fulltext_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "CUS00001",
            "Custom Dir Study",
            "Resources/Literature/Ortho/CUS00001 - Custom Dir Study/CUS00001 - Custom Dir Study.md",
            "Resources/Literature/Ortho/CUS00001 - Custom Dir Study/CUS00001 - Custom Dir Study.md",
            "Resources/Literature/Ortho/CUS00001 - Custom Dir Study/",
            "00_System/PaperForge/ocr/CUS00001/fulltext.md",
            "00_System/PaperForge/ocr/CUS00001/json/result.json",
            "00_System/PaperForge/ocr/CUS00001/fulltext.md",
        ),
    )
    conn.commit()
    conn.close()

    (old_pf / "indexes" / "formal-library.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "zotero_key": "CUS00001",
                        "ocr_md_path": "00_System/PaperForge/ocr/CUS00001/fulltext.md",
                        "main_note_path": "Resources/Literature/Ortho/CUS00001 - Custom Dir Study/CUS00001 - Custom Dir Study.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cut = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    assert cut["applied"] is True
    assert cut["verification"]["ok"] is True
    assert cut["verification"]["checks"]["tier0_ocr_preserved"] is True

    healed = heal_vault_progressive(tmp_path)
    assert healed["paper_meta_cleaned"] == 1
    assert healed["legacy_notes_renamed"] == 1
    assert healed["db_paths_updated"] >= 4
    assert healed["sidecars_hydrated"] >= 1
    assert healed["verification"]["ok"] is True
    assert healed["verification"]["checks"]["no_stale_db_paths"] is True
    assert healed["verification"]["checks"]["no_stale_paper_meta_paths"] is True

    # Verify DB rows & annotations hydrated
    live_conn = get_connection(get_memory_db_path(tmp_path), read_only=True)
    try:
        prow = live_conn.execute(
            "SELECT main_note_path, ocr_md_path, ocr_json_path FROM papers WHERE zotero_key = 'CUS00001'"
        ).fetchone()
        assert prow["main_note_path"].endswith("CUS00001.md")
        assert prow["ocr_md_path"] == ".paperforge/ocr/CUS00001/fulltext.md"
        assert prow["ocr_json_path"] == ".paperforge/ocr/CUS00001/json/result.json"
        ann_cnt = live_conn.execute(
            "SELECT COUNT(*) FROM paper_annotations WHERE paper_id = 'CUS00001'"
        ).fetchone()[0]
        assert ann_cnt == 1
    finally:
        live_conn.close()

    fl = json.loads((tmp_path / ".paperforge" / "indexes" / "formal-library.json").read_text(encoding="utf-8"))
    assert fl["items"][0]["ocr_md_path"] == ".paperforge/ocr/CUS00001/fulltext.md"
    assert fl["items"][0]["main_note_path"].endswith("CUS00001.md")


def test_rewrite_visual_embeds_respects_available_assets() -> None:
    md = "A: ![[render/figures/figure_001.md|Fig 1]]\nB: ![[render/figures/figure_999.md]]\n"
    updated, count = rewrite_visual_embeds_for_key(
        md, "K001", available_assets={"K001_figure_001.jpg"}
    )
    assert count == 1
    assert "![[K001_figure_001.jpg|Fig 1]]" in updated
    assert "![[render/figures/figure_999.md]]" in updated


def test_inspect_detects_chroma_vectors_vault_local_skills_and_veteran_rescue(tmp_path: Path) -> None:
    # Veteran rescue vault WITHOUT paperforge.json, using legacy 03_Resources & 05_Bases + Chroma + local skill
    ocr_json = tmp_path / "99_System" / "PaperForge" / "ocr" / "RES00001" / "json" / "result.json"
    ocr_json.parent.mkdir(parents=True)
    ocr_json.write_text(json.dumps({"pages": [{"p": 1}]}), encoding="utf-8")

    vec_dir = tmp_path / "99_System" / "PaperForge" / "indexes" / "vectors"
    vec_dir.mkdir(parents=True)
    (vec_dir / "chroma.sqlite3").write_bytes(b"legacy-chroma")

    local_skill = tmp_path / ".agents" / "skills" / "paperforge"
    local_skill.mkdir(parents=True)
    (local_skill / "SKILL.md").write_text("# Old skill\n", encoding="utf-8")

    ws = tmp_path / "03_Resources" / "Literature" / "Ortho" / "RES00001 - Rescue"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text('{"zotero_key": "RES00001"}', encoding="utf-8")
    _write_note(ws / "RES00001.md", "RES00001", "Rescue")
    (tmp_path / "05_Bases").mkdir()

    plan = inspect_vault_upgrade(tmp_path)
    cleanup_ids = {c["id"] for c in plan["cleanup_candidates"]}
    reconfig_ids = {r["id"] for r in plan["category_b_reconfig"]}
    assert "cleanup.legacy_chroma_vectors" in cleanup_ids
    assert any(cid.startswith("cleanup.vault_local_skill.") for cid in cleanup_ids)
    assert "vectors.rebuild_sqlite_vec" in reconfig_ids
    assert "skills.migrate_to_machine_hub" in reconfig_ids

    cut = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    assert cut["applied"] is True
    assert validate_config(tmp_path).state == "valid"
    snap = load_config(tmp_path)
    assert snap.values["system_dir"].value == ".paperforge"
    assert snap.values["resources_dir"].value == "03_Resources"
    assert snap.values["base_dir"].value == "05_Bases"
    manifest = read_vault_manifest(tmp_path)
    assert manifest is not None and manifest["layout_version"] == 2
    ver = verify_vault_upgrade(tmp_path)
    assert ver["ok"] is True


def test_rollback_after_full_upgrade_restores_legacy_engine_tree(tmp_path: Path) -> None:
    """PF-MIG-002: full (non-fast-cutover) upgrade --apply + --rollback restores all engine data with zero split-brain."""
    canonical_test_config(tmp_path, system_dir="99_System")
    old_pf = tmp_path / "99_System" / "PaperForge"
    ocr_res = old_pf / "ocr" / "NIN00001" / "json" / "result.json"
    ocr_res.parent.mkdir(parents=True)
    ocr_res.write_text('{"pages": [{"p": 1}]}', encoding="utf-8")
    idx_file = old_pf / "indexes" / "formal-library.json"
    idx_file.parent.mkdir(parents=True)
    idx_file.write_text('{"items": []}', encoding="utf-8")
    exp_file = old_pf / "exports" / "Ortho.json"
    exp_file.parent.mkdir(parents=True)
    exp_file.write_text('{"items": []}', encoding="utf-8")

    applied = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=False, rebuild_db=False)
    assert applied["applied"] is True
    assert not ocr_res.exists()
    assert (tmp_path / ".paperforge" / "ocr" / "NIN00001" / "json" / "result.json").is_file()

    rb = rollback_vault_upgrade(tmp_path)
    assert rb["rolled_back"] is True
    assert rb["restored_moves"] >= 3
    assert ocr_res.is_file()
    assert idx_file.is_file()
    assert exp_file.is_file()
    assert not (tmp_path / ".paperforge" / "ocr" / "NIN00001" / "json" / "result.json").exists()
    assert load_config(tmp_path).values["system_dir"].value == "99_System"


def test_inspect_and_heal_respect_03_resources_and_custom_base_dir(tmp_path: Path) -> None:
    """PF-MIG-003: inspect_vault_upgrade and heal_vault_progressive resolve 03_Resources/Literature & 05_Bases."""
    canonical_test_config(
        tmp_path,
        system_dir=".paperforge",
        resources_dir="03_Resources",
        literature_dir="Literature",
        base_dir="05_Bases",
    )
    (tmp_path / ".paperforge" / "indexes").mkdir(parents=True)
    ws = tmp_path / "03_Resources" / "Literature" / "Ortho" / "RSC00001 - Rescue Study"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text('{"zotero_key": "RSC00001"}', encoding="utf-8")
    _write_note(ws / "RSC00001.md", "RSC00001", "Rescue Study")
    base_f = tmp_path / "05_Bases" / "Ortho.base"
    base_f.parent.mkdir(parents=True)
    base_f.write_text("views:\n  - type: table\n    name: 控制面板\n", encoding="utf-8")

    plan = inspect_vault_upgrade(tmp_path)
    assert plan["census"]["pf_canonical"]["workspaces"] == 1
    assert any(a["id"] == "bases.upgrade_views" for a in plan["category_a_auto"])

    healed = heal_vault_progressive(tmp_path)
    assert healed["processed_workspaces"] == 1
    assert healed["workspace_registry_upserted"] == 1
    assert healed["verification"]["counts"]["workspaces"] == 1


def test_upgrade_backup_never_copies_plaintext_dotenv(tmp_path: Path) -> None:
    """PF-SEC-006: pre-flight backups must never persist plaintext .env secrets."""
    canonical_test_config(tmp_path, system_dir="System")
    (tmp_path / "System" / "PaperForge" / "indexes").mkdir(parents=True)
    secret_val = "sk-super-secret-ocr-token-12345"
    (tmp_path / ".env").write_text(f"PADDLEOCR_API_KEY={secret_val}\n", encoding="utf-8")

    res = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    assert res["applied"] is True
    backup_dir = Path(res["backup_dir"])
    assert not (backup_dir / ".env").exists()
    for f in backup_dir.rglob("*"):
        if f.is_file():
            assert secret_val not in f.read_text(encoding="utf-8", errors="ignore")


def test_quarantine_residuals_moves_legacy_engine_leftovers_after_cutover(tmp_path: Path) -> None:
    """PF-MIG-006: --quarantine-residuals moves cli.py and legacy Chroma vectors even after cutover into .paperforge/."""
    canonical_test_config(tmp_path, system_dir="System")
    old_pf = tmp_path / "System" / "PaperForge"
    (old_pf / "indexes" / "vectors").mkdir(parents=True)
    (old_pf / "indexes" / "vectors" / "chroma.sqlite3").write_bytes(b"chroma-old")
    (old_pf / "cli.py").write_text("# legacy cli\n", encoding="utf-8")

    res = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True, quarantine_residuals=True)
    assert res["applied"] is True
    assert not (tmp_path / ".paperforge" / "cli.py").exists()
    assert not (tmp_path / ".paperforge" / "indexes" / "vectors").exists()
    ops = {t.get("operation") for t in list_trash(tmp_path)}
    assert "upgrade_quarantine:cleanup.legacy_engine.cli.py" in ops
    assert "upgrade_quarantine:cleanup.legacy_chroma_vectors" in ops


def test_fast_cutover_does_not_repeat_full_scans_and_meets_3s_slo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PF-MIG-010: fast_cutover avoids full O(N) workspace/JSON scans and completes 300-paper cutover <3s."""
    import time
    from paperforge.services import identity_resolver

    canonical_test_config(tmp_path, system_dir="System")
    old_pf = tmp_path / "System" / "PaperForge"
    (old_pf / "indexes").mkdir(parents=True)
    (old_pf / "indexes" / "state.json").write_text("{}", encoding="utf-8")
    lit = tmp_path / "Resources" / "Literature" / "Ortho"
    lit.mkdir(parents=True)
    for i in range(300):
        k = f"KEY{i:05d}"
        ws = lit / f"{k} - Paper {i}"
        ws.mkdir()
        (ws / f"{k}.md").write_text(f"---\nzotero_key: {k}\n---\n", encoding="utf-8")
        if i < 50:
            rj = old_pf / "ocr" / k / "json" / "result.json"
            rj.parent.mkdir(parents=True)
            rj.write_text('{"pages": [{"p": 1}]}', encoding="utf-8")

    def _forbid_full_scan(*_a, **_kw):
        raise AssertionError("fast_cutover must not run full scan_vault_identities")

    monkeypatch.setattr(identity_resolver, "scan_vault_identities", _forbid_full_scan)
    t0 = time.perf_counter()
    res = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    elapsed = time.perf_counter() - t0
    assert res["applied"] is True
    assert res["verification"]["ok"] is True
    assert elapsed < 3.0, f"fast_cutover took {elapsed:.2f}s (> 3.0s SLO)"


def test_inject_backlink_alias_supports_yaml_block_list(tmp_path: Path) -> None:
    """PF-MIG-013: _inject_backlink_alias appends old stem into YAML block-list aliases."""
    from paperforge.services.vault_upgrade import _inject_backlink_alias

    note = tmp_path / "LEG00002.md"
    note.write_text(
        '---\nzotero_key: "LEG00002"\ntitle: "Meniscus Repair"\naliases:\n  - "MeniscusBlockAlias"\n---\n\nBody\n',
        encoding="utf-8",
    )
    _inject_backlink_alias(note, "LEG00002 - Meniscus Repair")
    txt = note.read_text(encoding="utf-8")
    assert '"MeniscusBlockAlias"' in txt
    assert '"LEG00002 - Meniscus Repair"' in txt


def test_rollback_restores_custom_base_dir(tmp_path: Path) -> None:
    """PF-MIG-014: preflight backup and rollback restore custom base_dir .base files."""
    canonical_test_config(tmp_path, system_dir="System", base_dir="MyCustomBases")
    (tmp_path / "System" / "PaperForge" / "indexes").mkdir(parents=True)
    custom_base = tmp_path / "MyCustomBases" / "Literature Hub.base"
    custom_base.parent.mkdir(parents=True)
    orig_base = "views:\n  - type: table\n    name: 控制面板\n"
    custom_base.write_text(orig_base, encoding="utf-8")

    cut = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    assert cut["applied"] is True
    assert "paperforge-table" in custom_base.read_text(encoding="utf-8")

    rb = rollback_vault_upgrade(tmp_path)
    assert rb["rolled_back"] is True
    assert custom_base.read_text(encoding="utf-8") == orig_base


def test_upgrade_fast_cutover_without_apply_rejects_cleanly(tmp_path: Path, capsys) -> None:
    """PF-UX-009: `upgrade --fast-cutover` without `--apply` returns exit 2 and does not pretend apply."""
    import argparse
    from paperforge.commands.upgrade import run as upgrade_run

    canonical_test_config(tmp_path, system_dir="System")
    args = argparse.Namespace(
        vault_path=str(tmp_path),
        json=True,
        rollback=False,
        heal=False,
        apply=False,
        dry_run=False,
        plan=False,
        fast_cutover=True,
        backfill_ocr=False,
        quarantine_residuals=False,
        quarantine_ids="",
        no_rebuild_db=False,
        priority_key="",
        limit=None,
    )
    rc = upgrade_run(args)
    out = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert out["ok"] is False
    assert "--apply" in out["error"]["message"]
