#!/usr/bin/env python3
"""Build disposable fixtures for the fast real-Obsidian Settings & Migration Matrix (H2).

Creates three tiny, deterministic vaults/directories under ``paperforge/plugin/test/vaults/``:
1. ``settings-fresh``   — brand-new unconfigured Obsidian vault (no ``paperforge.json``, no ``data.json``)
2. ``settings-zotero``  — tiny real ``zotero.sqlite`` library (2 articles + 2 collections + 1 PDF)
3. ``settings-legacy``  — veteran v1.x layout vault (``System/`` without ``vault-manifest.json`` + user note)
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paperforge.config import paperforge_paths  # noqa: E402

PLUGIN_DIR = Path(__file__).resolve().parents[2]
VAULTS_DIR = PLUGIN_DIR / "test" / "vaults"

OCR_FIXTURE = REPO_ROOT / "tests" / "sandbox" / "ocr-complete" / "TSTONE001"
PDF_FIXTURE = (
    REPO_ROOT
    / "tests"
    / "sandbox"
    / "TestZoteroData"
    / "storage"
    / "TSTONE001"
    / "TSTONE001.pdf"
)


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _build_fresh_vault(vault: Path) -> None:
    _reset_dir(vault)
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    (vault / "Welcome.md").write_text(
        "# Fresh Vault\n\nBrand new unconfigured Obsidian vault.\n",
        encoding="utf-8",
    )


def _build_zotero_fixture(zdir: Path) -> None:
    _reset_dir(zdir)
    for att_dir, pdf_name in (
        ("ATT00001", "hydrogel.pdf"),
        ("ATT00003", "rotator_cuff.pdf"),
        ("ATT00004", "运动医学_肩袖修复.pdf"),
    ):
        storage = zdir / "storage" / att_dir
        storage.mkdir(parents=True, exist_ok=True)
        (storage / pdf_name).write_bytes(b"%PDF-1.4\n% PaperForge E2E tiny PDF\n")

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
        CREATE TABLE collections (
            collectionID INTEGER PRIMARY KEY,
            collectionName TEXT,
            parentCollectionID INTEGER,
            key TEXT
        );
        CREATE TABLE deletedCollections (collectionID INTEGER PRIMARY KEY);
        CREATE TABLE collectionItems (collectionID INTEGER, itemID INTEGER);
        CREATE TABLE itemAttachments (
            itemID INTEGER PRIMARY KEY,
            parentItemID INTEGER,
            linkMode INTEGER,
            contentType TEXT,
            path TEXT
        );

        INSERT INTO itemTypes VALUES (1, 'journalArticle'), (2, 'attachment');
        INSERT INTO items VALUES
            (10, 1, 'ZOTKEY01'),
            (11, 2, 'ATT00001'),
            (12, 1, 'DELKEY99'),
            (13, 1, 'ZOTKEY02'),
            (14, 1, 'ZOTKEY03'),
            (15, 2, 'ATT00003'),
            (16, 1, 'ZOTKEY04'),
            (17, 2, 'ATT00004');
        INSERT INTO deletedItems VALUES (12);

        INSERT INTO fields VALUES
            (1, 'title'), (2, 'publicationTitle'), (3, 'date'),
            (4, 'DOI'), (5, 'extra'), (6, 'ISSN'), (7, 'citationKey');
        INSERT INTO itemDataValues VALUES
            (1, 'Cartilage Hydrogel Scaffolds'),
            (2, 'Biomaterials'),
            (3, '2025-04-01'),
            (4, '10.1016/j.biomaterials.2025.001'),
            (5, 'PMID: 12345678'),
            (6, '0142-9612'),
            (7, 'linCartilage2025'),
            (8, 'Tendon-Bone Healing Mechanics'),
            (9, 'Journal of Orthopaedic Research'),
            (10, '2026-01-15'),
            (11, '10.1002/jor.2026.002'),
            (12, 'linTendon2026'),
            (13, 'Rotator Cuff Suture Bridge Biomechanics'),
            (14, 'AJSM'),
            (15, '2025-07-10'),
            (16, '10.1177/0363546525000003'),
            (17, 'zhangRotator2025'),
            (18, '肩袖修复术后 MRI 评估'),
            (19, '中华骨科杂志'),
            (20, '2025-09-01'),
            (21, '10.3760/cma.j.cn121113.2025.004'),
            (22, 'wangRotator2025');
        INSERT INTO itemData VALUES
            (10,1,1), (10,2,2), (10,3,3), (10,4,4), (10,5,5), (10,6,6), (10,7,7),
            (13,1,8), (13,2,9), (13,3,10), (13,4,11), (13,7,12),
            (14,1,13), (14,2,14), (14,3,15), (14,4,16), (14,7,17),
            (16,1,18), (16,2,19), (16,3,20), (16,4,21), (16,7,22);

        INSERT INTO creatorTypes VALUES (1, 'author');
        INSERT INTO creators VALUES
            (1, 'Wei', 'Lin', 0),
            (2, 'Bo', 'Chen', 0),
            (3, 'Mei', 'Zhang', 0),
            (4, 'Jun', 'Wang', 0);
        INSERT INTO itemCreators VALUES
            (10, 1, 1, 0),
            (13, 2, 1, 0),
            (14, 3, 1, 0),
            (16, 4, 1, 0);

        INSERT INTO collections VALUES
            (100, 'BoneRegen', NULL, 'COLTOP01'),
            (101, 'Hydrogels', 100, 'COLSUB01');
        INSERT INTO collectionItems VALUES (101, 10), (100, 13), (100, 14), (100, 16);

        INSERT INTO itemAttachments VALUES
            (11, 10, 0, 'application/pdf', 'storage:hydrogel.pdf'),
            (15, 14, 0, 'application/pdf', 'storage:rotator_cuff.pdf'),
            (17, 16, 0, 'application/pdf', 'storage:运动医学_肩袖修复.pdf');
        """
    )
    conn.commit()
    conn.close()


def _build_legacy_vault(vault: Path) -> None:
    _reset_dir(vault)
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    # Veteran v1.x paperforge.json (System dir without schema_version: 2 or .paperforge/vault-manifest.json)
    (vault / "paperforge.json").write_text(
        json.dumps(
            {
                "vault_config": {
                    "system_dir": "System",
                    "resources_dir": "Resources",
                    "literature_dir": "Literature",
                    "base_dir": "Bases",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    paths = paperforge_paths(
        vault,
        {
            "system_dir": "System",
            "resources_dir": "Resources",
            "literature_dir": "Literature",
            "base_dir": "Bases",
        },
    )
    idx_dir = paths["paperforge"] / "indexes"
    idx_dir.mkdir(parents=True, exist_ok=True)
    (idx_dir / "formal-library.json").write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "zotero_key": "TSTONE001",
                        "title": "Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair",
                        "first_author": "Stone",
                        "year": "2024",
                        "domain": "BoneRegen",
                        "pdf_relpath": "System/Zotero/storage/TSTONE001/TSTONE001.pdf",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if OCR_FIXTURE.exists():
        shutil.copytree(
            OCR_FIXTURE,
            paths["ocr"] / "TSTONE001",
            dirs_exist_ok=True,
        )
    if PDF_FIXTURE.exists():
        pdf_dst = paths["zotero_dir"] / "storage" / "TSTONE001" / "TSTONE001.pdf"
        pdf_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PDF_FIXTURE, pdf_dst)

    # Personal non-PaperForge note — lossless migration must leave it byte-identical.
    personal_dir = vault / "Personal"
    personal_dir.mkdir(parents=True, exist_ok=True)
    (personal_dir / "MyNotes.md").write_text(
        "# Personal Lab Notebook\n\nUntouched user content.\n",
        encoding="utf-8",
    )


def _build_collision_vault(vault: Path) -> None:
    """Fresh vault already containing user-owned Resources/ and Bases/ folders."""
    _reset_dir(vault)
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    resources = vault / "Resources"
    resources.mkdir(parents=True, exist_ok=True)
    (resources / "PersonalReading.md").write_text(
        "# My Existing Notes\n\nMust stay untouched.\n",
        encoding="utf-8",
    )
    bases = vault / "Bases"
    bases.mkdir(parents=True, exist_ok=True)
    (bases / "MyTasks.base").write_text(
        "views:\n  - type: table\n    name: Personal Tasks\n",
        encoding="utf-8",
    )


def build() -> None:
    _build_fresh_vault(VAULTS_DIR / "settings-fresh")
    _build_zotero_fixture(VAULTS_DIR / "settings-zotero")
    _build_legacy_vault(VAULTS_DIR / "settings-legacy")
    _build_collision_vault(VAULTS_DIR / "settings-collision")
    print(f"Settings E2E fixtures ready under {VAULTS_DIR}")


if __name__ == "__main__":
    build()
