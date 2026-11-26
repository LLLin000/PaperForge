"""Cross-subsystem Performance & Blocker Regression Benchmark Suite.

Covers every non-plugin subsystem (Python identity scanner, upgrade census,
SQLite retrieval & reader gate, Base generator, OCR V3 pipeline, and
Rust native `paperforge-daemon` stdio RPC) with reproducible budgets.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

from paperforge.config import load_config, resolve_paths
from paperforge.memory.db import get_connection
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.gateway import route_gateway
from paperforge.services.identity_resolver import scan_vault_identities
from paperforge.services.vault_upgrade import inspect_vault_upgrade
from paperforge.worker.base_views import ensure_base_views
from paperforge.worker.ocr_blocks import build_structured_blocks
from paperforge.worker.ocr_object_stage import commit_object_roles, run_association_stage
from paperforge.worker.ocr_post_match_normalize import post_match_normalize
from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize


def _col_meta(conn: sqlite3.Connection, table: str):
    return [(r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _make_row(meta, overrides):
    cols, vals = [], []
    for name, typ, notnull, dflt in meta:
        if name in overrides:
            cols.append(name)
            vals.append(overrides[name])
        elif notnull and dflt is None:
            cols.append(name)
            vals.append(0 if "INT" in (typ or "").upper() else "")
    return cols, vals


def _seed_benchmark_vault(vault: Path, paper_count: int = 2000, workspace_dirs: int = 600) -> Path:
    eng = vault / ".paperforge"
    idx = eng / "indexes"
    idx.mkdir(parents=True, exist_ok=True)
    (vault / "paperforge.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "vault_config": {
                    "system_dir": ".paperforge",
                    "literature_dir": "Resources/Literature",
                    "resources_dir": "Resources",
                    "base_dir": "Bases",
                },
            }
        ),
        encoding="utf-8",
    )
    db_path = idx / "paperforge.db"
    conn = get_connection(db_path)
    try:
        ensure_schema(conn)
        acols = _col_meta(conn, "paper_annotations")
        mcols = _col_meta(conn, "paper_memory_cards")
        bcols = _col_meta(conn, "body_units")

        now = "2026-01-01T00:00:00Z"
        items, papers_rows, ann_rows, mem_rows, body_rows = [], [], [], [], []
        ann_cols, mem_cols, body_cols = [], [], []
        for i in range(paper_count):
            k = f"KEY{i:05d}"
            dom = ["Stroke", "Cardiology", "Oncology", "Neuro", "Chest"][i % 5]
            title = f"Deep {dom} Imaging Biomarker Study {i} Multimodal Radiology"
            abstract = f"Retrospective cohort evaluating deep learning {dom} sensitivity specificity n={100 + i}"
            items.append(
                {
                    "zotero_key": k,
                    "title": title,
                    "first_author": f"Author{i % 50}",
                    "year": str(2015 + (i % 11)),
                    "journal": "Radiology",
                    "impact_factor": "12.5",
                    "domain": dom,
                    "has_pdf": True,
                    "ocr_status": "done",
                    "deep_reading_status": "done",
                    "main_note_path": f"Resources/Literature/{dom}/{k}/{k}.md",
                    "collections": ["Core"],
                }
            )
            papers_rows.append(
                (
                    k,
                    title,
                    f"Author{i % 50}",
                    str(2015 + (i % 11)),
                    "Radiology",
                    dom,
                    abstract,
                    "done",
                    "done",
                    f"Resources/Literature/{dom}/{k}/{k}.md",
                )
            )
            for a in range(3):
                c, v = _make_row(
                    acols,
                    {
                        "ann_id": f"ann_{k}_{a}",
                        "paper_id": k,
                        "page": a + 1,
                        "kind": "highlight",
                        "color": "yellow",
                        "author": "user",
                        "exact_text": f"Sample quote {i}",
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                ann_cols = c
                ann_rows.append(tuple(v))
            c, v = _make_row(
                mcols,
                {
                    "zotero_key": k,
                    "facet": "idea_logic",
                    "content": f"Core hypothesis for {dom} study {i}",
                    "updated_at": now,
                },
            )
            mem_cols = c
            mem_rows.append(tuple(v))
            for b in range(10):
                c, v = _make_row(
                    bcols,
                    {
                        "unit_id": f"{k}_u{b}",
                        "paper_id": k,
                        "unit_type": "paragraph",
                        "section_path": "Methods > Cohort",
                        "text": f"Methods text about {dom} sensitivity specificity cohort {i} block {b}",
                        "indexable": 1,
                    },
                )
                body_cols = c
                body_rows.append(tuple(v))

        (idx / "formal-library.json").write_text(json.dumps({"items": items}), encoding="utf-8")
        conn.executemany(
            "INSERT OR REPLACE INTO papers (zotero_key, title, first_author, year, journal, domain, abstract, ocr_status, deep_reading_status, main_note_path) VALUES (?,?,?,?,?,?,?,?,?,?)",
            papers_rows,
        )
        conn.execute("INSERT INTO paper_fts(paper_fts) VALUES('rebuild')")
        conn.executemany(
            f"INSERT OR REPLACE INTO paper_annotations ({','.join(ann_cols)}) VALUES ({','.join(['?'] * len(ann_cols))})",
            ann_rows,
        )
        conn.executemany(
            f"INSERT OR REPLACE INTO paper_memory_cards ({','.join(mem_cols)}) VALUES ({','.join(['?'] * len(mem_cols))})",
            mem_rows,
        )
        conn.executemany(
            f"INSERT OR REPLACE INTO body_units ({','.join(body_cols)}) VALUES ({','.join(['?'] * len(body_cols))})",
            body_rows,
        )
        conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('rebuild')")
        conn.commit()
    finally:
        conn.close()

    lit_root = vault / "Resources" / "Literature" / "Stroke"
    for i in range(workspace_dirs):
        d = lit_root / f"KEY{i:05d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"KEY{i:05d}.md").write_text(
            f"---\nzotero_key: KEY{i:05d}\ntitle: Test {i}\nocr_status: done\n---\nBody\n",
            encoding="utf-8",
        )
    return db_path


def test_cross_subsystem_performance_scorecard(tmp_path: Path) -> None:
    """Measure every backend/daemon/OCR subsystem against explicit latency budgets."""
    vault = tmp_path / "bench_vault"
    db_path = _seed_benchmark_vault(vault, paper_count=2000, workspace_dirs=600)
    scorecard: list[tuple[str, str, str]] = []

    # 1. Vault Identity Scanner & Upgrade Census (600 paper workspaces)
    # First call primes Windows Defender / NTFS cache on freshly written temp files;
    # warm pass measures PaperForge's own algorithmic + syscall latency cleanly.
    t0 = time.perf_counter()
    scan_cold = scan_vault_identities(vault / "Resources" / "Literature")
    scan_cold_ms = (time.perf_counter() - t0) * 1000
    assert len(scan_cold.workspaces) == 600

    t0 = time.perf_counter()
    scan = scan_vault_identities(vault / "Resources" / "Literature")
    scan_ms = (time.perf_counter() - t0) * 1000
    assert len(scan.workspaces) == 600
    scorecard.append(
        ("scan_vault_identities (600 workspaces, warm / cold)", f"{scan_ms:.2f} / {scan_cold_ms:.2f} ms", "warm < 2000.00 ms")
    )
    assert scan_ms < 2000

    t0 = time.perf_counter()
    upg = inspect_vault_upgrade(vault)
    upg_ms = (time.perf_counter() - t0) * 1000
    assert upg["provenance"]["state"] in ("standard_current", "veteran_legacy")
    scorecard.append(("inspect_vault_upgrade (600 workspaces)", f"{upg_ms:.2f} ms", "< 2000.00 ms"))
    assert upg_ms < 2000

    # 2. Retrieval Gateway + Reader Gate (2,000 papers + 20,000 body units)
    t0 = time.perf_counter()
    res_exact = route_gateway(vault, "paper-lookup", "KEY01999", json_mode=True, limit=10)
    exact_ms = (time.perf_counter() - t0) * 1000
    assert res_exact.ok and res_exact.data.get("count") == 1
    scorecard.append(("route_gateway exact zotero_key (2k papers)", f"{exact_ms:.2f} ms", "< 50.00 ms"))
    assert exact_ms < 50

    t0 = time.perf_counter()
    res_lookup = route_gateway(vault, "paper-lookup", "Stroke Biomarker", json_mode=True, limit=10)
    lookup_ms = (time.perf_counter() - t0) * 1000
    assert res_lookup.ok
    scorecard.append(("route_gateway paper-lookup (2k papers)", f"{lookup_ms:.2f} ms", "< 100.00 ms"))
    assert lookup_ms < 100

    t0 = time.perf_counter()
    res_cd_empty = route_gateway(vault, "content-discovery", "UnmatchedTokenZzz", json_mode=True, limit=10)
    cd_empty_ms = (time.perf_counter() - t0) * 1000
    assert res_cd_empty.ok
    scorecard.append(("route_gateway content-discovery empty hit (20k units)", f"{cd_empty_ms:.2f} ms", "< 80.00 ms"))
    assert cd_empty_ms < 80

    t0 = time.perf_counter()
    res_cd = route_gateway(vault, "content-discovery", "Stroke sensitivity", json_mode=True, limit=10)
    cd_ms = (time.perf_counter() - t0) * 1000
    assert res_cd.ok
    scorecard.append(("route_gateway content-discovery (20k units)", f"{cd_ms:.2f} ms", "< 180.00 ms"))
    assert cd_ms < 180

    # 3. Base Views YAML Generator
    cfg = load_config(vault)
    paths = resolve_paths(vault, snapshot=cfg)
    t0 = time.perf_counter()
    ensure_base_views(vault, paths, cfg.values)
    bv_fresh_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    ensure_base_views(vault, paths, cfg.values)
    bv_idem_ms = (time.perf_counter() - t0) * 1000
    scorecard.append(("ensure_base_views (fresh / idempotent)", f"{bv_fresh_ms:.2f} / {bv_idem_ms:.2f} ms", "< 150.00 ms"))
    assert bv_fresh_ms < 150 and bv_idem_ms < 100

    # 4. OCR V3 Pipeline (20 pages / 500 blocks)
    raw_blocks = []
    block_idx = 0
    for p in range(1, 21):
        for b in range(25):
            lbl = "figure" if b == 5 else ("figure_title" if b == 6 else ("table" if b == 15 else ("table_title" if b == 14 else "text")))
            txt = (
                f"Figure {p}. ROC analysis of deep learning model."
                if b == 6
                else (
                    f"Table {p}. Baseline characteristics."
                    if b == 14
                    else f"Page {p} block {b} sensitivity 94.2% specificity 91.8% in stroke cohorts."
                )
            )
            raw_blocks.append(
                {
                    "paper_id": "BENCHOCR",
                    "page": p,
                    "block_id": f"p{p}_b{b}",
                    "raw_label": lbl,
                    "raw_order": block_idx,
                    "text": txt,
                    "bbox": [60, 30 + b * 28, 540, 56 + b * 28],
                    "page_width": 600,
                    "page_height": 800,
                }
            )
            block_idx += 1

    t0 = time.perf_counter()
    structured, doc_struct = build_structured_blocks(raw_blocks)
    structured, doc_struct = pre_match_normalize(structured, document_structure=doc_struct)
    stage = run_association_stage(structured)
    structured, _ = post_match_normalize(
        structured,
        figure_inventory=stage.figures,
        table_inventory=stage.tables,
        document_structure=doc_struct,
    )
    commit_object_roles(structured, stage.figures, stage.tables)
    ocr_ms = (time.perf_counter() - t0) * 1000
    assert len(structured) == 500
    assert stage.figures.get("completeness", {}).get("total_numbered_legends") == 20
    scorecard.append(("OCR V3 pipeline (20p / 500 blocks)", f"{ocr_ms:.2f} ms", "< 500.00 ms"))
    assert ocr_ms < 500

    # 5. Rust Native Daemon (`paperforge-daemon.exe` if compiled)
    repo_root = Path(__file__).resolve().parent.parent
    daemon_exe = repo_root / "crates" / "paperforge-daemon" / "target" / "release" / "paperforge-daemon.exe"
    if not daemon_exe.exists():
        daemon_exe = repo_root / "crates" / "paperforge-daemon" / "target" / "release" / "paperforge-daemon"
    if daemon_exe.exists():
        t_sp = time.perf_counter()
        proc = subprocess.Popen(
            [str(daemon_exe), "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            def rpc(req: dict):
                t = time.perf_counter()
                assert proc.stdin is not None and proc.stdout is not None
                proc.stdin.write(json.dumps(req) + "\n")
                proc.stdin.flush()
                line = proc.stdout.readline()
                return (time.perf_counter() - t) * 1000, json.loads(line)

            rpc({"id": 1, "op": "ping"})
            spawn_ping_ms = (time.perf_counter() - t_sp) * 1000
            snap_cold_ms, r1 = rpc({"id": 2, "op": "exec", "vault": str(vault), "argv": ["memory-card", "base-snapshot", "--json"]})
            snap_warm_ms, r2 = rpc({"id": 3, "op": "exec", "vault": str(vault), "argv": ["memory-card", "base-snapshot", "--json"]})
            search_ms, r3 = rpc({"id": 4, "op": "exec", "vault": str(vault), "argv": ["search", "Stroke", "--json"]})
            eng_ms, r4 = rpc({"id": 5, "op": "engine.status", "vault": str(vault)})
            rpc({"id": 99, "op": "shutdown"})
            assert r1.get("exit_code") == 0 and r2.get("exit_code") == 0
            assert r3.get("exit_code") == 0 and r4.get("ok") is True
            scorecard.append(("Rust daemon spawn + ping", f"{spawn_ping_ms:.2f} ms", "< 150.00 ms"))
            scorecard.append(("Rust base-snapshot (2k papers, cold)", f"{snap_cold_ms:.2f} ms", "< 250.00 ms"))
            scorecard.append(("Rust base-snapshot (2k papers, cached warm)", f"{snap_warm_ms:.2f} ms", "< 25.00 ms"))
            scorecard.append(("Rust FTS5 search (2k papers + 20k units)", f"{search_ms:.2f} ms", "< 30.00 ms"))
            scorecard.append(("Rust engine.status", f"{eng_ms:.2f} ms", "< 15.00 ms"))
            assert spawn_ping_ms < 150
            assert snap_cold_ms < 250
            assert snap_warm_ms < 25
            assert search_ms < 30
            assert eng_ms < 15
        finally:
            proc.wait(timeout=5)
    else:
        scorecard.append(("Rust daemon", "binary absent (skipped)", "n/a"))

    print("\n=== PaperForge Cross-Subsystem Performance Scorecard ===")
    for name, val, budget in scorecard:
        print(f"  - {name}: {val} (budget {budget})")
    print("========================================================")
    assert db_path.exists()
