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
