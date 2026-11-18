"""Unit tests for the read-only `paperforge inspect` command and V3 stage dump."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pymupdf
import pytest

from paperforge import cli
from paperforge.commands.inspect_paper import inspect_paper
from paperforge.memory.builder import compute_hash
from paperforge.memory.schema import CURRENT_SCHEMA_VERSION, ensure_schema
from paperforge.worker.ocr_hash import compute_ocr_result_hash
from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION


def _tree_snapshot(root: Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            snap[rel + "/"] = "DIR"
        elif p.is_file():
            snap[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def _write_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Sample PDF for inspect test.")
    doc.save(str(path))
    doc.close()


def _init_vault_config(vault: Path) -> None:
    (vault / "paperforge.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "vault_config": {
                    "system_dir": "System",
                    "resources_dir": "Resources",
                    "literature_dir": "Literature",
                    "control_dir": "Control",
                    "base_dir": "Bases",
                    "skill_dir": ".agents/skills",
                    "command_dir": ".opencode/command",
                },
                "vector_db_api_model": "text-embedding-3-small",
            }
        ),
        encoding="utf-8",
    )


def _write_index(vault: Path, items: list[dict]) -> Path:
    index_path = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps({"schema_version": "2", "paper_count": len(items), "items": items}),
        encoding="utf-8",
    )
    return index_path


def test_inspect_missing_paper_returns_path_not_found(tmp_path: Path, capsys) -> None:
    _init_vault_config(tmp_path)
    _write_index(tmp_path, [])

    rc = cli.main(["--vault", str(tmp_path), "inspect", "MISSING1", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["command"] == "inspect"
    assert payload["error"]["code"] == "PATH_NOT_FOUND"


def test_inspect_stale_ocr_without_db_is_strictly_readonly(tmp_path: Path, capsys) -> None:
    key = "ABCD1234"
    _init_vault_config(tmp_path)

    pdf_rel = "System/Zotero/storage/STOR0001/paper.pdf"
    _write_pdf(tmp_path / pdf_rel)

    note_rel = f"Resources/Literature/{key}.md"
    note_path = tmp_path / note_rel
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("# Paper Note\n", encoding="utf-8")

    _write_index(
        tmp_path,
        [
            {
                "zotero_key": key,
                "citation_key": "doe2025test",
                "title": "Stale OCR Pipeline Paper",
                "year": "2025",
                "doi": "10.1000/stale",
                "pdf_path": pdf_rel,
                "note_path": note_rel,
                "ocr_status": "done",
                "lifecycle": "ocr_done",
            }
        ],
    )

    ocr_dir = tmp_path / "System" / "PaperForge" / "ocr" / key
    (ocr_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (ocr_dir / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps({"page": 1, "block_id": "b1", "raw_label": "text", "text": "Hello"}) + "\n",
        encoding="utf-8",
    )
    (ocr_dir / "meta.json").write_text(
        json.dumps({"zotero_key": key, "ocr_status": "done", "ocr_pipeline_version": "1.0.0"}),
        encoding="utf-8",
    )

    before = _tree_snapshot(tmp_path)
    rc = cli.main(["--vault", str(tmp_path), "inspect", key, "--json"])
    out = capsys.readouterr().out
    after = _tree_snapshot(tmp_path)

    assert before == after
    assert rc == 0

    payload = json.loads(out)
    assert payload["ok"] is True
    data = payload["data"]
    assert data["resolved"] is True
    assert data["zotero_key"] == key
    assert data["stages"]["source"]["pdf_exists"] is True
    assert data["stages"]["source"]["source_page_count"] == 1
    assert data["stages"]["ocr"]["can_rebuild_offline"] is True
    assert data["stages"]["ocr"]["pipeline_stale"] is True
    assert data["stages"]["memory"]["db_exists"] is False
    assert data["diagnosis"]["overall"] == "action_needed"
    assert data["diagnosis"]["bottleneck_stage"] == "ocr"
    joined_recs = "\n".join(data["diagnosis"]["recommended_commands"])
    assert "rebuild" in joined_recs
    assert "paperforge memory build" in joined_recs


def test_inspect_healthy_paper_and_plain_text_output(tmp_path: Path, capsys) -> None:
    key = "HLTH9999"
    _init_vault_config(tmp_path)

    pdf_rel = "System/Zotero/storage/STOR0002/healthy.pdf"
    _write_pdf(tmp_path / pdf_rel)

    note_rel = f"Resources/Literature/{key}.md"
    (tmp_path / note_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / note_rel).write_text("# Healthy Paper\n", encoding="utf-8")

    items = [
        {
            "zotero_key": key,
            "citation_key": "smith2026healthy",
            "title": "Healthy End to End Paper",
            "year": "2026",
            "doi": "10.1000/healthy",
            "pdf_path": pdf_rel,
            "note_path": note_rel,
            "ocr_status": "done",
            "lifecycle": "ready",
        }
    ]
    _write_index(tmp_path, items)

    ocr_dir = tmp_path / "System" / "PaperForge" / "ocr" / key
    for sub in ("canonical", "structure", "index", "render", "health"):
        (ocr_dir / sub).mkdir(parents=True, exist_ok=True)

    (ocr_dir / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps({"page": 1, "block_id": "b1", "raw_label": "text", "text": "Body"}) + "\n",
        encoding="utf-8",
    )
    (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps({"page": 1, "block_id": "b1", "role": "body", "text": "Body"}) + "\n",
        encoding="utf-8",
    )
    (ocr_dir / "structure" / "figure_inventory.json").write_text(
        json.dumps({"matched_figures": [{"figure_number": 1}]}),
        encoding="utf-8",
    )
    (ocr_dir / "structure" / "table_inventory.json").write_text(
        json.dumps({"tables": [{"table_number": 1}, {"table_number": 2}]}),
        encoding="utf-8",
    )
    (ocr_dir / "index" / "structure-tree.json").write_text(
        json.dumps({"root": []}), encoding="utf-8"
    )
    (ocr_dir / "index" / "role-index.json").write_text(json.dumps({}), encoding="utf-8")
    (ocr_dir / "render" / "fulltext.md").write_text("# Body\n", encoding="utf-8")
    (ocr_dir / "fulltext.md").write_text("# Body\n", encoding="utf-8")
    (ocr_dir / "render" / "render.consistency.json").write_text(
        json.dumps({"state": "CLEAN", "issues": []}),
        encoding="utf-8",
    )
    (ocr_dir / "health" / "ocr_health.json").write_text(
        json.dumps({"overall": "healthy"}),
        encoding="utf-8",
    )
    (ocr_dir / "meta.json").write_text(
        json.dumps(
            {
                "zotero_key": key,
                "ocr_status": "done",
                "ocr_pipeline_version": OCR_PIPELINE_VERSION,
                "derived_stale": False,
                "derived_version": {"ocr_pipeline_version": OCR_PIPELINE_VERSION},
            }
        ),
        encoding="utf-8",
    )

    result_hash = compute_ocr_result_hash(ocr_dir)
    assert result_hash is not None
    (ocr_dir / "index" / "result-hash.txt").write_text(result_hash, encoding="utf-8")

    db_path = tmp_path / "System" / "PaperForge" / "indexes" / "paperforge.db"
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO papers (zotero_key, citation_key, title, year, doi, ocr_status, pdf_path, note_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (key, "smith2026healthy", "Healthy End to End Paper", "2026", "10.1000/healthy", "done", pdf_rel, note_rel),
        )
        conn.execute(
            "INSERT INTO body_units (unit_id, paper_id, section_path, unit_text, page_span_json, block_span_json, token_estimate, indexable, veto_reason, quality_hints_json) "
            "VALUES (?, ?, ?, ?, '[]', '[]', 10, 1, '', '[]')",
            (f"{key}:u1", key, "Methods", "Sample text"),
        )
        conn.execute(
            "INSERT INTO object_units (unit_id, paper_id, section_path, object_kind, object_label, caption_text, page_span_json, block_span_json) "
            "VALUES (?, ?, ?, 'figure', 'Figure 1', 'Caption', '[]', '[]')",
            (f"{key}:o1", key, "Results"),
        )
        conn.execute(
            "INSERT INTO vec_body_meta (rowid, paper_id, chunk_index, unit_id, text) VALUES (1, ?, 0, ?, ?)",
            (key, f"{key}:u1", "Sample text"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("schema_version", str(CURRENT_SCHEMA_VERSION)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"manifest:{key}", json.dumps({"ocr_result_hash": result_hash})),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("canonical_index_hash", compute_hash(items)),
        )
        conn.commit()
    finally:
        conn.close()

    before = _tree_snapshot(tmp_path)
    report = inspect_paper(tmp_path, "10.1000/healthy")
    rc = cli.main(["--vault", str(tmp_path), "inspect", "smith2026healthy"])
    text_out = capsys.readouterr().out
    after = _tree_snapshot(tmp_path)

    assert before == after
    assert report is not None
    assert report["diagnosis"]["overall"] == "healthy"
    assert report["diagnosis"]["bottleneck_stage"] is None
    assert report["stages"]["objects_and_render"]["figure_count"] == 1
    assert report["stages"]["objects_and_render"]["table_count"] == 2
    assert report["stages"]["memory"]["db_fresh"] is True
    assert report["stages"]["vectors"]["vector_body_count"] == 1
    assert report["stages"]["vectors"]["configured_model"] == "text-embedding-3-small"
    assert rc == 0
    assert "Overall:     healthy" in text_out
    assert "[memory]" in text_out


def test_inspect_ambiguous_title_returns_candidates(tmp_path: Path, capsys) -> None:
    _init_vault_config(tmp_path)
    _write_index(
        tmp_path,
        [
            {"zotero_key": "KEY00001", "title": "Biomarker Study Part I", "year": "2024"},
            {"zotero_key": "KEY00002", "title": "Biomarker Study Part II", "year": "2025"},
        ],
    )

    rc = cli.main(["--vault", str(tmp_path), "inspect", "Biomarker Study", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["data"]["resolved"] is False
    keys = {c["zotero_key"] for c in payload["data"]["candidates"]}
    assert keys == {"KEY00001", "KEY00002"}


def test_dump_v3_stage_transitions_writes_all_five_stages(tmp_path: Path) -> None:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "ocr_rebuild_paper.py"
    spec = importlib.util.spec_from_file_location("ocr_rebuild_paper_dev", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ocr_rebuild_paper_dev"] = mod
    spec.loader.exec_module(mod)

    raw_blocks = [
        {
            "paper_id": "TESTKEY1",
            "page": 1,
            "block_id": "b1",
            "raw_label": "doc_title",
            "raw_order": 0,
            "text": "A Clinical Study of Biomarkers",
            "bbox": [50, 40, 550, 90],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "paper_id": "TESTKEY1",
            "page": 1,
            "block_id": "b2",
            "raw_label": "paragraph_title",
            "raw_order": 1,
            "text": "Introduction",
            "bbox": [50, 120, 220, 145],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "paper_id": "TESTKEY1",
            "page": 1,
            "block_id": "b3",
            "raw_label": "text",
            "raw_order": 2,
            "text": "We evaluated patient cohorts across three clinical centers.",
            "bbox": [50, 160, 550, 220],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "paper_id": "TESTKEY1",
            "page": 2,
            "block_id": "b4",
            "raw_label": "image",
            "raw_order": 0,
            "text": "",
            "bbox": [80, 100, 520, 340],
            "page_width": 600,
            "page_height": 800,
        },
        {
            "paper_id": "TESTKEY1",
            "page": 2,
            "block_id": "b5",
            "raw_label": "figure_title",
            "raw_order": 1,
            "text": "Figure 1. Kaplan-Meier survival curve.",
            "bbox": [80, 355, 520, 390],
            "page_width": 600,
            "page_height": 800,
        },
    ]

    summary_path = mod.dump_v3_stage_transitions(
        "TESTKEY1",
        raw_blocks,
        output_dir=tmp_path / "stage_dump",
    )
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_stages = [
        "1_seed_roles",
        "2_pre_match_normalize",
        "3_object_matching",
        "4_post_match_normalize",
        "5_object_writebacks",
    ]
    assert summary["paper_key"] == "TESTKEY1"
    assert summary["block_count"] == len(raw_blocks)
    assert summary["stages"] == expected_stages
    assert list(summary["stage_role_counts"].keys()) == expected_stages
    assert all(sum(counts.values()) == len(raw_blocks) for counts in summary["stage_role_counts"].values())
    assert summary["transition_count"] >= 1

    # Also verify CLI entrypoint --ocr-dir + --dump-stages-only + --dump-dir
    ocr_root = tmp_path / "vault" / "System" / "PaperForge" / "ocr"
    canon_dir = ocr_root / "TESTKEY1" / "canonical"
    canon_dir.mkdir(parents=True, exist_ok=True)
    (canon_dir / "blocks.raw.jsonl").write_text(
        "\n".join(json.dumps(b) for b in raw_blocks) + "\n",
        encoding="utf-8",
    )
    cli_dump_dir = tmp_path / "cli_dump"
    rc = mod.main(
        [
            "--ocr-dir",
            str(ocr_root),
            "--dump-stages-only",
            "--dump-dir",
            str(cli_dump_dir),
            "TESTKEY1",
        ]
    )
    assert rc == 0
    assert (cli_dump_dir / "stages_summary.json").is_file()
