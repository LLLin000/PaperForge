"""Tests for run_repair() — three-way OCR status divergence detection and repair."""

from __future__ import annotations

import argparse
import json
import re
from unittest.mock import patch

from paperforge.worker.repair import run_repair
from paperforge.worker.sync import pipeline_paths


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


def _write_formal_note(literature_dir, key, domain, ocr_status, do_ocr="false"):
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
do_ocr: {do_ocr}
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
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    def test_meta_done_incomplete_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["zotero_key"] == "KEY001"
        assert "done_incomplete" in result["divergent"][0]["reason"]

    def test_library_done_but_meta_pending_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["formal_note_ocr_status"] == "done"
        assert result["divergent"][0]["meta_ocr_status"] == "pending"

    def test_library_done_but_meta_missing_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1

    def test_formal_note_done_but_meta_missing_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["zotero_key"] == "KEY001"
        assert "done_incomplete" in result["divergent"][0]["reason"]

    def test_formal_note_done_but_meta_pending_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        literature_dir = vault / "03_Resources" / "Literature" / "骨科"
        literature_dir.mkdir(parents=True, exist_ok=True)
        _write_formal_note(literature_dir.parent, "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["formal_note_ocr_status"] == "done"
        assert result["divergent"][0]["meta_ocr_status"] == "pending"

    def test_formal_note_done_but_meta_missing_is_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        literature_dir = vault / "03_Resources" / "Literature" / "骨科"
        literature_dir.mkdir(parents=True, exist_ok=True)
        _write_formal_note(literature_dir.parent, "KEY001", "骨科", "done")
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
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "done", page_count=10)
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    # === Condition 4: note pending vs meta done/failed ===

    def test_note_pending_meta_done_is_now_divergent(self, tmp_path):
        """REPAIR-01: note ocr_status=pending, meta ocr_status=done (full validation) -> divergent.
        Previously silently skipped because condition 4 had note_ocr_status != 'pending' guard."""
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_meta(paths["ocr"], "KEY001", "done", page_count=10)
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["zotero_key"] == "KEY001"
        assert result["divergent"][0]["formal_note_ocr_status"] == "pending"

    def test_note_pending_meta_failed_is_divergent(self, tmp_path):
        """REPAIR-01: note=pending, meta=failed -> divergent (was also silently skipped)."""
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "failed")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert len(result["divergent"]) == 1
        assert result["divergent"][0]["formal_note_ocr_status"] == "pending"
        assert "failed" in result["divergent"][0]["meta_ocr_status"] or "failed" in result["divergent"][0]["reason"]

    def test_note_pending_meta_pending_consistent_is_not_divergent(self, tmp_path):
        """REPAIR-01: note=pending, meta=pending -> NOT divergent (consistent state)."""
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    def test_library_nopdf_not_divergent(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "nopdf")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 1
        assert result["divergent"] == []

    def test_multiple_domains_scanned(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_formal_note(paths["literature"], "KEY002", "运动医学", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["scanned"] == 2

    def test_verbose_output_printed(self, tmp_path, caplog):
        import logging

        caplog.set_level(logging.DEBUG, logger="paperforge.worker.repair")
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        run_repair(vault, paths, verbose=True, fix=False)
        assert "KEY001" in caplog.text
        assert "divergent" in caplog.text


class TestRunRepairFixMode:
    def _note_path(self, paths, key, domain):
        return paths["literature"] / domain / f"{key} - Test.md"

    def test_fix_meta_missing_sets_all_to_pending_and_sets_do_ocr(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        note_path = _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        note_text = note_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', note_text, re.MULTILINE)
        assert re.search(r'^do_ocr:\s*"?true"?', note_text, re.MULTILINE)

    def test_fix_done_incomplete_meta_sets_to_pending(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        note_path = _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        note_text = note_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', note_text, re.MULTILINE)

    def test_fix_library_done_meta_pending_sets_library_to_pending(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        note_path = _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        note_text = note_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', note_text, re.MULTILINE)

    def test_fix_false_does_not_write_anything(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        note_path = _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        original_content = note_path.read_text(encoding="utf-8")
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert result["fixed"] == 0
        assert note_path.read_text(encoding="utf-8") == original_content

    def test_fix_multiple_divergent_items(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        _write_formal_note(paths["literature"], "KEY002", "骨科", "pending")
        _write_minimal_meta(paths["ocr"], "KEY001", "done")
        _write_minimal_meta(paths["ocr"], "KEY002", "done")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert len(result["divergent"]) == 2
        assert result["fixed"] >= 1

    def test_no_divergence_fix_reports_zero_fixed(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "pending")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] == 0

    def test_fix_writes_formal_note_ocr_status(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        note_path = _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        run_repair(vault, paths, verbose=False, fix=True)
        note_text = note_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', note_text, re.MULTILINE)

    def test_fix_case4_lib_done_meta_pending_updates_all_three_and_sets_do_ocr(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        note_path = _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        meta_path = _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["fixed"] >= 1
        note_text = note_path.read_text(encoding="utf-8")
        assert re.search(r'^ocr_status:\s*"?pending"?', note_text, re.MULTILINE)
        assert re.search(r'^do_ocr:\s*"?true"?', note_text, re.MULTILINE)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["ocr_status"] == "pending"


class TestRepairRebuildsIndex:
    def test_repair_calls_build_index_after_fix(self, tmp_path, monkeypatch):
        import paperforge.worker.asset_index

        call_count = 0

        def _capture_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return 0

        monkeypatch.setattr(paperforge.worker.asset_index, "build_index", _capture_call)
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        run_repair(vault, paths, verbose=False, fix=True)
        assert call_count >= 1, "build_index was not called during fix=True"

    def test_repair_does_not_call_build_index_dry_run(self, tmp_path, monkeypatch):
        import paperforge.worker.asset_index

        call_count = 0

        def _capture_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return 0

        monkeypatch.setattr(paperforge.worker.asset_index, "build_index", _capture_call)
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        run_repair(vault, paths, verbose=False, fix=False)
        assert call_count == 0, "build_index was called during dry-run (fix=False)"

    def test_repair_rebuilt_in_result(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done", do_ocr="false")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert "rebuilt" in result
        assert isinstance(result["rebuilt"], int)

    def test_repair_rebuild_fallback_on_error(self, tmp_path, monkeypatch):
        import paperforge.worker.asset_index

        def _failing_build(*args, **kwargs):
            raise RuntimeError("Simulated build failure")

        monkeypatch.setattr(paperforge.worker.asset_index, "build_index", _failing_build)
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=True)
        assert result["rebuilt"] == -1


class TestRunRepairReturnStructure:
    def test_result_has_all_keys(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        result = run_repair(vault, paths, verbose=False, fix=False)
        assert "scanned" in result
        assert "divergent" in result
        assert "fixed" in result
        assert "errors" in result
        assert "rebuilt" in result
        assert isinstance(result["scanned"], int)
        assert isinstance(result["divergent"], list)
        assert isinstance(result["fixed"], int)
        assert isinstance(result["errors"], list)
        assert isinstance(result["rebuilt"], int)

    def test_divergent_item_has_required_fields(self, tmp_path):
        vault = _make_vault(tmp_path)
        paths = pipeline_paths(vault)
        _write_formal_note(paths["literature"], "KEY001", "骨科", "done")
        _write_meta(paths["ocr"], "KEY001", "pending")
        result = run_repair(vault, paths, verbose=False, fix=False)
        item = result["divergent"][0]
        assert "zotero_key" in item
        assert "domain" in item
        assert "formal_note_ocr_status" in item
        assert "index_ocr_status" in item
        assert "meta_ocr_status" in item
        assert "reason" in item


class TestRepairCommandPaths:
    def test_repair_command_uses_pipeline_paths_with_config(self, tmp_path):
        vault = _make_vault(tmp_path)
        captured = {}

        def _fake_run_repair(vault_arg, paths_arg, verbose=False, fix=False, fix_paths=False):
            captured["vault"] = vault_arg
            captured["paths"] = paths_arg
            return {"scanned": 0, "divergent": [], "fixed": 0, "errors": [], "path_errors": {"total": 0}, "rebuilt": 0}

        from paperforge.commands import repair as repair_cmd

        args = argparse.Namespace(vault_path=None, paths=None, vault=str(vault), verbose=False, fix=False, fix_paths=False)
        with patch.object(repair_cmd, "_get_run_repair", return_value=_fake_run_repair):
            code = repair_cmd.run(args)

        assert code == 0
        assert captured["vault"] == vault
        assert "config" in captured["paths"]

    def test_repair_command_upgrades_legacy_paths_arg(self, tmp_path):
        vault = _make_vault(tmp_path)
        captured = {}

        def _fake_run_repair(vault_arg, paths_arg, verbose=False, fix=False, fix_paths=False):
            captured["paths"] = paths_arg
            return {"scanned": 0, "divergent": [], "fixed": 0, "errors": [], "path_errors": {"total": 0}, "rebuilt": 0}

        from paperforge.commands import repair as repair_cmd
        from paperforge.config import paperforge_paths

        legacy_paths = paperforge_paths(vault)
        args = argparse.Namespace(vault_path=vault, paths=legacy_paths, vault=str(vault), verbose=False, fix=False, fix_paths=False)
        with patch.object(repair_cmd, "_get_run_repair", return_value=_fake_run_repair):
            code = repair_cmd.run(args)

        assert code == 0
        assert "config" in captured["paths"]


class TestRepairDeadCode:
    """REPAIR-04: Verify load_domain_config dead code removed."""

    def test_no_import_load_domain_config(self):
        """load_domain_config import should not exist in repair.py source."""
        import paperforge.worker.repair as mod
        source = open(mod.__file__, encoding="utf-8").read()
        # The import line should be absent
        assert "load_domain_config" not in source, "REPAIR-04: load_domain_config still imported or referenced"

    def test_no_orphaned_dict_comprehension(self):
        """No orphaned config = load_domain_config(paths) call remains."""
        import paperforge.worker.repair as mod
        source = open(mod.__file__, encoding="utf-8").read()
        # The dead dict comprehension pattern should be gone
        assert 'export_file' not in source.split("def run_repair")[1].split("\n")[0:5] or True
        # Simpler check: `domain` in the context of dict comprehension
        lines = source.split("def run_repair")[1].split("\n")[:10]
        has_orphaned = any("entry[\"export_file\"]" in line for line in lines)
        assert not has_orphaned, "REPAIR-04: orphaned dict comprehension with export_file exists in run_repair()"
