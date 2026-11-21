"""Unit tests for ADR-018 Unified VaultEngine, Identity Resolver, OCR Salvage, & Safe Upgrade."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from paperforge.commands.daemon import DaemonEngineSession, _execute_request
from paperforge.materialization.ocr import assess_ocr_bundle_atoms
from paperforge.services.identity_resolver import resolve_workspace_by_key, scan_vault_identities
from paperforge.services.storage_migration import migrate_vault_storage
from paperforge.services.sync_service import SyncService
from paperforge.services.vault_engine import (
    kv_get,
    kv_set,
    quarantine_move,
    read_vault_manifest,
    rebuild_db_from_truth,
    sync_ocr_catalog,
    sync_workspace_registry,
)
from paperforge.services.vault_upgrade import execute_vault_upgrade, inspect_vault_upgrade
from paperforge.worker.trash import list_trash
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


def _write_note(path: Path, key: str, title: str, body: str = "Body text\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'---\nzotero_key: "{key}"\ntitle: "{title}"\n---\n\n{body}',
        encoding="utf-8",
    )


def test_identity_resolver_ignores_renamed_folders_and_nested_depths(tmp_path: Path) -> None:
    lit_root = tmp_path / "Resources" / "Literature"

    # Case 1: User completely renamed workspace folder (no "KEY - " prefix)
    ws1 = lit_root / "Ortho" / "Subtopic" / "My Custom Cartilage Review"
    ws1.mkdir(parents=True)
    (ws1 / "paper-meta.json").write_text(json.dumps({"zotero_key": "ABCD1234"}), encoding="utf-8")
    _write_note(ws1 / "ABCD1234.md", "ABCD1234", "Cartilage Study")
    (ws1 / "custom_user_memo.md").write_text("# My Personal Notes\n", encoding="utf-8")

    # Case 2: Folder prefix lies (WRONG999), but paper-meta + frontmatter say REAL0001
    ws2 = lit_root / "Sports" / "WRONG999 - Renamed Folder"
    ws2.mkdir(parents=True)
    (ws2 / "paper-meta.json").write_text(json.dumps({"zotero_key": "REAL0001"}), encoding="utf-8")
    _write_note(ws2 / "REAL0001.md", "REAL0001", "Real Study")

    # Case 3: Deeply nested standalone flat note (depth 3 != legacy 2)
    flat = lit_root / "Ortho" / "Deep" / "Sub" / "FLAT0002 - Flat Note.md"
    _write_note(flat, "FLAT0002", "Flat Study")

    scan = scan_vault_identities(lit_root)
    assert "ABCD1234" in scan.workspaces
    assert scan.workspaces["ABCD1234"].workspace_dir == ws1
    assert scan.workspaces["ABCD1234"].main_note_path == ws1 / "ABCD1234.md"
    assert (ws1 / "custom_user_memo.md") in scan.workspaces["ABCD1234"].auxiliary_notes

    assert "REAL0001" in scan.workspaces
    assert any(m["type"] == "folder_prefix_key_mismatch" for m in scan.mismatches)

    assert len(scan.flat_notes) == 1
    assert scan.flat_notes[0].zotero_key == "FLAT0002"
    assert resolve_workspace_by_key(tmp_path, "ABCD1234", lit_root=lit_root, db_first=False) == ws1


def test_clean_flat_notes_quarantines_verified_and_protects_user_clones(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    lit_root = tmp_path / "Resources" / "Literature"

    ws_dir = lit_root / "Ortho" / "Custom Name Without Key"
    ws_dir.mkdir(parents=True)
    (ws_dir / "paper-meta.json").write_text(json.dumps({"zotero_key": "KFLT0001"}), encoding="utf-8")
    (ws_dir / "KFLT0001.md").write_text(
        '---\nzotero_key: "KFLT0001"\ntitle: "Workspace Note"\nocr_status: "done"\n---\n\nShared migrated summary\n',
        encoding="utf-8",
    )

    # 1. Verified legacy flat note (has PF workflow signature + zero unique prose) -> quarantined
    flat = lit_root / "Ortho" / "KFLT0001 - Old Flat Note.md"
    flat.write_text(
        '---\nzotero_key: "KFLT0001"\ntitle: "Old Flat Note"\nocr_status: "done"\n---\n\nShared migrated summary\n',
        encoding="utf-8",
    )

    # 2. User reading copy with unique personal prose -> MUST be protected (ambiguous_clone)
    user_clone = lit_root / "Ortho" / "KFLT0001 - My Personal Draft.md"
    user_clone.write_text(
        '---\nzotero_key: "KFLT0001"\ntitle: "Old Flat Note"\nocr_status: "done"\n---\n\nMy irreplaceable handwritten hypothesis!\n',
        encoding="utf-8",
    )

    # 3. Copy in nested subfolder or custom filename -> MUST be protected
    sub_copy = lit_root / "Ortho" / "ReadingGroup" / "KFLT0001 Copy.md"
    _write_note(sub_copy, "KFLT0001", "Copy")

    svc = SyncService(tmp_path)
    removed = svc.clean_flat_notes({"literature": lit_root}, json_output=True)
    assert removed == 1
    assert not flat.exists()
    assert user_clone.exists()
    assert sub_copy.exists()

    trashed = list_trash(tmp_path)
    assert any(t.get("paper_key") == "KFLT0001" and t.get("operation") == "clean_migrated_flat_note" for t in trashed)


def test_storage_migration_merges_partial_dot_paperforge_and_preserves_zotero(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    # Point zotero_data_dir at System/Zotero
    from paperforge.config import set_config

    set_config(tmp_path, "zotero_data_dir", "System/Zotero")
    zot_dir = tmp_path / "System" / "Zotero"
    zot_dir.mkdir(parents=True)
    (zot_dir / "zotero.sqlite").write_bytes(b"sqlite-zotero")

    # Pre-existing partial .paperforge/trash + collision file
    existing_trash = tmp_path / ".paperforge" / "trash" / "20260816T000000Z" / "abc123"
    existing_trash.mkdir(parents=True)
    (existing_trash / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".paperforge" / "indexes").mkdir(parents=True)
    (tmp_path / ".paperforge" / "indexes" / "state.json").write_text('{"new": true}', encoding="utf-8")

    # Legacy System/PaperForge tree with colliding & unique files
    old_pf = tmp_path / "System" / "PaperForge"
    (old_pf / "indexes").mkdir(parents=True)
    (old_pf / "indexes" / "state.json").write_text('{"old": true}', encoding="utf-8")
    (old_pf / "ocr" / "REN00001").mkdir(parents=True)
    (old_pf / "ocr" / "REN00001" / "meta.json").write_text('{"zotero_key": "REN00001"}', encoding="utf-8")

    # Renamed workspace without " - "
    ws = tmp_path / "Resources" / "Literature" / "Ortho" / "Renamed Without Dash"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text('{"zotero_key": "REN00001"}', encoding="utf-8")
    _write_note(ws / "REN00001.md", "REN00001", "Renamed", body="![[render/figures/figure_001.md]]\n")

    res = migrate_vault_storage(tmp_path, dry_run=False)
    assert res["conflicts_quarantined"] == 1
    assert res["moved_zotero_dir"] is False
    assert res["zotero_preserved_in_place"] is True
    assert (zot_dir / "zotero.sqlite").is_file()
    assert res["notes_rewritten"] == 1
    assert "![[REN00001_figure_001.jpg]]" in (ws / "REN00001.md").read_text(encoding="utf-8")
    # Conflict file preserved in backups, NOT overwritten or lost
    conflict_files = list((tmp_path / ".paperforge" / "backups" / "storage-migration" / "conflicts").glob("*state.json"))
    assert len(conflict_files) == 1


def test_assess_ocr_atoms_salvages_result_json_when_derived_corrupt(tmp_path: Path) -> None:
    paper_dir = tmp_path / ".paperforge" / "ocr" / "OCR00001"
    (paper_dir / "json").mkdir(parents=True)
    (paper_dir / "json" / "result.json").write_text(
        json.dumps([{"prunedResult": {"parsing_res_list": []}}]),
        encoding="utf-8",
    )
    (paper_dir / "canonical").mkdir(parents=True)
    # Corrupt blocks.raw.jsonl (simulates interrupted/corrupt derived stage)
    (paper_dir / "canonical" / "blocks.raw.jsonl").write_bytes(b"\xff\xfe\x00broken")

    atom = assess_ocr_bundle_atoms(paper_dir)
    assert atom["tier0_truth_intact"] is True
    assert atom["has_blocks_raw"] is False
    assert atom["salvage_action"] == "backfill_from_result_json"


def test_vault_upgrade_inspector_and_apply_preserve_data(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    # Legacy System/PaperForge + .paperforge/trash + residual leftovers + legacy Base
    (tmp_path / ".paperforge" / "trash").mkdir(parents=True)
    (tmp_path / ".venv-corrupt").mkdir()
    (tmp_path / ".venv-corrupt" / "dummy.txt").write_text("corrupt", encoding="utf-8")
    (tmp_path / ".env").write_text("PADDLEOCR_API_KEY=dummy-placeholder\n", encoding="utf-8")

    old_pf = tmp_path / "System" / "PaperForge"
    (old_pf / "indexes").mkdir(parents=True)
    (old_pf / "indexes" / "vectors_test").mkdir(parents=True)
    (old_pf / "indexes" / "vectors_test" / "chroma.sqlite3").write_bytes(b"chroma")

    # OCR paper with intact Tier-0 result.json but missing canonical/blocks.raw.jsonl
    ocr_p = old_pf / "ocr" / "UPG00001"
    (ocr_p / "json").mkdir(parents=True)
    (ocr_p / "json" / "result.json").write_text(json.dumps({"pages": [{"page": 1}]}), encoding="utf-8")

    # Workspace with stale paper-meta.json path
    ws = tmp_path / "Resources" / "Literature" / "Ortho" / "UPG00001 - Upgrade Paper"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text(
        json.dumps(
            {
                "zotero_key": "UPG00001",
                "ocr_md_path": "[[99_System/LiteraturePipeline/ocr/UPG00001/fulltext.md]]",
            }
        ),
        encoding="utf-8",
    )
    _write_note(ws / "UPG00001.md", "UPG00001", "Upgrade Paper")

    # Legacy Base view
    bases = tmp_path / "Bases"
    bases.mkdir(parents=True)
    (bases / "Ortho.base").write_text(
        "views:\n  - type: table\n    name: 控制面板\n",
        encoding="utf-8",
    )

    plan = inspect_vault_upgrade(tmp_path)
    auto_ids = {item["id"] for item in plan["category_a_auto"]}
    assert "storage.move_to_dot_paperforge" in auto_ids
    assert "ocr.local_salvage_backfill" in auto_ids
    assert "workspaces.normalize_identities" in auto_ids
    assert "bases.upgrade_views" in auto_ids
    assert plan["summary"]["ocr_atoms"]["backfill_from_result_json"] == 1
    assert any(c["id"] == "cleanup.venv_corrupt" for c in plan["cleanup_candidates"])

    # Dry-run executes nothing
    dry = execute_vault_upgrade(tmp_path, dry_run=True)
    assert dry["applied"] is False
    assert (tmp_path / ".venv-corrupt").exists()

    # Apply WITHOUT quarantine_residuals -> residuals still untouched!
    applied = execute_vault_upgrade(tmp_path, dry_run=False, quarantine_residuals=False)
    assert applied["applied"] is True
    assert (tmp_path / ".venv-corrupt").exists()
    meta_after = json.loads((ws / "paper-meta.json").read_text(encoding="utf-8"))
    assert "ocr_md_path" not in meta_after
    manifest = read_vault_manifest(tmp_path)
    assert manifest is not None and manifest["layout_version"] == 2

    # Apply WITH quarantine_residuals -> moved into .paperforge/trash/ (never raw unlink/rmtree!)
    execute_vault_upgrade(tmp_path, dry_run=False, quarantine_residuals=True)
    assert not (tmp_path / ".venv-corrupt").exists()
    assert any("upgrade_quarantine:cleanup.venv_corrupt" in str(t.get("operation")) for t in list_trash(tmp_path))


def test_vault_engine_sqlite_registry_rebuild_and_daemon_session(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    lit_root = tmp_path / "Resources" / "Literature"
    ws = lit_root / "Ortho" / "Custom Named Folder"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text('{"zotero_key": "ENG00001"}', encoding="utf-8")
    _write_note(ws / "ENG00001.md", "ENG00001", "Engine Paper")

    sync_res = sync_workspace_registry(tmp_path, lit_root=lit_root)
    assert sync_res["upserted"] == 1

    kv_set(tmp_path, "test_flag", {"ok": True})
    assert kv_get(tmp_path, "test_flag") == {"ok": True}

    sync_ocr_catalog(tmp_path)
    rebuild_res = rebuild_db_from_truth(tmp_path)
    assert rebuild_res["workspace_registry"]["upserted"] == 1

    # Verify DaemonEngineSession caches and invalidates on state_seq bump
    session = DaemonEngineSession()
    r1 = _execute_request(
        {"id": 1, "op": "engine.resolve_key", "vault": str(tmp_path), "key": "ENG00001"},
        real_stdout=None,
        real_stderr=None,
        session=session,
    )
    assert r1["exit_code"] == 0
    payload1 = json.loads(r1["stdout"])
    assert payload1["workspace_relpath"].endswith("Custom Named Folder")

    r2 = _execute_request(
        {"id": 2, "op": "engine.status", "vault": str(tmp_path)},
        real_stdout=None,
        real_stderr=None,
        session=session,
    )
    st = json.loads(r2["stdout"])
    assert st["cache_hits"] >= 1
    assert st["workspace_count"] == 1

    # Bump state_seq -> triggers miss & refresh
    sync_workspace_registry(tmp_path, lit_root=lit_root)
    st_after = session.status(tmp_path)
    assert st_after["cache_misses"] == 2


def test_provenance_fresh_or_foreign_touches_nothing(tmp_path: Path) -> None:
    # Foreign Obsidian vault with user's own ./assets folder, native .base table, and notes
    (tmp_path / "Notes" / "ProjectA" / "assets").mkdir(parents=True)
    (tmp_path / "Notes" / "ProjectA" / "Notes.md").write_text("# My Thesis\n", encoding="utf-8")
    (tmp_path / "Bases").mkdir()
    native_base = tmp_path / "Bases" / "Experiments.base"
    native_base.write_text("views:\n  - type: table\n    name: Lab Log\n", encoding="utf-8")

    plan = inspect_vault_upgrade(tmp_path)
    assert plan["provenance"]["state"] == "fresh_or_foreign"
    assert plan["provenance"]["needs_upgrade"] is False
    assert plan["category_a_auto"] == []
    assert plan["category_b_reconfig"] == []
    assert plan["category_c_tamper"] == []
    assert "paperforge-table" not in native_base.read_text(encoding="utf-8")


def test_fast_cutover_progressive_heal_native_base_protection_and_rollback(tmp_path: Path) -> None:
    from paperforge.services.vault_upgrade import heal_vault_progressive, rollback_vault_upgrade

    canonical_test_config(tmp_path, system_dir="System")
    old_pf = tmp_path / "System" / "PaperForge"
    (old_pf / "indexes").mkdir(parents=True)
    (old_pf / "indexes" / "state.json").write_text('{"papers": {}}', encoding="utf-8")

    # Workspace with legacy note name `<KEY> - <Title>.md` to verify backlink `aliases` preservation
    ws = tmp_path / "Resources" / "Literature" / "Ortho" / "CUT00001 - Fast Study"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text(
        json.dumps({"zotero_key": "CUT00001", "ocr_md_path": "System/PaperForge/ocr/CUT00001/fulltext.md"}),
        encoding="utf-8",
    )
    _write_note(ws / "CUT00001 - Fast Study.md", "CUT00001", "Fast Study")

    bases = tmp_path / "Bases"
    bases.mkdir(parents=True)
    pf_base = bases / "Ortho.base"
    pf_base.write_text("views:\n  - type: table\n    name: 控制面板\n", encoding="utf-8")
    user_base = bases / "MyPersonalTracker.base"
    user_base.write_text("views:\n  - type: table\n    name: Daily Experiments\n", encoding="utf-8")

    # Phase 1: Fast cutover (<3s O(1) cutover)
    cut = execute_vault_upgrade(tmp_path, dry_run=False, fast_cutover=True)
    assert cut["applied"] is True
    assert cut["errors"] == []
    assert (tmp_path / ".paperforge" / "indexes" / "state.json").is_file()
    assert "paperforge-table" in pf_base.read_text(encoding="utf-8")
    # Native user .base MUST NOT be converted to paperforge-table!
    assert "paperforge-table" not in user_base.read_text(encoding="utf-8")

    # Phase 2: Progressive background heal with priority_key
    healed = heal_vault_progressive(tmp_path, priority_key="CUT00001")
    assert healed["legacy_notes_renamed"] == 1
    assert (ws / "CUT00001.md").is_file()
    renamed_text = (ws / "CUT00001.md").read_text(encoding="utf-8")
    # Preserves Obsidian [[CUT00001 - Fast Study]] backlinks via frontmatter aliases!
    assert "CUT00001 - Fast Study" in renamed_text
    assert healed["skipped_isolated"] == []

    # Phase 3: 1-Click Time-Machine Rollback
    rb = rollback_vault_upgrade(tmp_path)
    assert rb["rolled_back"] is True
    assert (tmp_path / "System" / "PaperForge" / "indexes" / "state.json").is_file()
    assert "控制面板" in pf_base.read_text(encoding="utf-8")
    assert "Daily Experiments" in user_base.read_text(encoding="utf-8")


def test_atomic_cas_conflict_and_permanent_log_schema_version(tmp_path: Path) -> None:
    import hashlib
    from paperforge.core.io import CASConflictError, read_jsonl, write_text_cas
    from paperforge.memory.permanent import append_reading_note, get_reading_log_path

    canonical_test_config(tmp_path, system_dir=".paperforge")
    note = tmp_path / "note.md"
    note.write_text("v1 original\n", encoding="utf-8")
    sha1 = hashlib.sha256(note.read_bytes()).hexdigest()
    write_text_cas(note, "v2 updated\n", expected_sha256=sha1)
    assert note.read_text(encoding="utf-8") == "v2 updated\n"
    sha2 = hashlib.sha256(note.read_bytes()).hexdigest()

    # Simulate user editing in Obsidian concurrently
    note.write_text("user concurrent edit\n", encoding="utf-8")
    with pytest.raises(CASConflictError):
        write_text_cas(note, "daemon stale overwrite\n", expected_sha256=sha2)
    assert note.read_text(encoding="utf-8") == "user concurrent edit\n"

    # Permanent JSONL stamps schema_version=1 and read_jsonl tolerates truncated tail line
    res = append_reading_note(tmp_path, paper_id="ABC12345", section="Methods", excerpt="Key result")
    assert res["ok"] is True
    log_file = get_reading_log_path(tmp_path)
    with open(log_file, "ab") as fh:
        fh.write(b'{"truncated_crash_line": ')
    rows = read_jsonl(log_file)
    assert len(rows) == 1
    assert rows[0]["schema_version"] == 1
    assert rows[0]["paper_id"] == "ABC12345"
