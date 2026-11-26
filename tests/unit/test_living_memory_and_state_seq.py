"""Unit tests for Commit 1 (v2.2): Living Paper Memory Cards, state-seq, base snapshot & YAML no-op guard."""
from __future__ import annotations

import argparse
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

from paperforge.commands.note import run as run_note
from paperforge.commands.paper_context import run as run_paper_context
from paperforge.config import paperforge_paths
from paperforge.memory.builder import build_for_keys
from paperforge.services.annotations_service import add_annotation
from paperforge.services.memory_card_service import (
    clear_memory_facet,
    get_base_table_snapshot,
    get_memory_card,
    get_memory_history,
    refine_memory_facet,
)
from paperforge.services.state_signal import read_state_seq
from paperforge.worker.asset_index import _build_entry, atomic_write_index
from tests.conftest import canonical_test_config


def _make_vault(tmp_path: Path, key: str = "MEM00001") -> tuple[Path, Path, dict]:
    import pymupdf

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / f"{key} - Study"
    ws.mkdir(parents=True)
    note_path = ws / f"{key}.md"
    note_path.write_text(
        f'---\nzotero_key: "{key}"\ndomain: Ortho\n---\n',
        encoding="utf-8",
    )

    zot_st = pf / "Zotero" / "storage" / "AT1"
    zot_st.mkdir(parents=True)
    pdf_path = zot_st / "paper.pdf"
    with pymupdf.open() as doc:
        p1 = doc.new_page(width=600, height=800)
        p1.insert_text((72, 120), "Double internal control calibration in cohort.")
        doc.save(pdf_path)

    item = {
        "key": key,
        "title": "Study",
        "authors": ["Lin"],
        "first_author": "Lin",
        "year": "2025",
        "journal": "AJSM",
        "domain": "Ortho",
        "collections": ["Ortho/Knee"],
        "collection_path": "Ortho/Knee",
        "has_pdf": True,
        "analyze": True,
        "do_ocr": False,
        "ocr_status": "done",
        "attachments": [{"contentType": "application/pdf", "path": "storage:AT1/paper.pdf"}],
    }
    idx_entry = {
        **item,
        "zotero_key": key,
        "citation_key": "lin2025study",
        "pdf_path": "storage:AT1/paper.pdf",
        "paper_root": f"Resources/Literature/Ortho/{key} - Study/",
        "main_note_path": f"Resources/Literature/Ortho/{key} - Study/{key}.md",
        "note_path": f"Resources/Literature/Ortho/{key} - Study/{key}.md",
    }
    atomic_write_index(pf / "indexes" / "formal-library.json", {"version": 1, "items": [idx_entry]})
    build_for_keys(vault)
    return vault, note_path, item


def test_living_memory_evolves_with_history_and_survives_rebuild(tmp_path: Path):
    vault, ws_note, _ = _make_vault(tmp_path, key="MEM00001")
    seq0 = read_state_seq(vault)["seq"]
    assert seq0 >= 1

    r1 = refine_memory_facet(
        vault,
        "MEM00001",
        facet="research_craft",
        content="Initial observation on single control group.",
    )
    assert r1["updated"]["revision"] == 1
    seq1 = read_state_seq(vault)["seq"]
    assert seq1 == seq0 + 1

    r2 = refine_memory_facet(
        vault,
        "MEM00001",
        facet="research_craft",
        content="Synthesized insight: double internal control cancels batch drift.",
    )
    assert r2["updated"]["revision"] == 2
    assert r2["card"]["facet_count"] == 1
    assert r2["card"]["facets"][0]["content"].startswith("Synthesized insight")

    refine_memory_facet(
        vault,
        "MEM00001",
        facet="methods_params",
        content="75 Hz PEMF, 2h/day for 14 days.",
    )
    card = get_memory_card(vault, "MEM00001")
    assert card["facet_count"] == 2
    assert [f["facet"] for f in card["facets"]] == ["methods_params", "research_craft"]

    hist = get_memory_history(vault, "MEM00001", facet="research_craft")["history"]
    assert len(hist) == 2
    assert hist[0]["revision"] == 2 and hist[1]["revision"] == 1

    # DB rebuild preserves workspace ai/memory-card.json
    (vault / ".paperforge" / "indexes" / "paperforge.db").unlink()
    build_for_keys(vault)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_paper_context(argparse.Namespace(vault_path=vault, key="MEM00001", structure=False, json=True))
    assert rc == 0
    ctx = json.loads(buf.getvalue())["data"]
    assert ctx["living_memory"]["facet_count"] == 2
    assert any(f["facet"] == "research_craft" for f in ctx["living_memory"]["facets"])

    clr = clear_memory_facet(vault, "MEM00001", facet="methods_params")
    assert clr["removed"] == 1
    assert get_memory_card(vault, "MEM00001")["facet_count"] == 1


def test_base_table_snapshot_and_state_seq_bump_on_note_flag(tmp_path: Path):
    vault, _ws_note, _ = _make_vault(tmp_path, key="MEM00002")
    add_annotation(
        vault,
        "MEM00002",
        page=1,
        rects=[[0.1, 0.12, 0.5, 0.16]],
        kind="highlight",
        color="yellow",
        exact_text="Double internal control",
    )
    refine_memory_facet(vault, "MEM00002", facet="idea_logic", content="Core causal test.")

    seq_before = read_state_seq(vault)["seq"]
    rc = run_note(
        argparse.Namespace(vault=vault, vault_path=vault, note_cmd="set-flag", key="MEM00002", field="do_ocr", value="true")
    )
    assert rc == 0
    assert read_state_seq(vault)["seq"] > seq_before

    snap = get_base_table_snapshot(vault)
    assert snap["seq"] > seq_before
    row = snap["rows"]["MEM00002"]
    assert row["do_ocr"] is True
    assert row["user_ann_count"] == 1
    assert row["agent_ann_count"] == 0
    assert row["memory_facet_count"] == 1


def test_build_entry_skips_redundant_disk_write_when_note_unchanged(tmp_path: Path):
    vault, note_path, item = _make_vault(tmp_path, key="MEM00003")
    paths = paperforge_paths(vault)
    zot_dir = vault / ".paperforge" / "Zotero"

    # First pass establishes canonical frontmatter
    _build_entry(item, vault, paths, "Ortho", zot_dir)
    mtime1 = note_path.stat().st_mtime_ns
    # Set distinct old timestamp so any accidental write would change it noticeably
    old_ns = mtime1 - 5_000_000_000
    os.utime(note_path, ns=(old_ns, old_ns))

    _build_entry(item, vault, paths, "Ortho", zot_dir)
    assert note_path.stat().st_mtime_ns == old_ns


def test_bump_state_seq_is_lossless_under_concurrent_subprocesses(tmp_path: Path):
    import concurrent.futures
    import subprocess
    import sys

    vault, _, _ = _make_vault(tmp_path, key="SEQ00001")
    seq0 = read_state_seq(vault)["seq"]
    assert seq0 >= 1
    idx_dir = vault / ".paperforge" / "indexes"
    idx_dir.mkdir(parents=True, exist_ok=True)

    worker_code = (
        "import sys; from pathlib import Path; "
        "from paperforge.services.state_signal import bump_state_seq_in_dir; "
        "d = Path(sys.argv[1]); n = int(sys.argv[2]); "
        "[bump_state_seq_in_dir(d, reason=f'w{sys.argv[3]}', changed_keys=[f'K{i}']) for i in range(n)]"
    )

    def _run_worker(wid: int) -> None:
        subprocess.run(
            [sys.executable, "-c", worker_code, str(idx_dir), "5", str(wid)],
            check=True,
            capture_output=True,
            text=True,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(_run_worker, wid) for wid in range(4)]
        for fut in futs:
            fut.result()

    assert read_state_seq(vault)["seq"] == seq0 + 20


def test_delete_paper_purges_registry_catalog_lineage_and_history(tmp_path: Path):
    """PF-ARCH-003 / PF-OCR-003: removing a paper purges all dependent SSOT/telemetry tables."""
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    vault, _, _ = _make_vault(tmp_path, key="PURGE01")
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO workspace_registry(zotero_key, domain, workspace_relpath, main_note_relpath, verified_at) "
            "VALUES ('PURGE01', 'Ortho', 'Resources/Literature/Ortho/PURGE01', 'Resources/Literature/Ortho/PURGE01/PURGE01.md', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO ocr_catalog(zotero_key, ocr_status, updated_at) VALUES ('PURGE01', 'done', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO lineage(paper_id, layer, identity, updated_at) VALUES ('PURGE01', 'ocr', 'h1', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO paper_memory_history(zotero_key, facet, content, revision, created_at) "
            "VALUES ('PURGE01', 'thesis', 'old', 1, '2026-01-01')"
        )
        conn.commit()
    finally:
        conn.close()

    atomic_write_index(get_index_path(vault), build_envelope([]))
    build_for_keys(vault)

    conn = get_connection(db_path, read_only=True)
    try:
        for table, col in (
            ("papers", "zotero_key"),
            ("workspace_registry", "zotero_key"),
            ("ocr_catalog", "zotero_key"),
            ("lineage", "paper_id"),
            ("paper_memory_history", "zotero_key"),
        ):
            cnt = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}='PURGE01'").fetchone()[0]
            assert cnt == 0, f"{table} still contains PURGE01"
    finally:
        conn.close()


def test_base_snapshot_obeys_sqlite_ssot(tmp_path: Path):
    """PF-ARCH-005: get_base_table_snapshot obeys SQLite papers SSOT and never resurrects deleted keys."""
    from paperforge.memory.db import get_connection, get_memory_db_path
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    vault, _, _ = _make_vault(tmp_path, key="ACTIVE01")
    snap_before = get_base_table_snapshot(vault)
    assert snap_before["state_authority"] == "sqlite"
    assert list(snap_before["rows"].keys()) == ["ACTIVE01"]

    # Inject stale JSON rows and mutate SQLite ocr_status -> SQLite must win & ghosts excluded
    atomic_write_index(
        get_index_path(vault),
        build_envelope([
            {"zotero_key": "ACTIVE01", "title": "Stale Title", "ocr_status": "pending", "domain": "Ortho"},
            {"zotero_key": "GHOST_JSON", "title": "Ghost Paper", "ocr_status": "done", "domain": "Ortho"},
        ]),
    )
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE papers SET ocr_status='done' WHERE zotero_key='ACTIVE01'")
        conn.commit()
    finally:
        conn.close()

    snap_after = get_base_table_snapshot(vault)
    assert snap_after["state_authority"] == "sqlite"
    assert list(snap_after["rows"].keys()) == ["ACTIVE01"]
    assert snap_after["rows"]["ACTIVE01"]["ocr_status"] == "done"

    # Empty papers table must stay empty even if formal-library.json still has stale rows
    conn = get_connection(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DELETE FROM papers")
        conn.commit()
    finally:
        conn.close()
    snap_empty = get_base_table_snapshot(vault)
    assert snap_empty["state_authority"] == "sqlite"
    assert snap_empty["rows"] == {}
