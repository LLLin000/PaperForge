"""Unit tests for Commit 3A: hybrid retrieval full union, metadata hydration, and BM25 deep gate."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from paperforge.cli import main as cli_main
from paperforge.embedding.search import _fuse_results, hybrid_search
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import (
    CREATE_BODY_UNITS,
    CREATE_BODY_UNITS_FTS,
    CREATE_META,
    CREATE_OBJECT_UNITS,
    CREATE_PAPERS,
)
from tests.conftest import canonical_test_config


def test_fuse_results_keeps_pure_semantic_body_hits_alongside_bm25() -> None:
    bm25 = [
        {
            "paper_id": "P1",
            "source": "body",
            "unit_id": "P1:u1",
            "text": "Exact keyword match",
            "bm25_score": 0.4,
            "title": "Paper 1",
            "first_author": "Smith",
            "year": "2024",
            "journal": "AJSM",
            "domain": "Ortho",
            "heading": "Methods",
        }
    ]
    vec = [
        {
            "paper_id": "P2",
            "source": "body",
            "unit_id": "P2:u9",
            "text": "Semantic synonym hit without keyword",
            "vec_score": 0.9,
        }
    ]

    fused = _fuse_results(bm25, vec, limit=5)
    assert len(fused) == 2
    by_unit = {r["unit_id"]: r for r in fused}
    assert "P1:u1" in by_unit
    assert "P2:u9" in by_unit
    assert by_unit["P2:u9"]["vec_score"] == 0.9


def test_hybrid_search_hydrates_paper_metadata_and_heading_on_vec_only_hits(
    tmp_path: Path,
) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    db_path = get_memory_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    conn.executescript(CREATE_META + CREATE_PAPERS + CREATE_BODY_UNITS + CREATE_BODY_UNITS_FTS + CREATE_OBJECT_UNITS)
    conn.execute(
        "INSERT INTO papers (zotero_key, title, year, first_author, journal, domain) VALUES (?, ?, ?, ?, ?, ?)",
        ("PVEC1", "Hydrated Seminal Paper", "2025", "Lin", "Lancet", "Ortho"),
    )
    conn.execute(
        """INSERT INTO body_units
           (unit_id, paper_id, section_path, section_path_json, section_level, section_title,
            unit_text, unit_kind, part_ordinal, page_span_json, block_span_json,
            token_estimate, indexable, veto_reason, quality_hints_json)
           VALUES ('PVEC1:u5', 'PVEC1', 'Results > Primary', '[]', 2, 'Primary Outcomes',
                   'No lexical match text here', 'body', 0, '[]', '[]', 10, 1, '', '[]')"""
    )
    conn.commit()
    conn.close()

    with patch("paperforge.embedding.search._vec_search", return_value=[
        {"paper_id": "PVEC1", "unit_id": "PVEC1:u5", "source": "body", "text": "No lexical match text here", "vec_score": 0.85}
    ]):
        with patch("paperforge.embedding.search.OpenAICompatibleProvider") as mock_prov:
            mock_prov.return_value.encode_single.return_value = [0.1, 0.2]
            hits = hybrid_search(tmp_path, "completely different query", limit=5)

    assert len(hits) == 1
    assert hits[0]["title"] == "Hydrated Seminal Paper"
    assert hits[0]["first_author"] == "Lin"
    assert hits[0]["year"] == "2025"
    assert hits[0]["heading"] == "Primary Outcomes"


def test_retrieve_deep_allows_bm25_when_vectors_not_built_and_blocks_stale_vector_only(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")

    fake_hits = [
        {"paper_id": "P_BM25", "unit_id": "P_BM25:u1", "source": "body", "text": "BM25 hit", "bm25_score": 0.7, "vec_score": 0.0, "score": 0.7, "title": "BM25 Paper"},
        {"paper_id": "P_STALE_VEC", "unit_id": "P_STALE_VEC:u1", "source": "body", "text": "Stale vec", "bm25_score": 0.0, "vec_score": 0.8, "score": 0.56, "title": "Stale Paper"},
        {"paper_id": "P_DUAL", "unit_id": "P_DUAL:u1", "source": "body", "text": "Dual hit", "bm25_score": 0.6, "vec_score": 0.8, "score": 0.65, "title": "Dual Paper"},
    ]
    fake_probe = {
        "papers": {
            "P_BM25": {"ocr": "current", "retrieval": "current", "vector": "missing"},
            "P_STALE_VEC": {"ocr": "current", "retrieval": "current", "vector": "stale"},
            "P_DUAL": {"ocr": "current", "retrieval": "current", "vector": "stale"},
        }
    }

    monkeypatch.setattr("paperforge.embedding.search.hybrid_search", lambda *a, **kw: fake_hits)
    monkeypatch.setattr("paperforge.lineage.observe_lineage_papers", lambda vault, pids: fake_probe)

    rc = cli_main(["--vault", str(tmp_path), "retrieve", "acl injury", "--deep", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    keys = {m["zotero_key"] for m in payload["data"]["matches"]}
    assert "P_BM25" in keys
    assert "P_DUAL" in keys  # downgraded cleanly to BM25 score
    assert "P_STALE_VEC" not in keys  # stale vector-only never leaks
    dual = next(m for m in payload["data"]["matches"] if m["zotero_key"] == "P_DUAL")
    assert dual["score"] == 0.6


def test_retrieve_deep_real_bm25_without_vectors_and_missing_db(
    tmp_path: Path, capsys
) -> None:
    """Real unmocked `retrieve --deep`: safe empty return before DB exists, and real BM25 hits without vectors."""
    import shutil
    import pymupdf
    from paperforge.config import load_config, resolve_paths
    from paperforge.worker.ocr_artifacts import compute_pdf_fingerprint
    from tests.conftest import EXPORT_FIXTURE, OCR_FIXTURE

    canonical_test_config(tmp_path, system_dir=".paperforge")

    # (a) Before memory DB exists, retrieve --deep must not crash with OperationalError
    rc_empty = cli_main(["--vault", str(tmp_path), "retrieve", "suture anchor", "--deep", "--json"])
    assert rc_empty == 0
    payload_empty = json.loads(capsys.readouterr().out)
    assert payload_empty["ok"] is True
    assert payload_empty["data"]["matches"] == []

    # (b) Seed canonical OCR fixture, sync -> memory build (NO embed build / NO vectors)
    paths = resolve_paths(tmp_path, load_config(tmp_path))
    pdf_path = paths["zotero_dir"] / "storage" / "TSTONE001" / "TSTONE001.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(pdf_path)

    paths["exports"].mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXPORT_FIXTURE, paths["exports"] / "骨科.json")

    key = "TSTONE001"
    ocr_target = paths["ocr"] / key
    shutil.copytree(OCR_FIXTURE, ocr_target, dirs_exist_ok=True)
    meta_file = ocr_target / "meta.json"
    meta_obj = json.loads(meta_file.read_text(encoding="utf-8"))
    meta_obj["raw_version"]["pdf_fingerprint"] = compute_pdf_fingerprint(pdf_path)
    meta_file.write_text(json.dumps(meta_obj), encoding="utf-8")

    assert cli_main(["--vault", str(tmp_path), "sync", "--json"]) == 0
    assert cli_main(["--vault", str(tmp_path), "memory", "build", "--json"]) == 0
    _ = capsys.readouterr()

    rc_real = cli_main(["--vault", str(tmp_path), "retrieve", "suture anchor", "--deep", "--json"])
    assert rc_real == 0
    payload_real = json.loads(capsys.readouterr().out)
    assert payload_real["ok"] is True
    matched_keys = [m["zotero_key"] for m in payload_real["data"]["matches"]]
    assert key in matched_keys
