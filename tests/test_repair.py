"""Tests for run_repair() — three-way OCR status divergence detection and repair."""
from __future__ import annotations

import json
import re

import pytest

from pipeline.worker.scripts.literature_pipeline import run_repair, pipeline_paths


def _make_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    system = vault / "99_System"
    pf = system / "PaperForge"
    (pf / "exports").mkdir(parents=True)
    (pf / "ocr").mkdir(parents=True)
    resources = vault / "03_Resources"
    literature = resources / "Literature"
    literature.mkdir(parents=True)
    control = resources / "LiteratureControl"
    control.mkdir(parents=True)
    records = control / "library-records"
    records.mkdir(parents=True)
    (vault / "05_Bases").mkdir(parents=True)
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)
    cfg = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
    }
    (vault / "paperforge.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return vault


def _write_library_record(records_dir, key, domain, ocr_status, do_ocr="false", analyze="false"):
    record_path = records_dir / f"{key}.md"
    content = f"""---
zotero_key: {key}
domain: {domain}
title: "Test Paper {key}"
year: 2024
doi: "10.1234/test"
has_pdf: true
pdf_path: ""
fulltext_md_path: ""
recommend_analyze: true
analyze: {analyze}
do_ocr: {do_ocr}
ocr_status: {ocr_status}
deep_reading_status: pending
analysis_note: ""
---
# Test Paper {key}
"""
    record_path.write_text(content, encoding="utf-8")
    return record_path


def _write_formal_note(literature_dir, key, domain, ocr_status):
    domain_lit = literature_dir / domain
    domain_lit.mkdir(parents=True, exist_ok=True)
    note_path = domain_lit / f"{key} - Test.md"
    content = f"""---
title: "Test Paper {key}"
year: 2024
domain: "{domain}"
zotero_key: "{key}"
doi: "10.1234/test"
ocr_status: {ocr_status}
deep_reading_status: pending
---
# Test Paper {key}
"""
    note_path.write_text(content, encoding="utf-8")
    return note_path


def _write_meta(ocr_root, key, ocr_status, zotero_key=None, page_count=10, with_fulltext=True, with_json=True):
    meta_dir = ocr_root / key
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "zotero_key": zotero_key or key,
        "ocr_status": ocr_status,
        "page_count": page_count,
    }
    if with_fulltext:
        ft = meta_dir / "fulltext.md"
        page_lines = []
        for i in range(1, page_count + 1):
            page_lines.append(f"<!-- page {i} -->")
            page_lines.append("x" * 100)
        ft.write_text("\n".join(page_lines), encoding="utf-8")
        meta["markdown_path"] = f"99_System/PaperForge/ocr/{key}/fulltext.md"
        meta["fulltext_md_path"] = f"99_System/PaperForge/ocr/{key}/fulltext.md"
    if with_json:
        json_dir = meta_dir / "json"
        json_dir.mkdir(parents=True, exist_ok=True)
        result = json_dir / "result.json"
        pages_data = [{"text": "x" * 200} for _ in range(page_count)]
        result.write_text(json.dumps({"pages": pages_data}, ensure_ascii=False), encoding="utf-8")
        meta["json_path"] = f"99_System/PaperForge/ocr/{key}/json/result.json"
    (meta_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta_dir / "meta.json"


def _write_minimal_meta(ocr_root, key, ocr_status):
    meta_dir = ocr_root / key
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {"zotero_key": key, "ocr_status": ocr_status}
    (meta_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta_dir / "meta.json"


class TestRunRepairScanOnly:
    def test_no_records_returns_empty(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 0
        assert result["divergent"] == []
        assert result["fixed"] == 0
        assert result["errors"] == []

    def test_all_consistent_pending_no_divergence(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    def test_meta_done_incomplete_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["zotero_key"] == "KEY001"
        assert "done_incomplete" in result["divergent"][0]["reason"]

    def test_library_done_but_meta_pending_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["library_record_ocr_status"] == "done"
        assert result["divergent"][0]["meta_ocr_status"] == "pending"

    def test_library_done_but_meta_missing_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "done")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1

    def test_formal_note_done_but_meta_missing_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        literature_dir = vault / "03_Resources" / "Literature"
        _write_library_record(records_dir, "KEY001", "骨科", "pending")
        _write_formal_note(literature_dir, "KEY001", "骨科", "done")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1

    def test_library_vs_meta_post_validation_mismatch_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "done", page_count=10)
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    def test_library_nopdf_not_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "nopdf")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    def test_multiple_domains_scanned(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir_ortho = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir_ortho.mkdir(parents=True, exist_ok=True)
        records_dir_sports = vault / "03_Resources" / "LiteratureControl" / "library-records" / "运动医学"
        records_dir_sports.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir_ortho, "KEY001", "骨科", "pending")
        _write_library_record(records_dir_sports, "KEY002", "运动医学", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 2

    def test_verbose_output_printed(self, tmp_path, capsys):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=True, fix=False)
        captured = capsys.readouterr()
        assert "KEY001" in captured.out
        assert "divergent" in captured.out


class TestRunRepairFixMode:
    def test_fix_meta_missing_sets_all_to_pending_and_sets_do_ocr(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        lit_dir = vault / "03_Resources" / "Literature"
        record_path = _write_library_record(records_dir, "KEY001", "骨科", "done", do_ocr="false")
        _write_formal_note(lit_dir, "KEY001", "骨科", "done")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        record_text = record_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', record_text, re.MULTILINE)
        assert re.search(r'^do_ocr:\s*"?true"?', record_text, re.MULTILINE)

    def test_fix_done_incomplete_meta_sets_to_pending(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        record_path = _write_library_record(records_dir, "KEY001", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        record_text = record_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', record_text, re.MULTILINE)

    def test_fix_library_done_meta_pending_sets_library_to_pending(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        record_path = _write_library_record(records_dir, "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        record_text = record_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', record_text, re.MULTILINE)

    def test_fix_false_does_not_write_anything(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        record_path = _write_library_record(records_dir, "KEY001", "骨科", "done")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        original_content = record_path.read_text(encoding="utf-8")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["fixed"] == 0
        assert record_path.read_text(encoding="utf-8") == original_content

    def test_fix_multiple_divergent_items(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        record1_path = _write_library_record(records_dir, "KEY001", "骨科", "done", do_ocr="false")
        record2_path = _write_library_record(records_dir, "KEY002", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        _write_minimal_meta(paths["ocr"], "KEY002", "done")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert len(result["divergent"]) == 2
        assert result["fixed"] >= 1

    def test_no_divergence_fix_reports_zero_fixed(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "pending")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] == 0

    def test_fix_writes_formal_note_ocr_status(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        lit_dir = vault / "03_Resources" / "Literature"
        _write_library_record(records_dir, "KEY001", "骨科", "done", do_ocr="false")
        note_path = _write_formal_note(lit_dir, "KEY001", "骨科", "done")
        result = run_repair(vault, paths, verbose=False, fix=True)
        note_text = note_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', note_text, re.MULTILINE)


class TestRunRepairReturnStructure:
    def test_result_has_all_keys(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert "scanned" in result
        assert "divergent" in result
        assert "fixed" in result
        assert "errors" in result
        assert isinstance(result["scanned"], int)
        assert isinstance(result["divergent"], list)
        assert isinstance(result["fixed"], int)
        assert isinstance(result["errors"], list)

    def test_divergent_item_has_required_fields(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        records_dir = vault / "03_Resources" / "LiteratureControl" / "library-records" / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        _write_library_record(records_dir, "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        item = result["divergent"][0]
        assert "zotero_key" in item
        assert "domain" in item
        assert "library_record_ocr_status" in item
        assert "formal_note_ocr_status" in item
        assert "meta_ocr_status" in item
        assert "reason" in item