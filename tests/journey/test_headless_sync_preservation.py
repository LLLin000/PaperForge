"""J2 — headless sync + vault preservation (#146 J-matrix).

Runs `paperforge sync` headless over a seeded vault and asserts the
Obsidian-managed directory (`.obsidian`) is byte-for-byte untouched.
This is the 3-OS machine gate: the sync path must never rewrite
Obsidian-owned files, even when a plugin bundle is present.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a CLI command as subprocess and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "paperforge"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=90,
    )


def _plant_obsidian_dir(vault: Path) -> dict[Path, bytes]:
    """Plant a .obsidian directory with sentinel content; return path -> bytes."""
    obs = vault / ".obsidian"
    sentinels = {
        obs / "app.json": json.dumps(
            {"vault": "sentinel-app", "attachmentFolderPath": "Attachments"},
            indent=2,
        ).encode("utf-8"),
        obs / "plugins" / "paperforge" / "main.js": (
            b"// sentinel plugin bundle\nconsole.log('paperforge');\n"
        ),
    }
    for path, payload in sentinels.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return sentinels


def test_headless_sync_preserves_obsidian_dir(test_vault: Path) -> None:
    """#146 J2: headless sync must not touch the Obsidian-managed directory."""
    sentinels = _plant_obsidian_dir(test_vault)

    result = _run(["sync", "--json"], test_vault)
    assert result.returncode == 0, f"sync failed: {result.stderr[:500]}"

    # Sync actually ran and produced the index...
    idx = (
        test_vault
        / ".paperforge"
        / "indexes"
        / "formal-library.json"
    )
    assert idx.exists(), "index file should exist after sync"

    # ...and the Obsidian-owned directory is byte-for-byte untouched.
    for path, payload in sentinels.items():
        assert path.read_bytes() == payload, f"{path} was modified by sync"


def test_sync_ignores_user_sovereign_notes_without_zotero_key(tmp_path: Path) -> None:
    """PF-MIG-004: user-sovereign notes lacking zotero_key are never wrapped into workspaces or pruned."""
    from paperforge.services.sync_service import SyncService
    from tests.conftest import canonical_test_config

    canonical_test_config(tmp_path, system_dir=".paperforge")
    pf = tmp_path / ".paperforge"
    (pf / "exports").mkdir(parents=True)
    (pf / "exports" / "Ortho.json").write_text(
        json.dumps(
            {
                "collections": {},
                "items": [
                    {
                        "key": "ZOT00001",
                        "itemType": "journalArticle",
                        "title": "Real Paper",
                        "creators": [],
                        "attachments": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    sovereign = tmp_path / "Resources" / "Literature" / "Ortho" / "My Sovereign Research Ideas.md"
    sovereign.parent.mkdir(parents=True)
    sovereign.write_text("---\ntags: [ideas]\n---\n\n# Personal thoughts\n", encoding="utf-8")

    res = SyncService(tmp_path).run(prune=True, prune_force=True, json_output=True)
    assert res.ok is True
    assert sovereign.is_file()
    assert not (
        tmp_path / "Resources" / "Literature" / "Ortho" / "My Sovereign Research Ideas - My Sovereign Research Ideas"
    ).exists()
    assert not (res.data.get("prune") or {}).get("preview")


def test_sync_fastpath_invalidates_on_workspace_note_edit_and_pdf_download(tmp_path: Path) -> None:
    """PF-MIG-015: editing a workspace main note or adding a PDF in Zotero storage/ invalidates sync fastpath."""
    import sqlite3
    import time
    from paperforge.services.sync_service import SyncService
    from tests.conftest import canonical_test_config

    zdir = tmp_path / "ZoteroData"
    zdir.mkdir()
    (zdir / "storage" / "ATT00002").mkdir(parents=True)
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
        INSERT INTO items VALUES (1, 1, 'ZOT00001'), (2, 2, 'ATT00002');
        INSERT INTO fields VALUES (1, 'title');
        INSERT INTO itemDataValues VALUES (1, 'Cloud PDF Paper');
        INSERT INTO itemData VALUES (1, 1, 1);
        INSERT INTO collections VALUES (10, 'Ortho', NULL, 'COL00001');
        INSERT INTO collectionItems VALUES (10, 1);
        INSERT INTO itemAttachments VALUES (2, 1, 0, 'application/pdf', 'storage:cloud_only.pdf');
        """
    )
    conn.commit()
    conn.close()

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(
        vault,
        system_dir=".paperforge",
        zotero_data_dir=str(zdir),
        zotero_source_mode="sqlite",
        domain_mode="per_collection",
        zotero_selected_collections='["*"]',
    )

    svc = SyncService(vault)
    r1 = svc.run(json_output=True)
    assert r1.ok is True
    paths = svc.resolve_paths()
    d1 = svc._compute_sync_fastpath_digest(paths)

    # (a) Edit workspace main note (e.g. toggle do_ocr: true)
    ws_note = next((vault / "Resources" / "Literature" / "Ortho").rglob("ZOT00001.md"))
    time.sleep(0.02)
    ws_note.write_text(ws_note.read_text(encoding="utf-8").replace("do_ocr: false", "do_ocr: true"), encoding="utf-8")
    d2 = svc._compute_sync_fastpath_digest(paths)
    assert d2 != d1

    # (b) Drop cloud-only PDF into Zotero storage/ATT00002/ without touching zotero.sqlite
    time.sleep(0.02)
    (zdir / "storage" / "ATT00002" / "cloud_only.pdf").write_bytes(b"%PDF-1.4\ndownloaded\n")
    d3 = svc._compute_sync_fastpath_digest(paths)
    assert d3 != d2
