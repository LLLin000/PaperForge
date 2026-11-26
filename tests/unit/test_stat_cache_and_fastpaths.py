"""Tests for Racy-Git stat fingerprint cache, read_index cache, SQLite fast paths, and log compaction."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

import pytest

from paperforge.config import bootstrap_config, paperforge_paths, set_config
from paperforge.core import stat_cache
from paperforge.memory.db import get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.services.annotations_service import (
    add_annotation,
    delete_annotation,
    read_active_annotations_for_workspace,
    update_annotation,
)
from paperforge.services.memory_card_service import get_base_table_snapshot
from paperforge.worker.asset_index import build_envelope, read_index
from paperforge.worker.ocr_hash import OCR_RESULT_HASH_ARTIFACTS, compute_ocr_result_hash

pytestmark = pytest.mark.unit


def _make_old_file(path: Path, data: bytes, age_seconds: float = 10.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    old = time.time() - age_seconds
    os.utime(path, (old, old))


def test_cached_sha256_skips_file_read_when_non_racy_and_rehashes_in_racy_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPERFORGE_CACHE_DIR", str(tmp_path / "pf-cache"))
    stat_cache.clear_memory_cache()

    pdf = tmp_path / "paper.pdf"
    payload = b"%PDF-1.4\n" + (b"A" * 4096)
    _make_old_file(pdf, payload, age_seconds=20.0)
    expected = hashlib.sha256(payload).hexdigest()

    assert stat_cache.cached_sha256_hex(pdf) == expected

    # Clear process-memory cache to verify persistent SQLite cache hit with zero file read
    stat_cache.clear_memory_cache()
    monkeypatch.setattr(
        stat_cache,
        "_stream_sha256_hex",
        lambda _p: (_ for _ in ()).throw(AssertionError("should not re-read unchanged old file")),
    )
    assert stat_cache.cached_sha256_hex(pdf) == expected

    # Same-size overwrite with current mtime (within racy 2s window) must bypass cache!
    monkeypatch.undo()
    monkeypatch.setenv("PAPERFORGE_CACHE_DIR", str(tmp_path / "pf-cache"))
    new_payload = b"%PDF-1.4\n" + (b"B" * 4096)
    pdf.write_bytes(new_payload)
    assert stat_cache.cached_sha256_hex(pdf) == hashlib.sha256(new_payload).hexdigest()


def test_cached_concat_ocr_hash_matches_raw_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPERFORGE_CACHE_DIR", str(tmp_path / "pf-cache"))
    stat_cache.clear_memory_cache()

    paper_root = tmp_path / "ocr" / "K1"
    raw_concat = b""
    for i, rel in enumerate(OCR_RESULT_HASH_ARTIFACTS):
        chunk = f"artifact-{i}-payload\n".encode()
        raw_concat += chunk
        _make_old_file(paper_root / rel, chunk, age_seconds=30.0)

    expected = hashlib.sha256(raw_concat).hexdigest()
    assert compute_ocr_result_hash(paper_root) == expected
    assert compute_ocr_result_hash(paper_root) == expected


def test_read_index_mtime_cache_and_sqlite_first_base_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    bootstrap_config(vault)
    set_config(vault, "system_dir", ".paperforge")
    paths = paperforge_paths(vault)
    paths["paperforge"].mkdir(parents=True, exist_ok=True)
    (paths["paperforge"] / "indexes").mkdir(parents=True, exist_ok=True)
    ws_k1 = paths["literature"] / "General" / "K1 - Sample"
    ws_k2 = paths["literature"] / "General" / "K2 - Unindexed"
    ws_k1.mkdir(parents=True, exist_ok=True)
    ws_k2.mkdir(parents=True, exist_ok=True)

    env = build_envelope(
        [
            {
                "zotero_key": "K1",
                "title": "In DB Paper",
                "paper_root": ws_k1.relative_to(vault).as_posix(),
            },
            {
                "zotero_key": "K2",
                "title": "New Unindexed Paper",
                "paper_root": ws_k2.relative_to(vault).as_posix(),
            },
        ]
    )
    _make_old_file(paths["index"], json.dumps(env).encode("utf-8"), age_seconds=20.0)
    first = read_index(vault)
    assert isinstance(first, dict) and len(first["items"]) == 2
    assert read_index(vault) == first

    # Before DB exists: sidecar annotation on K2 is read via index_json fallback
    add_annotation(vault, "K2", page=1, rects=[[0.1, 0.1, 0.4, 0.2]], exact_text="new finding")
    snap_pre_db = get_base_table_snapshot(vault)
    assert snap_pre_db["state_authority"] == "index_json"
    assert snap_pre_db["rows"]["K2"]["user_ann_count"] == 1

    # Populate DB for K1 ONLY: SQLite papers SSOT governs; K2 is not resurrected
    db_path = get_memory_db_path(vault)
    conn = sqlite3.connect(str(db_path))
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO papers (zotero_key, title, domain, has_pdf, ocr_status) VALUES (?, ?, ?, ?, ?)",
        ("K1", "In DB Paper", "General", 1, "done"),
    )
    conn.commit()
    conn.close()

    snap = get_base_table_snapshot(vault)
    assert snap["state_authority"] == "sqlite"
    assert "K2" not in snap["rows"]
    assert snap["rows"]["K1"]["user_ann_count"] == 0

    # Ensure K1 (which IS in db_papers) never triggers workspace card read fallback
    from paperforge.services import memory_card_service as mcs

    called_paths: list[Path] = []
    orig_read_card = mcs._read_card_file

    def _spy_read_card(card_path: Path) -> dict:
        called_paths.append(card_path)
        return orig_read_card(card_path)

    monkeypatch.setattr(mcs, "_read_card_file", _spy_read_card)
    get_base_table_snapshot(vault)
    assert all("K1" not in str(p) for p in called_paths), called_paths


def test_annotations_jsonl_compacts_when_log_bloat_exceeds_threshold(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    bootstrap_config(vault)
    set_config(vault, "system_dir", ".paperforge")
    paths = paperforge_paths(vault)
    ws = paths["literature"] / "General" / "K1 - Sample"
    ws.mkdir(parents=True, exist_ok=True)
    paths["index"].parent.mkdir(parents=True, exist_ok=True)
    paths["index"].write_text(
        json.dumps(build_envelope([{"zotero_key": "K1", "title": "Sample", "paper_root": ws.relative_to(vault).as_posix()}])),
        encoding="utf-8",
    )

    kept = add_annotation(vault, "K1", page=1, rects=[[0.1, 0.1, 0.3, 0.2]], exact_text="keep")
    # Generate 97 update events + delete -> hits 100 lines (>2x active) right on delete and compacts to 1
    victim = add_annotation(vault, "K1", page=1, rects=[[0.2, 0.2, 0.4, 0.3]], exact_text="temp")
    for idx in range(97):
        update_annotation(vault, "K1", victim["ann_id"], comment=f"rev-{idx}")
    delete_annotation(vault, "K1", victim["ann_id"])

    jsonl_path = ws / "annotations.jsonl"
    lines = [ln for ln in jsonl_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    active = read_active_annotations_for_workspace(ws)
    assert [a["ann_id"] for a in active] == [kept["ann_id"]]
