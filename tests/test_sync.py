def test_frontmatter_note_writes_ocr_redo_false_by_default():
    from paperforge.worker.sync import frontmatter_note

    entry = {
        "title": "Test Paper",
        "zotero_key": "ABCD1234",
        "citation_key": "test2024",
        "year": "2024",
        "journal": "Test Journal",
        "first_author": "Smith",
        "domain": "test",
        "doi": "",
        "pmid": "",
        "collections": [],
        "collection_tags": [],
        "impact_factor": "",
        "abstract": "",
        "has_pdf": False,
        "do_ocr": False,
        "analyze": False,
        "ocr_status": "pending",
        "deep_reading_status": "pending",
        "pdf_path": "",
        "fulltext_path": "",
    }

    result = frontmatter_note(entry)
    assert "ocr_redo: false" in result


def test_frontmatter_note_preserves_ocr_redo_true():
    from paperforge.worker.sync import frontmatter_note

    entry = {
        "title": "Test Paper",
        "zotero_key": "ABCD1234",
        "citation_key": "test2024",
        "year": "2024",
        "journal": "Test Journal",
        "first_author": "Smith",
        "domain": "test",
        "doi": "",
        "pmid": "",
        "collections": [],
        "collection_tags": [],
        "impact_factor": "",
        "abstract": "",
        "has_pdf": False,
        "do_ocr": False,
        "analyze": False,
        "ocr_status": "pending",
        "deep_reading_status": "pending",
        "pdf_path": "",
        "fulltext_path": "",
    }

    result = frontmatter_note(entry, preserved_ocr_redo=True)
    assert "ocr_redo: true" in result
    assert "ocr_redo: false" not in result


def test_migrate_to_workspace_deletes_existing_workspace_fulltext(tmp_path, monkeypatch):
    from paperforge.worker import sync

    vault = tmp_path / "vault"
    literature = vault / "Resources" / "Literature"
    ocr = vault / "PaperForge" / "ocr"
    domain_dir = literature / "test_domain"
    domain_dir.mkdir(parents=True)

    key = "ABCD1234"
    title = "Test Paper"
    flat_note = domain_dir / f"{key} - {title}.md"
    flat_note.write_text(
        "---\n"
        f'title: "{title}"\n'
        f"zotero_key: {key}\n"
        "---\n\n"
        "# Test Paper\n",
        encoding="utf-8",
    )

    workspace_dir = domain_dir / f"{key} - {title}"
    workspace_dir.mkdir()
    (workspace_dir / f"{key}.md").write_text("# Existing note\n", encoding="utf-8")
    (workspace_dir / "fulltext.md").write_text("old workspace fulltext\n", encoding="utf-8")

    monkeypatch.setattr(sync.asset_index, "read_index", lambda _vault: {"items": []})

    paths = {
        "literature": literature,
        "ocr": ocr,
    }

    sync.migrate_to_workspace(vault, paths)

    assert not (workspace_dir / "fulltext.md").exists()


def test_sync_orphan_state_and_cleanup_use_configured_index_dir(tmp_path):
    from paperforge.commands.sync import _cleanup_legacy_snapshot_files, _write_orphan_state
    from paperforge.config import load_vault_config, paperforge_paths
    from paperforge.core.result import PFResult
    from tests.conftest import canonical_test_config

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="CustomSystem")
    index_dir = paperforge_paths(vault, load_vault_config(vault))["index"].parent
    result = PFResult(
        ok=True,
        command="sync",
        version="test",
        data={"prune": {"preview": [{"zotero_key": "ABCD1234"}]}},
    )

    _write_orphan_state(vault, result)
    orphan_path = index_dir / "sync-orphan-state.json"
    assert orphan_path.exists()
    assert not (vault / "System" / "PaperForge" / "indexes" / orphan_path.name).exists()

    (index_dir / "memory-runtime-state.json").write_text("legacy", encoding="utf-8")
    _cleanup_legacy_snapshot_files(vault)
    assert not (index_dir / "memory-runtime-state.json").exists()


def test_sync_fastpath_bypasses_when_index_export_hash_is_stale(tmp_path):
    import json
    from paperforge.services.sync_service import SyncService
    from paperforge.worker import asset_index
    from tests.conftest import canonical_test_config

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    svc = SyncService(vault)
    paths = svc.resolve_paths()
    paths["exports"].mkdir(parents=True, exist_ok=True)
    (paths["exports"] / "Sports.json").write_text(
        json.dumps({"items": [{"key": "K1", "title": "Paper 1"}]}),
        encoding="utf-8",
    )

    idx_dir = paths["index"].parent
    idx_dir.mkdir(parents=True, exist_ok=True)
    digest = svc._compute_sync_fastpath_digest(paths)
    (idx_dir / ".sync-fastpath.json").write_text(
        json.dumps({"digest": digest, "data": {"selection": {}}}),
        encoding="utf-8",
    )

    # Stale formal-library.json export_hash MUST bypass fastpath so sync refreshes the index
    paths["index"].write_text(
        json.dumps({"export_hash": "stale-e2e-hash", "items": []}),
        encoding="utf-8",
    )
    _, hit = svc._check_fastpath_or_sqlite_preflight()
    assert hit is None

    # Matching export_hash allows fastpath hit
    paths["index"].write_text(
        json.dumps({"export_hash": asset_index.compute_export_hash(paths), "items": []}),
        encoding="utf-8",
    )
    _, hit2 = svc._check_fastpath_or_sqlite_preflight()
    assert hit2 is not None and hit2.ok is True


def test_sync_fastpath_self_heals_stale_workspace_registry(tmp_path):
    import json
    import sqlite3
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.sync_service import SyncService
    from paperforge.worker import asset_index
    from tests.conftest import canonical_test_config

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    svc = SyncService(vault)
    paths = svc.resolve_paths()
    paths["exports"].mkdir(parents=True, exist_ok=True)
    (paths["exports"] / "Ortho.json").write_text(
        json.dumps({"items": [{"key": "GK000001", "title": "Ortho Paper"}]}),
        encoding="utf-8",
    )

    real_dir = paths["literature"] / "Ortho" / "GK000001 - Ortho Paper"
    real_dir.mkdir(parents=True, exist_ok=True)
    (real_dir / "GK000001.md").write_text(
        '---\nzotero_key: "GK000001"\ndomain: "Ortho"\ntitle: "Ortho Paper"\n---\n',
        encoding="utf-8",
    )

    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO workspace_registry (zotero_key, domain, workspace_relpath, main_note_relpath, dir_mtime_ns, identity_source, status, verified_at) "
        "VALUES (?, ?, ?, ?, 0, 'legacy', 'active', '2026-01-01')",
        (
            "GK000001",
            "Literature",
            "Resources/Literature/Literature/GK000001 - Ortho Paper",
            "Resources/Literature/Literature/GK000001 - Ortho Paper/GK000001.md",
        ),
    )
    conn.commit()
    conn.close()

    idx_dir = paths["index"].parent
    idx_dir.mkdir(parents=True, exist_ok=True)
    paths["index"].write_text(
        json.dumps({"export_hash": asset_index.compute_export_hash(paths), "items": []}),
        encoding="utf-8",
    )
    digest = svc._compute_sync_fastpath_digest(paths)
    (idx_dir / ".sync-fastpath.json").write_text(
        json.dumps({"digest": digest, "data": {"selection": {}}}),
        encoding="utf-8",
    )

    _, hit = svc._check_fastpath_or_sqlite_preflight()
    assert hit is not None and hit.ok is True

    check = sqlite3.connect(str(db_path))
    row = check.execute(
        "SELECT domain, main_note_relpath FROM workspace_registry WHERE zotero_key = 'GK000001'"
    ).fetchone()
    check.close()
    assert row is not None
    assert row[0] == "Ortho"
    assert row[1] == "Resources/Literature/Ortho/GK000001 - Ortho Paper/GK000001.md"


def test_sync_does_not_create_db_on_fresh_vault_and_dashboard_falls_back_when_papers_empty(tmp_path):
    import json
    from paperforge.commands.dashboard import _dashboard_from_db
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.sync_service import SyncService
    from tests.conftest import canonical_test_config

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    svc = SyncService(vault)
    paths = svc.resolve_paths()
    paths["exports"].mkdir(parents=True, exist_ok=True)
    (paths["exports"] / "Ortho.json").write_text(
        json.dumps({"items": [{"key": "GK000002", "title": "Fresh Paper"}]}),
        encoding="utf-8",
    )

    res = svc.run(json_output=True)
    assert res.ok is True
    db_path = get_memory_db_path(vault)
    # sync on a fresh vault must NOT prematurely create paperforge.db with 0 papers
    assert not db_path.exists()

    # If paperforge.db exists with empty papers table while formal-library.json has items,
    # _dashboard_from_db must return None so dashboard falls back to formal-library.json.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    ensure_schema(conn)
    conn.commit()
    conn.close()
    assert _dashboard_from_db(vault) is None
