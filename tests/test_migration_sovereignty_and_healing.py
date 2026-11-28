"""Regression suite for migration data sovereignty, FTS5 healing, RC-1..RC-5."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from paperforge.config import load_config
from paperforge.core.fs_safe import (
    is_windows_reserved_name,
    safe_is_dir,
    safe_is_file,
    safe_iterdir,
    safe_rglob,
)
from paperforge.doctor.field_validator import validate_frontmatter_from_file
from paperforge.memory.builder import (
    _delete_paper,
    _incremental_units_only,
    _upsert_body_units,
    build_from_index,
)
from paperforge.memory.db import (
    check_and_heal_fts,
    get_connection,
    get_memory_db_path,
    rebuild_fts_indexes,
    safe_delete_body_units_fts,
)
from paperforge.memory.schema import (
    CURRENT_SCHEMA_VERSION,
    ensure_schema,
    get_schema_version,
    migrate_schema,
)
from paperforge.schema import load_field_registry
from paperforge.services.identity_resolver import (
    _fast_parse_identity_frontmatter,
    _read_note_identity,
)
from paperforge.services.migration_contract import (
    PER_FILE_ACTION_CONTRACT,
    FileActionRule,
    MigrationStateError,
    UpgradePhase,
    UpgradeStateMachine,
    audit_file_action_conflicts,
)
from paperforge.services.storage_migration import (
    _move_tree_entries,
    migrate_vault_storage,
    quiesce_sqlite_wal,
    rollback_incomplete_migration,
)
from paperforge.services.upgrade_reconcile import (
    CURRENT_RECONCILE_EPOCH,
    ensure_vault_reconciled,
)
from paperforge.services.vault_upgrade import (
    _capture_db_tier0_counts,
    execute_vault_upgrade,
    rollback_vault_upgrade,
    verify_vault_upgrade,
)
from paperforge.worker.asset_index import atomic_write_index, get_index_path
from paperforge.worker.ocr_hash import publish_ocr_result_hash
from paperforge.worker.status import run_doctor
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Ensure tests never read or write the host user's ~/.paperforge directory."""
    fake_home = tmp_path / "_isolated_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    return fake_home


# ---------------------------------------------------------------------------
# Shared real-artifact helpers
# ---------------------------------------------------------------------------


def _make_v2_vault(tmp_path: Path, name: str = "vault") -> Path:
    vault = tmp_path / name
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault, system_dir=".paperforge")
    (vault / ".paperforge" / "indexes").mkdir(parents=True, exist_ok=True)
    (vault / ".paperforge" / "ocr").mkdir(parents=True, exist_ok=True)
    (vault / "Resources" / "Literature" / "Ortho").mkdir(parents=True, exist_ok=True)
    (vault / "Bases").mkdir(parents=True, exist_ok=True)
    return vault


def _write_ocr_artifacts(ocr_dir: Path, key: str, text_body: str, *, publish_hash: bool = True) -> None:
    index_dir = ocr_dir / "index"
    structure_dir = ocr_dir / "structure"
    index_dir.mkdir(parents=True, exist_ok=True)
    structure_dir.mkdir(parents=True, exist_ok=True)
    tree = {
        "paper_id": key,
        "nodes": [
            {
                "node_id": "sec:intro",
                "kind": "section",
                "title": "Introduction",
                "level": 1,
                "section_path": ["Introduction"],
                "page_span": [1, 1],
                "own_block_ids": ["p1:b1"],
                "subtree_block_ids": ["p1:b1"],
                "children": [],
            }
        ],
    }
    (index_dir / "structure-tree.json").write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    blocks = [{"block_id": "b1", "page": 1, "role": "body_paragraph", "text": text_body}]
    (structure_dir / "blocks.structured.jsonl").write_text(
        "\n".join(json.dumps(b, ensure_ascii=False) for b in blocks) + "\n",
        encoding="utf-8",
    )
    (index_dir / "role-index.json").write_text(
        json.dumps({"figure_captions": [], "table_captions": [], "headings": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (ocr_dir / "fulltext.md").write_text(f"# {key}\n\n{text_body}\n", encoding="utf-8")
    if publish_hash:
        publish_ocr_result_hash(ocr_dir)


def _write_index(vault: Path, items: list[dict]) -> None:
    idx_path = get_index_path(vault)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_index(idx_path, {"schema_version": "2", "paper_count": len(items), "items": items, "generated_at": ""})


def _desync_body_units_fts(conn: sqlite3.Connection, probe_key: str) -> None:
    """Desync body_units_fts so PRAGMA integrity_check == 'ok' while FTS delete raises DatabaseError."""
    conn.execute("DELETE FROM body_units_fts_data WHERE id = 1")
    conn.commit()
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with pytest.raises(sqlite3.DatabaseError, match="malformed"):
        conn.execute(
            """INSERT INTO body_units_fts(body_units_fts, rowid, unit_id, paper_id, section_path, unit_text)
               SELECT 'delete', rowid, unit_id, paper_id, section_path, unit_text
               FROM body_units WHERE paper_id = ? AND indexable = 1""",
            (probe_key,),
        )


def _seed_tier0_rows(conn: sqlite3.Connection, key: str = "KEEP0001") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO papers (zotero_key, title, domain) VALUES (?, ?, ?)",
        (key, f"Title {key}", "Ortho"),
    )
    conn.execute(
        "INSERT OR REPLACE INTO vec_body_meta (rowid, paper_id, chunk_index, unit_id, text) "
        "VALUES (101, ?, 0, ?, 'embedded body text')",
        (key, f"{key}:body:sec:intro:1-b1:1-b1"),
    )
    conn.execute(
        "INSERT OR REPLACE INTO reading_log (id, paper_id, section, excerpt, usage, created_at) "
        "VALUES (?, ?, 'Methods', 'preserved excerpt', 'method', '2026-01-01T00:00:00Z')",
        (f"rl_{key}", key),
    )


# ---------------------------------------------------------------------------
# 1. RC-1: FTS5 Auto-Repair & Non-Self-Corrupting Upsert
# ---------------------------------------------------------------------------


def test_rc1_build_from_index_heals_desynced_fts_and_preserves_tier0(tmp_path: Path) -> None:
    vault = _make_v2_vault(tmp_path, "rc1_build")
    ocr_root = vault / ".paperforge" / "ocr"
    _write_ocr_artifacts(ocr_root / "KEEP0001", "KEEP0001", "Kept cartilage repair baseline text.")
    _write_ocr_artifacts(ocr_root / "UPD00002", "UPD00002", "Original text before update.")

    items = [
        {"zotero_key": "KEEP0001", "title": "Keep Paper", "domain": "Ortho"},
        {"zotero_key": "UPD00002", "title": "Update Paper", "domain": "Ortho"},
    ]
    _write_index(vault, items)
    build_from_index(vault)

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        _seed_tier0_rows(conn, "KEEP0001")
        _desync_body_units_fts(conn, "UPD00002")
    finally:
        conn.close()

    # Trigger incremental build_from_index (remove UPD00002 -> exercises _delete_paper + incremental path)
    _write_index(vault, [{"zotero_key": "KEEP0001", "title": "Keep Paper", "domain": "Ortho"}])
    res = build_from_index(vault)
    assert "quarantined_corrupt_db" not in res
    assert res["papers_indexed"] == 1

    conn = get_connection(db_path)
    try:
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")
        vec_rows = conn.execute("SELECT paper_id, text FROM vec_body_meta WHERE paper_id='KEEP0001'").fetchall()
        rl_rows = conn.execute("SELECT id, excerpt FROM reading_log WHERE paper_id='KEEP0001'").fetchall()
        assert len(vec_rows) == 1 and vec_rows[0]["text"] == "embedded body text"
        assert len(rl_rows) == 1 and rl_rows[0]["excerpt"] == "preserved excerpt"
    finally:
        conn.close()


def test_rc1_incremental_units_only_and_delete_paper_heal_desynced_fts(tmp_path: Path) -> None:
    vault = _make_v2_vault(tmp_path, "rc1_inc_del")
    ocr_root = vault / ".paperforge" / "ocr"
    _write_ocr_artifacts(ocr_root / "KEEP0001", "KEEP0001", "Keep body paragraph alpha.")
    _write_ocr_artifacts(ocr_root / "UPD00002", "UPD00002", "Initial body paragraph beta.")
    _write_ocr_artifacts(ocr_root / "DEL00003", "DEL00003", "To be deleted gamma.")

    items = [
        {"zotero_key": "KEEP0001", "title": "Keep", "domain": "Ortho"},
        {"zotero_key": "UPD00002", "title": "Update", "domain": "Ortho"},
        {"zotero_key": "DEL00003", "title": "Delete", "domain": "Ortho"},
    ]
    _write_index(vault, items)
    build_from_index(vault)

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        _seed_tier0_rows(conn, "KEEP0001")
        _desync_body_units_fts(conn, "DEL00003")

        # (a) _delete_paper heals desynced body_units_fts without crashing
        _delete_paper(conn, vault, "DEL00003")
        conn.commit()
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")
        assert conn.execute("SELECT COUNT(*) FROM body_units_fts_data WHERE id = 1").fetchone()[0] == 1

        # (b) Re-desync and exercise _incremental_units_only with changed OCR artifacts
        _desync_body_units_fts(conn, "UPD00002")
        _write_ocr_artifacts(ocr_root / "UPD00002", "UPD00002", "Updated body paragraph beta v2.")
        _incremental_units_only(
            conn,
            [
                {"zotero_key": "KEEP0001", "title": "Keep", "domain": "Ortho"},
                {"zotero_key": "UPD00002", "title": "Update", "domain": "Ortho"},
            ],
            ocr_root,
            vault=vault,
        )
        conn.commit()
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")

        # KEEP0001 Tier-0 rows remain 100% intact
        assert conn.execute("SELECT COUNT(*) FROM vec_body_meta WHERE paper_id='KEEP0001'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM reading_log WHERE paper_id='KEEP0001'").fetchone()[0] == 1
        hits = conn.execute(
            "SELECT unit_text FROM body_units_fts WHERE body_units_fts MATCH 'updated'"
        ).fetchall()
        assert len(hits) == 1
    finally:
        conn.close()


def test_rc1_repeated_upsert_body_units_never_corrupts_fts5(tmp_path: Path) -> None:
    db_path = tmp_path / "upsert_fts.db"
    conn = get_connection(db_path)
    try:
        ensure_schema(conn)
        for rev in range(1, 6):
            units = [
                {
                    "unit_id": "P001:body:sec:1:1-b1:1-b1",
                    "paper_id": "P001",
                    "node_id": "sec:1",
                    "section_path": "Methods",
                    "section_path_json": '["Methods"]',
                    "section_level": 1,
                    "section_title": "Methods",
                    "unit_text": f"Revision {rev} surgical biomechanical protocol alpha{rev}",
                    "unit_kind": "body",
                    "part_ordinal": 0,
                    "page_span": [1, 1],
                    "block_span": ["b1"],
                    "token_estimate": 10,
                    "indexable": True,
                    "veto_reason": "",
                    "quality_hints": [],
                },
                {
                    "unit_id": "P001:body:sec:2:2-b2:2-b2",
                    "paper_id": "P001",
                    "node_id": "sec:2",
                    "section_path": "Results",
                    "section_path_json": '["Results"]',
                    "section_level": 1,
                    "section_title": "Results",
                    "unit_text": f"Outcome measurement beta{rev}",
                    "unit_kind": "body",
                    "part_ordinal": 0,
                    "page_span": [2, 2],
                    "block_span": ["b2"],
                    "token_estimate": 6,
                    "indexable": True,
                    "veto_reason": "",
                    "quality_hints": [],
                },
            ]
            # Shrink units on final iteration to ensure removed units don't linger in FTS
            if rev == 5:
                units = units[:1]
            _upsert_body_units(conn, units)
            conn.commit()
            conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")

        assert conn.execute(
            "SELECT COUNT(*) FROM body_units_fts WHERE body_units_fts MATCH 'alpha5'"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM body_units_fts WHERE body_units_fts MATCH 'alpha1'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM body_units_fts WHERE body_units_fts MATCH 'beta5'"
        ).fetchone()[0] == 0

        # Direct helper contract checks
        assert safe_delete_body_units_fts(conn, "P001") is True
        conn.execute("DELETE FROM body_units WHERE paper_id='P001'")
        assert rebuild_fts_indexes(conn, ("body_units_fts",)) == ["body_units_fts"]
        assert check_and_heal_fts(conn)["repaired"] == []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2. RC-2: Tier-0 Data-Sovereignty Gate, FSM Enforcement & Pre-v3 Migration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "count_key,table_name",
    [
        ("db_vec_body_rows", "vec_body_meta"),
        ("db_vec_objects_rows", "vec_objects_meta"),
        ("db_vec_fulltext_rows", "vec_fulltext_meta"),
        ("db_reading_log_rows", "reading_log"),
        ("db_project_log_rows", "project_log"),
        ("db_annotations_rows", "paper_annotations"),
        ("db_memory_cards_rows", "paper_memory_cards"),
    ],
)
def test_rc2_verify_vault_upgrade_enforces_all_7_tier0_db_counts(
    tmp_path: Path, count_key: str, table_name: str
) -> None:
    vault = _make_v2_vault(tmp_path, f"tier0_{count_key}")
    (vault / ".paperforge" / "vault-manifest.json").write_text(
        json.dumps({"schema_version": 1, "layout_version": 2}),
        encoding="utf-8",
    )
    ws = vault / "Resources" / "Literature" / "Ortho" / "T0000001 - Test"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "T0000001.md").write_text('---\nzotero_key: "T0000001"\ntitle: "Test"\n---\n', encoding="utf-8")

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        ensure_schema(conn)
        conn.execute("INSERT INTO papers (zotero_key, title, domain) VALUES ('T0000001', 'Test', 'Ortho')")
        conn.execute("INSERT INTO vec_body_meta (rowid, paper_id, chunk_index, unit_id, text) VALUES (1, 'T0000001', 0, 'u1', 'b')")
        conn.execute("INSERT INTO vec_objects_meta (rowid, paper_id, chunk_index, unit_id, text) VALUES (1, 'T0000001', 0, 'o1', 'o')")
        conn.execute("INSERT INTO vec_fulltext_meta (rowid, paper_id, chunk_index, text, source) VALUES (1, 'T0000001', 0, 'f', 'ocr')")
        conn.execute(
            "INSERT INTO reading_log (id, paper_id, section, excerpt, usage, created_at) "
            "VALUES ('rl1', 'T0000001', 'Methods', 'ex', 'u', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO project_log (id, project, date, type, title, created_at) "
            "VALUES ('pl1', 'proj', '2026-01-01', 'note', 't', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO paper_annotations (ann_id, paper_id, page, created_at, updated_at) "
            "VALUES ('ann1', 'T0000001', 1, '2026-01-01', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO paper_memory_cards (zotero_key, facet, content, revision, updated_at) "
            "VALUES ('T0000001', 'summary', 'card', 1, '2026-01-01')"
        )
        conn.commit()
    finally:
        conn.close()

    pre_db = _capture_db_tier0_counts(db_path)
    assert all(pre_db[k] == 1 for k in pre_db) and len(pre_db) == 7

    pre_counts = {
        "tier0_ocr_valid": 0,
        "workspaces": 1,
        "annotations_files": 0,
        "memory_card_files": 0,
        **pre_db,
    }
    ok_res = verify_vault_upgrade(vault, pre_counts=pre_counts)
    assert ok_res["ok"] is True
    assert ok_res["checks"]["tier0_db_sovereignty_preserved"] is True

    # Drop row in the target Tier-0 table -> verify_vault_upgrade must fail closed
    conn = get_connection(db_path)
    try:
        conn.execute(f"DELETE FROM {table_name}")
        conn.commit()
    finally:
        conn.close()

    fail_res = verify_vault_upgrade(vault, pre_counts=pre_counts)
    assert fail_res["ok"] is False
    assert fail_res["checks"]["tier0_db_sovereignty_preserved"] is False
    assert any(count_key in msg for msg in fail_res["failures"])


def test_rc2_upgrade_fsm_transitions_persistence_and_file_contract(tmp_path: Path) -> None:
    fsm = UpgradeStateMachine()
    assert fsm.state == UpgradePhase.IDLE

    with pytest.raises(MigrationStateError):
        fsm.transition(UpgradePhase.ENGINE_CUTOVER, gate="illegal_jump")
    with pytest.raises(MigrationStateError):
        fsm.transition(UpgradePhase.COMPLETED, gate="illegal_skip")

    fsm.transition(UpgradePhase.PREFLIGHT_AUDIT, gate="G0")
    fsm.transition(UpgradePhase.SNAPSHOT_AND_QUIESCE, gate="G1")
    fsm.transition(UpgradePhase.ENGINE_CUTOVER, gate="G1_cutover")
    fsm.transition(UpgradePhase.DERIVED_VIEW_AND_INDEX_RECONCILE, gate="G2")
    fsm.transition(UpgradePhase.PER_WORKSPACE_PROGRESSIVE_HEAL, gate="G3")
    fsm.transition(UpgradePhase.COMPLETED, gate="G4", detail={"ok": True})

    with pytest.raises(MigrationStateError):
        fsm.transition(UpgradePhase.PREFLIGHT_AUDIT, gate="terminal_reenter")

    trace_path = tmp_path / "fsm-trace.json"
    fsm.persist(trace_path)
    persisted = json.loads(trace_path.read_text(encoding="utf-8"))
    assert persisted["state"] == "COMPLETED"
    assert len(persisted["trace"]) == 6
    assert persisted["trace"][0]["from"] == "IDLE"
    assert persisted["trace"][-1]["to"] == "COMPLETED"
    assert persisted["trace"][-1]["detail"] == {"ok": True}

    # Violation -> rollback path
    fsm_rb = UpgradeStateMachine()
    fsm_rb.transition(UpgradePhase.PREFLIGHT_AUDIT, gate="G0")
    fsm_rb.transition(UpgradePhase.SNAPSHOT_AND_QUIESCE, gate="G1")
    fsm_rb.transition(UpgradePhase.ENGINE_CUTOVER, gate="G1_cutover")
    fsm_rb.transition(UpgradePhase.SOVEREIGNTY_VIOLATION, gate="G2_fail")
    fsm_rb.transition(UpgradePhase.ROLLING_BACK, gate="G2_rb")
    fsm_rb.transition(UpgradePhase.ROLLED_BACK, gate="G2_done")
    assert fsm_rb.state == UpgradePhase.ROLLED_BACK

    # File action contract completeness and conflict check
    assert len(PER_FILE_ACTION_CONTRACT) >= 15
    assert audit_file_action_conflicts() == []

    bad_contract = (
        FileActionRule(
            file_class="bad_tier0",
            tier="tier0",
            stage="CUTOVER",
            action="DELETE_IMMEDIATELY",
            conflict_policy="DROP",
            rollback_strategy="NONE",
        ),
    )
    assert len(audit_file_action_conflicts(bad_contract)) >= 1


def test_rc2_prev3_destructive_schema_migration_preserves_tier0_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_v2.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO meta (key, value) VALUES ('schema_version', '2');
            CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT NOT NULL);
            INSERT INTO papers (zotero_key, title) VALUES ('LEG00001', 'Legacy Paper');
            CREATE TABLE reading_log (
                id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, project TEXT DEFAULT '',
                section TEXT NOT NULL, excerpt TEXT NOT NULL, context TEXT DEFAULT '',
                usage TEXT NOT NULL, note TEXT DEFAULT '', tags_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL, agent TEXT DEFAULT '', verified INTEGER DEFAULT 0
            );
            INSERT INTO reading_log (id, paper_id, section, excerpt, usage, created_at)
            VALUES ('rl_leg1', 'LEG00001', 'Results', 'Important finding', 'evidence', '2025-05-01');
            CREATE TABLE project_log (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, date TEXT NOT NULL,
                type TEXT NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL
            );
            INSERT INTO project_log (id, project, date, type, title, created_at)
            VALUES ('pl_leg1', 'Spine', '2025-05-01', 'decision', 'Use v2 data', '2025-05-01');
            CREATE TABLE paper_annotations (
                ann_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, page INTEGER NOT NULL,
                exact_text TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            INSERT INTO paper_annotations (ann_id, paper_id, page, exact_text, created_at, updated_at)
            VALUES ('ann_leg1', 'LEG00001', 3, 'Legacy highlight', '2025-05-01', '2025-05-01');
            CREATE TABLE paper_memory_cards (
                zotero_key TEXT NOT NULL, facet TEXT NOT NULL, content TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
                PRIMARY KEY (zotero_key, facet)
            );
            INSERT INTO paper_memory_cards (zotero_key, facet, content, revision, updated_at)
            VALUES ('LEG00001', 'findings', 'Preserved card content', 2, '2025-05-01');
            """
        )
        conn.commit()

        action = migrate_schema(conn, get_schema_version(conn), CURRENT_SCHEMA_VERSION)
        assert action == "destructive"
        ensure_schema(conn)
        assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION

        assert conn.execute("SELECT excerpt FROM reading_log WHERE id='rl_leg1'").fetchone()[0] == "Important finding"
        assert conn.execute("SELECT title FROM project_log WHERE id='pl_leg1'").fetchone()[0] == "Use v2 data"
        assert conn.execute("SELECT exact_text FROM paper_annotations WHERE ann_id='ann_leg1'").fetchone()[0] == "Legacy highlight"
        assert conn.execute("SELECT content FROM paper_memory_cards WHERE zotero_key='LEG00001'").fetchone()[0] == "Preserved card content"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 3. Split-Brain Rich-Wins, WAL Quiesce & JSONL Union Merge
# ---------------------------------------------------------------------------


def test_split_brain_rich_wins_and_jsonl_union_merge(tmp_path: Path) -> None:
    vault = tmp_path / "split_brain"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")

    legacy_pf = vault / "System" / "PaperForge"
    dot_pf = vault / ".paperforge"
    (legacy_pf / "indexes").mkdir(parents=True)
    (legacy_pf / "logs").mkdir(parents=True)
    (dot_pf / "indexes").mkdir(parents=True)
    (dot_pf / "logs").mkdir(parents=True)

    # Rich legacy DB vs empty v7 .paperforge DB
    rich_db = legacy_pf / "indexes" / "paperforge.db"
    c_rich = get_connection(rich_db)
    try:
        ensure_schema(c_rich)
        c_rich.execute("INSERT INTO papers (zotero_key, title, domain) VALUES ('RICH0001', 'Rich Study', 'Ortho')")
        c_rich.execute("INSERT INTO vec_body_meta (rowid, paper_id, chunk_index, unit_id, text) VALUES (1, 'RICH0001', 0, 'u1', 'vec text')")
        c_rich.execute(
            "INSERT INTO reading_log (id, paper_id, section, excerpt, usage, created_at) "
            "VALUES ('rl_rich', 'RICH0001', 'Intro', 'rich excerpt', 'bg', '2026-01-01')"
        )
        c_rich.commit()
    finally:
        c_rich.close()

    empty_db = dot_pf / "indexes" / "paperforge.db"
    c_empty = get_connection(empty_db)
    try:
        ensure_schema(c_empty)
        c_empty.commit()
    finally:
        c_empty.close()

    # Rich legacy formal-library.json vs empty .paperforge formal-library.json
    (legacy_pf / "indexes" / "formal-library.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "items": [
                    {"zotero_key": "RICH0001", "title": "Rich Study", "domain": "Ortho"},
                    {"zotero_key": "RICH0002", "title": "Second Study", "domain": "Ortho"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (dot_pf / "indexes" / "formal-library.json").write_text(
        json.dumps({"schema_version": "2", "items": []}),
        encoding="utf-8",
    )

    # JSONL split-brain with overlapping ID + corrupt truncated line
    (legacy_pf / "logs" / "reading-log.jsonl").write_text(
        '{"id":"rl_1","paper_id":"RICH0001","section":"Intro","excerpt":"one","usage":"u","created_at":"2026-01-01"}\n'
        '{"id":"rl_2","paper_id":"RICH0001","section":"Methods","excerpt":"two","usage":"u","created_at":"2026-01-02"}\n'
        '{"id":"truncated_corrupt_line"\n',
        encoding="utf-8",
    )
    (dot_pf / "logs" / "reading-log.jsonl").write_text(
        '{"id":"rl_2","paper_id":"RICH0001","section":"Methods","excerpt":"two","usage":"u","created_at":"2026-01-02"}\n'
        '{"id":"rl_3","paper_id":"RICH0001","section":"Results","excerpt":"three","usage":"u","created_at":"2026-01-03"}\n',
        encoding="utf-8",
    )

    res = execute_vault_upgrade(vault, dry_run=False, fast_cutover=True)
    assert res["applied"] is True
    assert res["fsm"]["state"] == "COMPLETED_FAST_CUTOVER"

    # Rich DB won and empty DB was archived
    c_final = sqlite3.connect(str(dot_pf / "indexes" / "paperforge.db"))
    try:
        assert c_final.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 1
        assert c_final.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0] == 1
        assert c_final.execute("SELECT COUNT(*) FROM reading_log").fetchone()[0] == 1
    finally:
        c_final.close()

    loser_dir = dot_pf / "backups" / "storage-migration" / "rich_wins_loser"
    assert loser_dir.is_dir()
    archived_names = [p.name for p in loser_dir.iterdir()]
    assert any("paperforge.db" in n for n in archived_names)
    assert any("formal-library.json" in n for n in archived_names)

    # Rich formal-library.json won
    merged_idx = json.loads((dot_pf / "indexes" / "formal-library.json").read_text(encoding="utf-8"))
    assert len(merged_idx["items"]) == 2

    # reading-log.jsonl union-merged without duplicates and without losing valid rows around corrupt line
    rl_lines = (dot_pf / "logs" / "reading-log.jsonl").read_text(encoding="utf-8").splitlines()
    rl_ids = [json.loads(line)["id"] for line in rl_lines]
    assert sorted(rl_ids) == ["rl_1", "rl_2", "rl_3"]


def test_wal_quiesce_flushes_uncheckpointed_wal_frames_before_move(tmp_path: Path) -> None:
    vault = tmp_path / "wal_vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")
    legacy_idx = vault / "System" / "PaperForge" / "indexes"
    legacy_idx.mkdir(parents=True)

    # Stage a DB with uncheckpointed rows living exclusively in -wal
    staging_db = tmp_path / "staging.db"
    conn = sqlite3.connect(str(staging_db))
    try:
        ensure_schema(conn)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=0")
        conn.execute("INSERT INTO papers (zotero_key, title, domain) VALUES ('WAL00001', 'In Base', 'Ortho')")
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        conn.execute("INSERT INTO papers (zotero_key, title, domain) VALUES ('WAL00002', 'Only In WAL', 'Ortho')")
        conn.execute(
            "INSERT INTO reading_log (id, paper_id, section, excerpt, usage, created_at) "
            "VALUES ('rl_wal', 'WAL00002', 'Intro', 'uncheckpointed wal row', 'u', '2026-01-01')"
        )
        conn.commit()

        wal_file = Path(f"{staging_db}-wal")
        assert wal_file.is_file() and wal_file.stat().st_size > 0

        target_legacy_db = legacy_idx / "paperforge.db"
        shutil.copy2(staging_db, target_legacy_db)
        shutil.copy2(wal_file, Path(f"{target_legacy_db}-wal"))
        shm_file = Path(f"{staging_db}-shm")
        if shm_file.is_file():
            shutil.copy2(shm_file, Path(f"{target_legacy_db}-shm"))
    finally:
        conn.close()

    assert quiesce_sqlite_wal(legacy_idx / "paperforge.db") is True
    assert not (legacy_idx / "paperforge.db-wal").exists()

    dot_idx = vault / ".paperforge" / "indexes"
    _move_tree_entries(legacy_idx, dot_idx, dry_run=False, conflict_backup_dir=vault / ".paperforge" / "backups" / "sm")

    moved_conn = sqlite3.connect(str(dot_idx / "paperforge.db"))
    try:
        keys = {r[0] for r in moved_conn.execute("SELECT zotero_key FROM papers").fetchall()}
        assert keys == {"WAL00001", "WAL00002"}
        rl = moved_conn.execute("SELECT excerpt FROM reading_log WHERE id='rl_wal'").fetchone()
        assert rl is not None and rl[0] == "uncheckpointed wal row"
    finally:
        moved_conn.close()


# ---------------------------------------------------------------------------
# 4. RC-3: Performance & Correctness
# ---------------------------------------------------------------------------


def test_rc3_read_note_identity_fast_path_parity_and_fallbacks(tmp_path: Path) -> None:
    # 1. Quoted/unquoted scalars + UTF-8 BOM + CRLF + multiline abstract: |
    note_std = tmp_path / "std.md"
    raw_std = (
        "\ufeff---\r\n"
        'zotero_key: "ABCD1234"\r\n'
        "title: Unquoted Clinical Title\r\n"
        "year: 2025\r\n"
        "do_ocr: true\r\n"
        "analyze: false\r\n"
        "empty_field: null\r\n"
        "abstract: |\r\n"
        "  Background: Bone graft mechanics.\r\n"
        "  Methods: 30 patients evaluated.\r\n"
        "  - Result: 1\r\n"
        "---\r\n\r\nBody prose.\r\n"
    )
    note_std.write_bytes(raw_std.encode("utf-8"))

    fast_parsed = _fast_parse_identity_frontmatter(raw_std)
    assert fast_parsed is not None
    key, fm, enc_status = _read_note_identity(note_std)
    yaml_fm = yaml.safe_load(raw_std.lstrip("\ufeff").split("---", 2)[1])
    assert enc_status == "utf-8-sig"
    assert key == yaml_fm["zotero_key"] == "ABCD1234"
    assert fm["title"] == yaml_fm["title"] == "Unquoted Clinical Title"
    assert fm["do_ocr"] is True and fm["analyze"] is False and fm["empty_field"] is None

    # 2. Flow/complex zotero_key -> fast path returns None and falls back to yaml.safe_load
    note_flow = tmp_path / "flow.md"
    raw_flow = "---\nzotero_key: [FLOW1234]\ntitle: Flow Key\n---\nBody\n"
    note_flow.write_text(raw_flow, encoding="utf-8")
    assert _fast_parse_identity_frontmatter(raw_flow) is None
    key_flow, fm_flow, _ = _read_note_identity(note_flow)
    assert fm_flow["zotero_key"] == ["FLOW1234"]
    assert key_flow == "['FLOW1234']"

    # Complex anchor zotero_key fallback
    note_anchor = tmp_path / "anchor.md"
    raw_anchor = "---\nzotero_key: &zk ANCHOR01\ntitle: Anchor\n---\nBody\n"
    note_anchor.write_text(raw_anchor, encoding="utf-8")
    assert _fast_parse_identity_frontmatter(raw_anchor) is None
    key_anc, fm_anc, _ = _read_note_identity(note_anchor)
    assert key_anc == "ANCHOR01"
    assert fm_anc["zotero_key"] == "ANCHOR01"


def test_rc3_validate_frontmatter_ignores_indented_abstract_and_handles_over_16kb(tmp_path: Path) -> None:
    registry = {
        "frontmatter": {
            "zotero_key": {"type": "str", "required": True, "public": True},
            "domain": {"type": "str", "required": True, "public": True},
            "title": {"type": "str", "required": True, "public": True},
            "abstract": {"type": "str", "required": False, "public": True},
        }
    }

    # Multiline indented abstract containing colon lines & bullet-colon lines must NOT cause DRIFT
    note_multiline = tmp_path / "multiline.md"
    note_multiline.write_text(
        "---\n"
        'zotero_key: "ML000001"\n'
        'domain: "Ortho"\n'
        'title: "Multiline Abstract"\n'
        "abstract: |\n"
        "  Background: Cohort study of 120 patients.\n"
        "  Methods: Multivariate logistic regression.\n"
        "  - Result: 1\n"
        "\tConclusion: Safe.\n"
        "---\n\nBody\n",
        encoding="utf-8",
    )
    assert validate_frontmatter_from_file(note_multiline, registry) == []

    # >16 KB frontmatter fallback: real top-level fields AFTER 16 KB must be read accurately
    filler = "\n".join(f"  Line {i}: {'x' * 120}" for i in range(180))
    assert len(filler.encode("utf-8")) > 16384
    note_large = tmp_path / "large_fm.md"
    note_large.write_text(
        "---\n"
        'domain: "Ortho"\n'
        'title: "Large Frontmatter"\n'
        "abstract: |\n"
        f"{filler}\n"
        'zotero_key: "LRG00001"\n'
        'rogue_drift_field: "oops"\n'
        "---\n\nBody\n",
        encoding="utf-8",
    )
    issues = validate_frontmatter_from_file(note_large, registry)
    codes_fields = {(i["code"], i["field"]) for i in issues}
    assert ("MISSING_REQUIRED", "zotero_key") not in codes_fields
    assert ("DRIFT", "rogue_drift_field") in codes_fields


def test_rc3_throttled_journal_and_externalized_bak_rollback_byte_for_byte(tmp_path: Path) -> None:
    # Part A: rollback_incomplete_migration with externalized notes/*.bak + >50 moved files
    v_inc = tmp_path / "v_incomplete"
    v_inc.mkdir()
    canonical_test_config(v_inc, system_dir="System")
    old_pf = v_inc / "System" / "PaperForge"
    (old_pf / "indexes" / "bulk").mkdir(parents=True)
    for i in range(55):
        (old_pf / "indexes" / "bulk" / f"item_{i:02d}.json").write_text(f'{{"i": {i}}}', encoding="utf-8")
    fig = old_pf / "ocr" / "RBK00001" / "assets" / "figures" / "figure_001.jpg"
    fig.parent.mkdir(parents=True)
    fig.write_bytes(b"jpg-bytes")

    ws = v_inc / "Resources" / "Literature" / "Ortho" / "RBK00001 - Paper"
    ws.mkdir(parents=True)
    (ws / "paper-meta.json").write_text('{"zotero_key": "RBK00001"}', encoding="utf-8")
    note_path = ws / "RBK00001.md"
    orig_note_text = '---\nzotero_key: "RBK00001"\ntitle: "Paper"\n---\n\n![[render/figures/figure_001.md]]\n'
    note_path.write_text(orig_note_text, encoding="utf-8")
    orig_note_bytes = note_path.read_bytes()

    res = migrate_vault_storage(v_inc, dry_run=False)
    assert res["notes_rewritten"] == 1
    assert note_path.read_bytes() != orig_note_bytes

    journal_path = v_inc / ".paperforge" / ".migration-journal.json"
    jdata = json.loads(journal_path.read_text(encoding="utf-8"))
    assert len(jdata["rewritten_notes"]) == 1
    assert "backup" in jdata["rewritten_notes"][0]
    assert "original_text" not in jdata["rewritten_notes"][0]
    assert Path(jdata["rewritten_notes"][0]["backup"]).is_file()

    # Simulate interrupted state and run rollback_incomplete_migration
    jdata["state"] = "in_progress"
    journal_path.write_text(json.dumps(jdata), encoding="utf-8")
    rb_inc = rollback_incomplete_migration(v_inc)
    assert rb_inc["recovered"] is True
    assert note_path.read_bytes() == orig_note_bytes
    assert load_config(v_inc).values["system_dir"].value == "System"
    assert (old_pf / "indexes" / "bulk" / "item_54.json").is_file()

    # Part B: Full execute_vault_upgrade + rollback_vault_upgrade restores notes byte-for-byte
    v_full = tmp_path / "v_full"
    v_full.mkdir()
    canonical_test_config(v_full, system_dir="System")
    old_pf2 = v_full / "System" / "PaperForge"
    fig2 = old_pf2 / "ocr" / "RBK00002" / "assets" / "figures" / "figure_001.jpg"
    fig2.parent.mkdir(parents=True)
    fig2.write_bytes(b"jpg-bytes-2")
    ws2 = v_full / "Resources" / "Literature" / "Ortho" / "RBK00002 - Paper"
    ws2.mkdir(parents=True)
    (ws2 / "paper-meta.json").write_text('{"zotero_key": "RBK00002"}', encoding="utf-8")
    note2 = ws2 / "RBK00002.md"
    orig_note2_text = (
        '---\nzotero_key: "RBK00002"\ntitle: "Paper 2"\n---\n\nKeep exact spacing  \n![[render/figures/figure_001.md]]\n'
    )
    note2.write_text(orig_note2_text, encoding="utf-8")
    orig_note2_bytes = note2.read_bytes()

    up_res = execute_vault_upgrade(v_full, dry_run=False, fast_cutover=False)
    assert up_res["applied"] is True
    assert "![[RBK00002_figure_001.jpg]]" in note2.read_text(encoding="utf-8")

    rb_full = rollback_vault_upgrade(v_full, backup_dir=Path(up_res["backup_dir"]))
    assert rb_full["rolled_back"] is True
    assert note2.read_bytes() == orig_note2_bytes
    assert load_config(v_full).values["system_dir"].value == "System"


# ---------------------------------------------------------------------------
# 5. RC-4: Doctor Single-Contract & Grouping
# ---------------------------------------------------------------------------


def test_rc4_doctor_single_contract_and_15_plus_1_drift_grouping(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import paperforge.runtime_pointer as _rp
    from paperforge import credentials as _creds

    monkeypatch.setattr(_rp, "read_pointer", lambda *a, **k: None)
    monkeypatch.setattr(
        _creds,
        "status",
        lambda key, **_kw: _creds.CredentialStatus(key=key, state="available", source="environment"),
    )

    vault = _make_v2_vault(tmp_path, "rc4_doctor")
    zot_dir = tmp_path / "zot_data"
    zot_dir.mkdir()
    from paperforge.config import set_config

    set_config(vault, "zotero_source_mode", "sqlite")
    set_config(vault, "zotero_data_dir", str(zot_dir))

    lit_ortho = vault / "Resources" / "Literature" / "Ortho"
    ws_dir = lit_ortho / "DOC00001 - Single Contract"
    ws_dir.mkdir(parents=True)

    # Canonical fulltext exists ONLY under .paperforge/ocr/DOC00001/fulltext.md (NO workspace fulltext.md)
    ocr_ft = vault / ".paperforge" / "ocr" / "DOC00001" / "fulltext.md"
    ocr_ft.parent.mkdir(parents=True, exist_ok=True)
    ocr_ft.write_text("# Fulltext\n\nValid OCR text.\n", encoding="utf-8")
    assert not (ws_dir / "fulltext.md").exists()

    _write_index(
        vault,
        [
            {
                "zotero_key": "DOC00001",
                "title": "Single Contract",
                "domain": "Ortho",
                "paper_root": "Resources/Literature/Ortho/DOC00001 - Single Contract",
                "ocr_status": "done",
                "has_pdf": False,
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "healthy",
                    "asset_health": "healthy",
                },
            }
        ],
    )

    # Use real field_registry.yaml fields so notes 1..3 share drift_shared_alpha + drift_shared_beta
    # and total distinct drift fields >= 18 (> 15 cap -> 15 groups + 1 overflow line = 16 checks).
    reg = load_field_registry()
    req_fields = [k for k, m in reg.get("frontmatter", {}).items() if m.get("required")]
    base_fm = "\n".join(f'{k}: "val"' if k != "has_pdf" else f"{k}: false" for k in req_fields)

    # 3 notes share drift_shared_alpha, 2 notes share drift_shared_beta, plus 16 unique drift fields
    for idx in range(18):
        key = f"DOC{idx + 1:05d}"
        ndir = ws_dir if idx == 0 else (lit_ortho / f"{key} - Note {idx}")
        ndir.mkdir(parents=True, exist_ok=True)
        extra_lines = [f'drift_unique_{idx:02d}: "x"']
        if idx < 3:
            extra_lines.append('drift_shared_alpha: "shared"')
        if idx < 2:
            extra_lines.append('drift_shared_beta: "shared2"')
        (ndir / f"{key}.md").write_text(
            f"---\n{base_fm}\n" + "\n".join(extra_lines) + "\n---\n\nBody\n",
            encoding="utf-8",
        )

    run_doctor(vault, json_output=True)
    payload = json.loads(capsys.readouterr().out)["data"]
    checks = payload["checks"]

    # Zero missing fulltext warnings when .paperforge/ocr/<KEY>/fulltext.md exists
    msgs = [c["message"] for c in checks]
    assert not any("missing OCR fulltext" in m or "missing fulltext.md" in m for m in msgs)
    assert any("Workspace integrity: all papers valid" in m for m in msgs)

    # Grouping + 15+1 cap in "字段注册表"
    reg_checks = [c for c in checks if c["category"] == "字段注册表"]
    assert len(reg_checks) == 16  # 15 groups + 1 overflow summary
    assert any("drift_shared_alpha" in c["message"] and "(3 notes," in c["message"] for c in reg_checks[:15])
    assert any("drift_shared_beta" in c["message"] and "(2 notes," in c["message"] for c in reg_checks[:15])
    assert "more field issue group(s)" in reg_checks[-1]["message"]


# ---------------------------------------------------------------------------
# 6. RC-5: Hostile FS & Epoch=2 Zombie Recovery
# ---------------------------------------------------------------------------


def test_rc5_fs_safe_hostile_names_and_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_root = tmp_path / "scan_root"
    scan_root.mkdir()
    for reserved in ("nul", "CON", "AUX.md", "prn.txt", "COM1", "lpt9.json", "CON ", "nul."):
        assert is_windows_reserved_name(reserved) is True
        assert safe_is_dir(scan_root / reserved) is False
        assert safe_is_file(scan_root / reserved) is False
        assert safe_iterdir(scan_root / reserved) == []
        assert safe_rglob(scan_root / reserved) == []

    for normal in ("notes.md", "console.md", "auxiliary", "null.md", ""):
        assert is_windows_reserved_name(normal) is False

    # Real traversal skips .obsidian/.trash/.git/node_modules
    (scan_root / "valid.md").write_text("ok", encoding="utf-8")
    (scan_root / "sub").mkdir()
    (scan_root / "sub" / "nested.md").write_text("ok", encoding="utf-8")
    for skip_dir in (".obsidian", ".trash", ".git", "node_modules"):
        (scan_root / skip_dir).mkdir()
        (scan_root / skip_dir / "ignored.md").write_text("no", encoding="utf-8")

    found_rglob = safe_rglob(scan_root, suffix=".md")
    assert [p.relative_to(scan_root).as_posix() for p in found_rglob] == ["sub/nested.md", "valid.md"]
    assert [p.name for p in safe_iterdir(scan_root)] == [".git", ".obsidian", ".trash", "node_modules", "sub", "valid.md"]

    # Simulate os.walk yielding hostile reserved names to verify filter directly
    real_walk = os.walk

    def _walk_with_hostile(top, **kwargs):
        for root, dirs, files in real_walk(top, **kwargs):
            if Path(root) == scan_root:
                dirs.append("CON")
                files.extend(["nul", "AUX.md"])
            yield root, dirs, files

    monkeypatch.setattr("paperforge.core.fs_safe.os.walk", _walk_with_hostile)
    filtered = safe_rglob(scan_root, suffix=".md")
    assert all(not is_windows_reserved_name(p.name) for p in filtered)
    assert [p.relative_to(scan_root).as_posix() for p in filtered] == ["sub/nested.md", "valid.md"]


def test_rc5_epoch2_zombie_ocr_recovery_and_active_job_guard(tmp_path: Path) -> None:
    assert CURRENT_RECONCILE_EPOCH == 2

    vault = _make_v2_vault(tmp_path, "rc5_epoch2")
    ws_done = vault / "Resources" / "Literature" / "Ortho" / "ZMBDONE1 - Done Study"
    ws_intr = vault / "Resources" / "Literature" / "Ortho" / "ZMBINTR2 - Interrupted Study"
    ws_done.mkdir(parents=True)
    ws_intr.mkdir(parents=True)

    note_bytes = b'---\nzotero_key: "ZMBDONE1"\ntitle: "Done"\n---\n\nUser note\n'
    note_file = ws_done / "ZMBDONE1.md"
    note_file.write_bytes(note_bytes)
    (ws_intr / "ZMBINTR2.md").write_text('---\nzotero_key: "ZMBINTR2"\ntitle: "Intr"\n---\n', encoding="utf-8")

    ann_bytes = b'{"ann_id":"a1","paper_id":"ZMBDONE1","page":1,"kind":"highlight"}\n'
    ann_file = ws_done / "annotations.jsonl"
    ann_file.write_bytes(ann_bytes)

    (vault / ".paperforge" / "logs").mkdir(parents=True, exist_ok=True)
    rl_bytes = b'{"id":"rl1","paper_id":"ZMBDONE1","section":"Intro","excerpt":"x","usage":"u"}\n'
    rl_file = vault / ".paperforge" / "logs" / "reading-log.jsonl"
    rl_file.write_bytes(rl_bytes)

    # ZMBDONE1 has fulltext.md + json/result.json -> heals to 'done'
    done_ocr = vault / ".paperforge" / "ocr" / "ZMBDONE1"
    (done_ocr / "json").mkdir(parents=True)
    (done_ocr / "fulltext.md").write_text("# Done\n", encoding="utf-8")
    (done_ocr / "json" / "result.json").write_text('{"pages": [{"p": 1}]}', encoding="utf-8")
    # ZMBINTR2 lacks json/result.json -> heals to 'interrupted'
    intr_ocr = vault / ".paperforge" / "ocr" / "ZMBINTR2"
    intr_ocr.mkdir(parents=True)
    (intr_ocr / "fulltext.md").write_text("# Partial\n", encoding="utf-8")

    def _reset_running_state(active_job_age_minutes: int | None) -> None:
        _write_index(
            vault,
            [
                {
                    "zotero_key": "ZMBDONE1",
                    "title": "Done Study",
                    "domain": "Ortho",
                    "ocr_status": "running",
                    "paper_root": "Resources/Literature/Ortho/ZMBDONE1 - Done Study",
                },
                {
                    "zotero_key": "ZMBINTR2",
                    "title": "Interrupted Study",
                    "domain": "Ortho",
                    "ocr_status": "running",
                    "paper_root": "Resources/Literature/Ortho/ZMBINTR2 - Interrupted Study",
                },
            ],
        )
        (vault / ".paperforge" / "vault-manifest.json").write_text(
            json.dumps({"schema_version": 1, "layout_version": 2, "reconcile_epoch": 1}),
            encoding="utf-8",
        )
        db_path = get_memory_db_path(vault)
        conn = get_connection(db_path)
        try:
            ensure_schema(conn)
            conn.execute("DELETE FROM engine_jobs")
            conn.execute(
                "INSERT OR REPLACE INTO papers (zotero_key, title, domain, ocr_status) "
                "VALUES ('ZMBDONE1', 'Done Study', 'Ortho', 'running')"
            )
            conn.execute(
                "INSERT OR REPLACE INTO papers (zotero_key, title, domain, ocr_status) "
                "VALUES ('ZMBINTR2', 'Interrupted Study', 'Ortho', 'running')"
            )
            if active_job_age_minutes is not None:
                ts = (datetime.now(timezone.utc) - timedelta(minutes=active_job_age_minutes)).isoformat()
                conn.execute(
                    "INSERT INTO engine_jobs (job_id, job_type, target_key, status, updated_at) "
                    "VALUES ('job1', 'ocr', 'ZMBINTR2', 'running', ?)",
                    (ts,),
                )
            # Populate a body_unit and desync body_units_fts cleanly while keeping physical SQLite ok
            conn.execute(
                "INSERT OR REPLACE INTO body_units "
                "(unit_id, paper_id, section_path, unit_text, page_span_json, block_span_json, "
                "token_estimate, indexable, veto_reason, quality_hints_json) "
                "VALUES ('ZMBDONE1:body:1', 'ZMBDONE1', 'Intro', 'zombie text', '[1,1]', '[\"b1\"]', 2, 1, '', '[]')"
            )
            conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('rebuild')")
            conn.commit()
            conn.execute("DELETE FROM body_units_fts_data")
            conn.commit()
        finally:
            conn.close()

    # Case A: Active OCR job < 30 min (5 min old) -> running rows are NOT touched
    _reset_running_state(active_job_age_minutes=5)
    res_active = ensure_vault_reconciled(vault)
    assert res_active["reconciled"] is True
    assert res_active["reconcile_epoch"] == 2
    assert res_active["zombie_running_healed"] == 0
    assert "body_units_fts" in res_active["fts_repaired"]

    conn = get_connection(get_memory_db_path(vault))
    try:
        statuses = dict(conn.execute("SELECT zotero_key, ocr_status FROM papers").fetchall())
        assert statuses == {"ZMBDONE1": "running", "ZMBINTR2": "running"}
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")
    finally:
        conn.close()

    # Case B: Stale OCR job > 30 min (45 min old) -> zombies heal deterministically
    _reset_running_state(active_job_age_minutes=45)
    res_stale = ensure_vault_reconciled(vault)
    assert res_stale["reconciled"] is True
    assert res_stale["zombie_running_healed"] == 2
    assert "body_units_fts" in res_stale["fts_repaired"]

    conn = get_connection(get_memory_db_path(vault))
    try:
        statuses = dict(conn.execute("SELECT zotero_key, ocr_status FROM papers").fetchall())
        assert statuses == {"ZMBDONE1": "done", "ZMBINTR2": "interrupted"}
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")
    finally:
        conn.close()

    idx_items = {
        e["zotero_key"]: e["ocr_status"]
        for e in json.loads(get_index_path(vault).read_text(encoding="utf-8"))["items"]
    }
    assert idx_items == {"ZMBDONE1": "done", "ZMBINTR2": "interrupted"}

    # User files remain byte-identical
    assert note_file.read_bytes() == note_bytes
    assert ann_file.read_bytes() == ann_bytes
    assert rl_file.read_bytes() == rl_bytes


# ---------------------------------------------------------------------------
# 7. Mass-Invalidation Circuit Breaker & Hot-Journal Recovery
# ---------------------------------------------------------------------------


def test_mass_invalidation_circuit_breaker_preserves_vectors_on_partial_ocr_sync(tmp_path: Path) -> None:
    vault = tmp_path / "breaker_vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    # 25 papers: all start with stored manifests, body_units, and vec_body_meta rows,
    # but only ONE (KEEP0001) has local OCR artifacts on disk (24/25 missing locally).
    items: list[dict[str, str]] = []
    ocr_keep = vault / ".paperforge" / "ocr" / "KEEP0001"
    (ocr_keep / "index").mkdir(parents=True)
    (ocr_keep / "structure").mkdir(parents=True)
    (ocr_keep / "index" / "structure-tree.json").write_text(
        json.dumps({"root": {"node_id": "root", "title": "Root", "children": []}}),
        encoding="utf-8",
    )
    (ocr_keep / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps(
            {
                "block_id": "b1",
                "page": 1,
                "role": "text",
                "section_path": "Intro",
                "text": "Kept paper updated clinical evidence.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    for i in range(25):
        k = "KEEP0001" if i == 0 else f"PART{i:04d}"
        items.append({"zotero_key": k, "title": f"Study {k}", "domain": "Ortho"})
    _write_index(vault, items)

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        ensure_schema(conn)
        for i, item in enumerate(items):
            k = item["zotero_key"]
            conn.execute(
                "INSERT OR REPLACE INTO papers (zotero_key, title, domain) VALUES (?, ?, 'Ortho')",
                (k, item["title"]),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (
                    f"manifest:{k}",
                    json.dumps(
                        {
                            "ocr_result_hash": "old_hash",
                            "retrieval_policy_version": "old",
                        }
                    ),
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO body_units "
                "(unit_id, paper_id, section_path, unit_text, page_span_json, block_span_json, "
                "token_estimate, indexable, veto_reason, quality_hints_json) "
                "VALUES (?, ?, 'Intro', ?, '[1,1]', '[\"b1\"]', 5, 1, '', '[]')",
                (f"{k}:body:1", k, f"Original stored text for {k}"),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vec_body_meta (rowid, paper_id, chunk_index, unit_id, text) "
                "VALUES (?, ?, 0, ?, ?)",
                (i + 1, k, f"{k}:body:1", f"Vec text {k}"),
            )
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('rebuild')")
        conn.commit()
    finally:
        conn.close()

    # Whole-library build trips circuit breaker: preserves the 24 missing papers while rebuilding KEEP0001
    from paperforge.memory.builder import build_for_keys, build_from_index

    res = build_from_index(vault)
    assert res["papers_indexed"] == 25

    conn = get_connection(db_path, read_only=True)
    try:
        vec_cnt = conn.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0]
        assert vec_cnt >= 24
        part1_units = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='PART0001'").fetchone()[0]
        assert part1_units == 1
    finally:
        conn.close()

    # Explicitly scoped build STILL invalidates the specifically requested missing-OCR key
    build_for_keys(vault, ["PART0001"])
    conn = get_connection(db_path, read_only=True)
    try:
        assert conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='PART0001'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='PART0002'").fetchone()[0] == 1
    finally:
        conn.close()


def test_open_live_reader_recovers_hot_rollback_journal(tmp_path: Path) -> None:
    vault = tmp_path / "hot_journal_vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        ensure_schema(conn)
        conn.execute("INSERT INTO papers (zotero_key, title, domain) VALUES ('HOT00001', 'Hot Study', 'Ortho')")
        conn.commit()
    finally:
        conn.close()

    # Simulate a REAL synced hot rollback journal left behind by a crashed/killed writer
    # by forcing page-cache spill in DELETE mode before copying bytes out.
    journal_path = Path(str(db_path) + "-journal")
    rw = sqlite3.connect(str(db_path))
    rw.execute("PRAGMA journal_mode=DELETE")
    rw.execute("PRAGMA cache_size=1")
    rw.execute("BEGIN EXCLUSIVE")
    for idx in range(2, 62):
        rw.execute(
            "INSERT INTO papers (zotero_key, title, domain) VALUES (?, ?, 'Ortho')",
            (f"HOT{idx:05d}", f"Spill Uncommitted Study {idx} " + ("x" * 200)),
        )
    assert journal_path.is_file() and journal_path.stat().st_size > 0
    hot_db_bytes = db_path.read_bytes()
    hot_journal_bytes = journal_path.read_bytes()
    rw.rollback()
    rw.close()

    db_path.write_bytes(hot_db_bytes)
    journal_path.write_bytes(hot_journal_bytes)
    assert journal_path.is_file() and journal_path.stat().st_size > 0

    # Confirm bare ?mode=ro fails before recovery, proving this is a genuine hot journal
    raw_ro = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly database"):
            raw_ro.execute("SELECT COUNT(*) FROM papers").fetchone()
    finally:
        raw_ro.close()

    from paperforge.memory.db import open_live_reader

    with open_live_reader(vault, db_path) as rconn:
        cnt = rconn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        assert cnt == 1
    assert not journal_path.exists() or journal_path.stat().st_size == 0


# ---------------------------------------------------------------------------
# 8. Phase 3 Fast Bulk OCR Census & Large-DB Plan Probe
# ---------------------------------------------------------------------------


def test_fast_validate_result_json_and_assess_atoms_large_and_corrupt(tmp_path: Path) -> None:
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms, validate_result_json

    # 1. >64KB valid result.json passes fast structural check and skips sha256
    big_dir = tmp_path / "ocr" / "BIG00001"
    for sub in ("json", "canonical", "structure", "index"):
        (big_dir / sub).mkdir(parents=True)
    padding = "A" * 80000
    (big_dir / "json" / "result.json").write_text(
        json.dumps({"pages": [{"p": 1, "text": padding}]}),
        encoding="utf-8",
    )
    (big_dir / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps({"block_id": "b1", "text": padding[:20000]}) + "\n",
        encoding="utf-8",
    )
    (big_dir / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps({"block_id": "b1", "page": 1, "role": "text", "text": padding[:20000]}) + "\n",
        encoding="utf-8",
    )
    (big_dir / "index" / "structure-tree.json").write_text(
        json.dumps({"nodes": [{"id": "n1", "text": padding[:20000]}]}),
        encoding="utf-8",
    )
    (big_dir / "index" / "role-index.json").write_text(
        json.dumps({"text": [padding[:20000]]}),
        encoding="utf-8",
    )
    (big_dir / "index" / "result-hash.txt").write_text("abc123\n", encoding="utf-8")
    (big_dir / "fulltext.md").write_text("# Valid fulltext\n", encoding="utf-8")
    (big_dir / "meta.json").write_text(json.dumps({"ocr_status": "done"}), encoding="utf-8")

    ok_fast, reason_fast, _ = validate_result_json(big_dir, fast=True)
    assert ok_fast is True and reason_fast == "ok"
    atom_fast = assess_ocr_bundle_atoms(big_dir, fast=True)
    assert atom_fast["tier0_truth_intact"] is True
    assert atom_fast["tier0_sha256"] == ""
    assert atom_fast["salvage_action"] == "current"

    # 2. >64KB truncated result.json is caught as invalid even under fast=True
    trunc_dir = tmp_path / "ocr" / "TRUNC001"
    (trunc_dir / "json").mkdir(parents=True)
    (trunc_dir / "json" / "result.json").write_text('{"pages": [{"text": "' + padding, encoding="utf-8")
    ok_trunc, reason_trunc, _ = validate_result_json(trunc_dir, fast=True)
    assert ok_trunc is False and reason_trunc == "invalid"

    # 3. Small (<=64KB) invalid JSON falls back to full json.loads validation
    small_dir = tmp_path / "ocr" / "SMALLBAD"
    (small_dir / "json").mkdir(parents=True)
    (small_dir / "json" / "result.json").write_text('{"broken":', encoding="utf-8")
    ok_small, reason_small, _ = validate_result_json(small_dir, fast=True)
    assert ok_small is False and reason_small == "invalid"


def test_inspect_vault_upgrade_fast_ocr_and_large_db_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = tmp_path / "fast_plan_vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "FAST0001"
    (ocr_dir / "json").mkdir(parents=True)
    (ocr_dir / "json" / "result.json").write_text(
        json.dumps({"pages": [{"p": 1, "text": "B" * 80000}]}),
        encoding="utf-8",
    )

    db_path = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    conn = get_connection(db_path)
    try:
        ensure_schema(conn)
        conn.execute("INSERT INTO papers (zotero_key, title, domain) VALUES ('FAST0001', 'Fast Study', 'Ortho')")
        conn.commit()
    finally:
        conn.close()

    # Force the large-DB (>=64 MB) branch in inspect_vault_upgrade without writing 64 MB to disk
    import paperforge.services.vault_upgrade as vu_mod

    real_stat = Path.stat

    class _FakeStat:
        def __init__(self, base, size: int) -> None:
            self._base = base
            self.st_size = size

        def __getattr__(self, name: str):
            return getattr(self._base, name)

    def _patched_stat(self: Path, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if self.name == "paperforge.db":
            return _FakeStat(st, 100 * 1024 * 1024)
        return st

    monkeypatch.setattr(Path, "stat", _patched_stat)
    plan = vu_mod.inspect_vault_upgrade(vault, fast_summary=False)
    assert plan["summary"]["ocr_atoms"]["backfill_from_result_json"] == 1
    assert not any(t.get("id") == "db.integrity_failed" for t in plan["category_c_tamper"])


