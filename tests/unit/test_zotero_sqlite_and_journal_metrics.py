"""Tests for direct zotero.sqlite adapter and multi-source journal metrics."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from paperforge.adapters.zotero_sqlite import (
    build_bbt_export_documents_from_sqlite,
    list_zotero_collections,
    materialize_zotero_sqlite_exports,
)
from paperforge.journal_metrics import lookup_journal_metric, parse_extra_journal_metric
from paperforge.services.sync_service import SyncService
from paperforge.worker.sync import frontmatter_note
from tests.conftest import canonical_test_config


def _create_mock_zotero_dir(base: Path) -> Path:
    zdir = base / "ZoteroData"
    zdir.mkdir(parents=True, exist_ok=True)
    storage = zdir / "storage" / "ATT00001"
    storage.mkdir(parents=True, exist_ok=True)
    pdf_file = storage / "hydrogel.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\nhello world\n")

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
        INSERT INTO items VALUES (10, 1, 'ZOTKEY01'), (11, 2, 'ATT00001'), (12, 1, 'DELKEY99');
        INSERT INTO deletedItems VALUES (12);

        INSERT INTO fields VALUES (1, 'title'), (2, 'publicationTitle'), (3, 'date'), (4, 'DOI'), (5, 'extra'), (6, 'ISSN'), (7, 'citationKey');
        INSERT INTO itemDataValues VALUES
            (1, 'Cartilage Hydrogel Scaffolds'),
            (2, 'Biomaterials'),
            (3, '2025-04-01'),
            (4, '10.1016/j.biomaterials.2025.001'),
            (5, 'PMID: 12345678\n影响因子: 14.0\n中科院分区: 1区Top'),
            (6, '0142-9612'),
            (7, 'linCartilage2025');
        INSERT INTO itemData VALUES (10,1,1), (10,2,2), (10,3,3), (10,4,4), (10,5,5), (10,6,6), (10,7,7);

        INSERT INTO creatorTypes VALUES (1, 'author');
        INSERT INTO creators VALUES (1, 'Wei', 'Lin', 0);
        INSERT INTO itemCreators VALUES (10, 1, 1, 0);

        INSERT INTO collections VALUES (100, 'BoneRegen', NULL, 'COLTOP01'), (101, 'Hydrogels', 100, 'COLSUB01');
        INSERT INTO collectionItems VALUES (101, 10);

        INSERT INTO itemAttachments VALUES (11, 10, 0, 'application/pdf', 'storage:hydrogel.pdf');
        """
    )
    conn.commit()
    conn.close()
    return zdir


def test_zotero_sqlite_collections_and_dual_domain_modes(tmp_path: Path) -> None:
    zdir = _create_mock_zotero_dir(tmp_path)
    listed = list_zotero_collections(zdir)
    assert listed["found"] is True
    assert listed["total_papers"] == 1
    assert [c["path"] for c in listed["collections"]] == ["BoneRegen", "BoneRegen/Hydrogels"]

    # per_collection mode maps top-level selection -> Domain file
    docs_per = build_bbt_export_documents_from_sqlite(
        zdir, selected_collections=["COLTOP01"], domain_mode="per_collection"
    )
    assert "BoneRegen" in docs_per
    items = docs_per["BoneRegen"]["items"]
    assert len(items) == 1
    it = items[0]
    assert it["key"] == "ZOTKEY01"
    assert it["citationKey"] == "linCartilage2025"
    assert it["ISSN"] == "0142-9612"
    assert it["PMID"] == "12345678"
    assert it["attachments"][0]["path"] == "storage:ATT00001/hydrogel.pdf"
    assert it["attachments"][0]["size"] > 0

    # unified mode places all items under one unified domain while preserving collection paths
    docs_uni = build_bbt_export_documents_from_sqlite(
        zdir, selected_collections=["COLTOP01"], domain_mode="unified", unified_domain="AllPapers"
    )
    assert list(docs_uni.keys()) == ["AllPapers"]
    assert len(docs_uni["AllPapers"]["items"]) == 1


def test_sync_service_materializes_sqlite_without_manual_bbt_json(tmp_path: Path) -> None:
    zdir = _create_mock_zotero_dir(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(
        vault,
        system_dir=".paperforge",
        resources_dir="Resources",
        literature_dir="Literature",
        control_dir="LiteratureControl",
        base_dir="Bases",
        skill_dir=".agents/skills",
        zotero_data_dir=str(zdir),
        zotero_source_mode="sqlite",
        domain_mode="per_collection",
        zotero_selected_collections='["COLTOP01"]',
    )

    svc = SyncService(vault)
    paths = svc.resolve_paths()
    svc._materialize_sqlite_exports_if_enabled(paths)

    mat_file = paths["exports"] / "BoneRegen.json"
    assert mat_file.is_file()
    doc = json.loads(mat_file.read_text(encoding="utf-8"))
    assert doc["__managed_by"] == "zotero_sqlite"
    assert doc["items"][0]["key"] == "ZOTKEY01"

    # Second run with narrower collection updates and keeps manual exports untouched
    manual_file = paths["exports"] / "ManualLegacy.json"
    manual_file.write_text(json.dumps({"collections": {}, "items": []}), encoding="utf-8")
    materialize_zotero_sqlite_exports(vault, paths["exports"], zdir, selected_collections=[], domain_mode="unified")
    assert (paths["exports"] / "Literature.json").is_file()
    assert not mat_file.exists()
    assert manual_file.is_file()


def test_journal_metrics_extra_and_partition_extraction(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    m = lookup_journal_metric(
        "Biomaterials",
        "影响因子: 14.0\n中科院分区: 1区Top\nJCR: Q1",
        vault,
        allow_network=False,
    )
    assert m["impact_factor"] == "14.0"
    assert m["impact_factor_source"] == "extra"
    assert "Q1" in m["journal_partition"]
    assert "1区Top" in m["journal_partition"]

    parsed = parse_extra_journal_metric("IF: 8.4\nJCR: Q2")
    assert parsed["impact_factor"] == "8.4"
    assert parsed["journal_partition"] == "Q2"


def test_openalex_offline_seed_lookup_and_aliases_preservation(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    # Force network calls to raise so we prove bundled CC0 seed resolves offline without HTTP
    monkeypatch.setattr(
        "requests.get",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("HTTP must not be called when seed hits")),
    )
    seeded = lookup_journal_metric("Nature", "", vault, allow_network=True)
    assert seeded["impact_factor_source"] == "openalex_2yr"
    assert float(seeded["impact_factor"]) > 0.0

    # Sync frontmatter update must preserve user-added custom aliases alongside canonical title/key
    existing = "---\nzotero_key: ZOTKEY01\naliases:\n  - My Custom Nickname\n  - Cartilage Paper\n---\n\nBody text\n"
    rendered = frontmatter_note(
        {
            "key": "ZOTKEY01",
            "title": "Hydrogel Repair of Cartilage",
            "citation_key": "linCartilage2025",
            "domain": "BoneRegen",
            "attachments": [],
        },
        existing_text=existing,
    )
    assert "My Custom Nickname" in rendered
    assert "Cartilage Paper" in rendered
    assert "Hydrogel Repair of Cartilage" in rendered
    assert "linCartilage2025" in rendered


def test_sync_fails_closed_on_corrupt_locked_or_missing_zotero_sqlite(tmp_path: Path) -> None:
    """PF-MIG-001: corrupt, OS-locked, or missing zotero.sqlite must fail closed with zero pruning."""
    import ctypes
    import os
    from paperforge.core.errors import ErrorCode

    zdir = _create_mock_zotero_dir(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(
        vault,
        system_dir=".paperforge",
        zotero_data_dir=str(zdir),
        zotero_source_mode="sqlite",
        domain_mode="per_collection",
    )

    # First run healthy sync so workspace + fastpath + exports exist
    svc = SyncService(vault)
    ok_res = svc.run(json_output=True)
    assert ok_res.ok is True
    ws_note = vault / "Resources" / "Literature" / "BoneRegen" / "ZOTKEY01 - Cartilage Hydrogel Scaffolds" / "ZOTKEY01.md"
    assert ws_note.is_file()

    # (a) Corrupt zotero.sqlite after prior valid exports -> must fail closed (never silently reuse stale exports)
    db_path = zdir / "zotero.sqlite"
    orig_bytes = db_path.read_bytes()
    db_path.write_bytes(b"NOT_A_VALID_SQLITE_DATABASE_HEADER" * 20)
    corrupt_res = svc.run(prune=True, prune_force=True, json_output=True)
    assert corrupt_res.ok is False
    assert corrupt_res.error is not None
    assert corrupt_res.error.code == ErrorCode.SYNC_FAILED
    assert ws_note.is_file()

    # (b) OS-exclusively locked zotero.sqlite (Windows CreateFileW dwShareMode=0) -> fail closed
    db_path.write_bytes(orig_bytes)
    if os.name == "nt":
        k32 = ctypes.windll.kernel32
        handle = k32.CreateFileW(str(db_path), 0xC0000000, 0, None, 3, 0x80, None)
        assert handle != -1
        try:
            locked_res = svc.run(json_output=True)
            assert locked_res.ok is False
            assert locked_res.error is not None
            assert locked_res.error.code == ErrorCode.SYNC_FAILED
            assert ws_note.is_file()
        finally:
            k32.CloseHandle(handle)

    # (c) Missing zotero.sqlite when zotero_data_dir is configured -> fail closed
    db_path.unlink()
    missing_res = svc.run(prune=True, prune_force=True, json_output=True)
    assert missing_res.ok is False
    assert missing_res.error is not None
    assert missing_res.error.code == ErrorCode.SYNC_FAILED
    assert ws_note.is_file()


def test_deleted_collections_excluded_and_missing_selection_fails_closed(tmp_path: Path) -> None:
    """PF-MIG-008: deletedCollections are excluded and unmatched selected_collections fail closed."""
    import pytest

    zdir = _create_mock_zotero_dir(tmp_path)
    conn = sqlite3.connect(str(zdir / "zotero.sqlite"))
    conn.execute("INSERT INTO collections VALUES (102, 'DeletedOld', NULL, 'COL_DEL1')")
    conn.execute("INSERT INTO deletedCollections VALUES (102)")
    conn.execute("INSERT INTO collectionItems VALUES (102, 10)")
    conn.commit()
    conn.close()

    docs = build_bbt_export_documents_from_sqlite(zdir, domain_mode="unified")
    assert "COL_DEL1" not in docs["Literature"]["collections"]

    with pytest.raises(ValueError, match="matched no active Zotero collections"):
        build_bbt_export_documents_from_sqlite(
            zdir, selected_collections=["NON_EXISTENT_COL"], domain_mode="per_collection"
        )


def test_zotero_detect_without_deleted_collections_and_per_collection_no_collapse(tmp_path: Path) -> None:
    """PF-UX-010: missing deletedCollections table degrades gracefully; default per_collection splits top-level collections."""
    zdir = tmp_path / "ZoteroMinimal"
    zdir.mkdir()
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
        CREATE TABLE collectionItems (collectionID INTEGER, itemID INTEGER);
        CREATE TABLE itemAttachments (itemID INTEGER PRIMARY KEY, parentItemID INTEGER, linkMode INTEGER, contentType TEXT, path TEXT);

        INSERT INTO itemTypes VALUES (1, 'journalArticle');
        INSERT INTO items VALUES (1, 1, 'P1KEY001'), (2, 1, 'P2KEY002');
        INSERT INTO fields VALUES (1, 'title');
        INSERT INTO itemDataValues VALUES (1, 'Ortho Paper'), (2, 'AI Paper');
        INSERT INTO itemData VALUES (1, 1, 1), (2, 1, 1), (2, 1, 2);
        INSERT INTO collections VALUES (10, 'Orthopedics', NULL, 'COL_ORTH'), (20, 'AI_Radiology', NULL, 'COL_AIRAD');
        INSERT INTO collectionItems VALUES (10, 1), (20, 2);
        """
    )
    conn.commit()
    conn.close()

    listed = list_zotero_collections(zdir)
    assert listed["found"] is True
    assert listed["total_papers"] == 2
    assert {c["name"] for c in listed["collections"]} == {"Orthopedics", "AI_Radiology"}

    docs = build_bbt_export_documents_from_sqlite(zdir, selected_collections=[], domain_mode="per_collection")
    assert set(docs.keys()) == {"Orthopedics", "AI_Radiology"}
    assert "Literature" not in docs


def test_cross_collection_item_resolves_no_raw_collection_keys(tmp_path: Path) -> None:
    """PF-MIG-017: cross-domain items must never leak raw 8-char collection keys in per_collection slices."""
    from paperforge.adapters.bbt import load_export_rows

    zdir = _create_mock_zotero_dir(tmp_path)
    conn = sqlite3.connect(str(zdir / "zotero.sqlite"))
    conn.execute("INSERT INTO collections VALUES (200, 'Sports', NULL, 'COL_SPRT')")
    conn.execute("INSERT INTO collectionItems VALUES (200, 10)")
    conn.commit()
    conn.close()

    docs = build_bbt_export_documents_from_sqlite(
        zdir, selected_collections=["COLTOP01", "COL_SPRT"], domain_mode="per_collection"
    )
    tmp_json = tmp_path / "BoneRegen.json"
    tmp_json.write_text(json.dumps(docs["BoneRegen"]), encoding="utf-8")
    rows = load_export_rows(tmp_json)
    assert rows[0]["collections"] == ["BoneRegen/Hydrogels"]
    assert "COL_SPRT" not in rows[0]["collections"]


def test_sqlite_nested_storage_backslash_renamed_and_attachments_base_dir(tmp_path: Path, monkeypatch) -> None:
    """Nested storage paths, stale filenames, backslashes, and multi-profile baseAttachmentPath all resolve cleanly."""
    from paperforge.adapters import zotero_sqlite

    zdir = tmp_path / "ZoteroMain"
    att_dir = zdir / "storage" / "ATTNEST1"
    (att_dir / "sub").mkdir(parents=True)
    nested_pdf = att_dir / "sub" / "nested.pdf"
    nested_pdf.write_bytes(b"%PDF-1.4\nnested\n")

    att_renamed = zdir / "storage" / "ATTREN01"
    att_renamed.mkdir(parents=True)
    actual_pdf = att_renamed / "actual_name.pdf"
    actual_pdf.write_bytes(b"%PDF-1.4\nrenamed\n")

    prof1 = tmp_path / "prof1"
    prof1.mkdir()
    base1 = tmp_path / "LinkedOther"
    base1.mkdir()
    (prof1 / "prefs.js").write_text(
        f'user_pref("extensions.zotero.dataDir", "{(tmp_path / "OtherZotero").as_posix()}");\n'
        f'user_pref("extensions.zotero.baseAttachmentPath", "{base1.as_posix()}");\n',
        encoding="utf-8",
    )

    prof2 = tmp_path / "prof2"
    prof2.mkdir()
    base2 = tmp_path / "LinkedMain"
    (base2 / "Ortho").mkdir(parents=True)
    linked_pdf = base2 / "Ortho" / "linked.pdf"
    linked_pdf.write_bytes(b"%PDF-1.4\nlinked\n")
    (prof2 / "prefs.js").write_text(
        f'user_pref("extensions.zotero.dataDir", "{zdir.as_posix()}");\n'
        f'user_pref("extensions.zotero.baseAttachmentPath", "{base2.as_posix()}");\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(zotero_sqlite, "_zotero_profile_dirs", lambda: [prof1, prof2])
    resolved_base = zotero_sqlite.read_zotero_base_attachment_path(zdir)
    assert resolved_base == base2

    norm_nested, _, sz_nested = zotero_sqlite._resolve_sqlite_attachment_path(
        "storage:sub\\nested.pdf", "ATTNEST1", 0, zdir, resolved_base
    )
    assert norm_nested == "storage:ATTNEST1/sub/nested.pdf"
    assert sz_nested > 0

    norm_renamed, _, sz_renamed = zotero_sqlite._resolve_sqlite_attachment_path(
        "storage:stale_name.pdf", "ATTREN01", 0, zdir, resolved_base
    )
    assert norm_renamed == "storage:ATTREN01/actual_name.pdf"
    assert sz_renamed > 0

    norm_att, _, sz_att = zotero_sqlite._resolve_sqlite_attachment_path(
        "attachments:Ortho\\linked.pdf", "ATTLNK01", 2, zdir, resolved_base
    )
    assert Path(norm_att) == linked_pdf
    assert sz_att > 0


def test_journal_metrics_offline_seed_and_cache_fast_paths(tmp_path: Path, monkeypatch) -> None:
    """Bundled CC0 seed works when allow_network=False, local plugin DB is mtime-cached, and misses memoize."""
    from paperforge import journal_metrics

    vault = tmp_path / "vault_jm"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    zoterostyle = vault / ".paperforge" / "Zotero" / "zoterostyle.json"
    zoterostyle.parent.mkdir(parents=True, exist_ok=True)
    zoterostyle.write_text(json.dumps({"Custom Journal": {"rank": {"sciif": "9.5"}}}), encoding="utf-8")

    journal_metrics._LOCAL_DB_CACHE.clear()
    journal_metrics._INMEM_MISS_OFFLINE.clear()
    journal_metrics._INMEM_MISS_NETWORK.clear()

    read_calls = 0
    orig_read_json = journal_metrics.read_json

    def _counting_read_json(p: Path):
        nonlocal read_calls
        if p == zoterostyle:
            read_calls += 1
        return orig_read_json(p)

    monkeypatch.setattr(journal_metrics, "read_json", _counting_read_json)
    for _ in range(10):
        hit = lookup_journal_metric("Custom Journal", "", vault, allow_network=False)
        assert hit["impact_factor"] == "9.5"
    assert read_calls == 1

    # Offline lookup should hit bundled CC0 seed with 0 HTTP calls
    seeded_offline = lookup_journal_metric("Nature", "", vault, allow_network=False)
    assert seeded_offline["impact_factor_source"] == "openalex_2yr"
    assert float(seeded_offline["impact_factor"]) > 0.0

    # Negative misses memoize per vault without repeatedly hitting SQLite
    sqlite_calls = 0
    orig_read_sqlite = journal_metrics._read_sqlite_cache

    def _counting_sqlite(*args, **kwargs):
        nonlocal sqlite_calls
        sqlite_calls += 1
        return orig_read_sqlite(*args, **kwargs)

    monkeypatch.setattr(journal_metrics, "_read_sqlite_cache", _counting_sqlite)
    miss1 = lookup_journal_metric("NonExistentJournal_XYZ_999", "", vault, allow_network=False)
    miss2 = lookup_journal_metric("NonExistentJournal_XYZ_999", "", vault, allow_network=False)
    assert miss1["impact_factor"] == ""
    assert miss2["impact_factor"] == ""
    assert sqlite_calls == 1
