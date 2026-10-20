"""Research records are JSONL records, not paper-metadata search hits (#353)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

from tests.conftest import canonical_test_config


def cli(vault, *args):
    env = {**os.environ, "PYTHON_KEYRING_BACKEND": "keyring.backends.fail.Keyring"}
    proc = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), "reading-log", *args, "--json"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_immediate_record_search_without_memory_database(tmp_path):
    canonical_test_config(tmp_path)
    rc, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Straße 研究发现", "--usage", "Bridge-marker")
    assert rc == 0, saved
    record_id = saved["data"]["id"]
    cli(tmp_path, "--write", "PAPER001", "--excerpt", "unrelated observation")
    rc, found = cli(tmp_path, "--search", " STRASSE\u3000bridge-MARKER ")
    assert rc == 0, found
    assert found["data"]["count"] == 1
    hit = found["data"]["matches"][0]
    assert (hit["id"], hit["excerpt"], hit["usage"]) == (record_id, "Straße 研究发现", "Bridge-marker")
    assert hit["matched_fields"] == ["excerpt", "usage"]
    assert hit["record_status"] == "active"
    assert found["data"]["freshness"] == {"authority": "jsonl", "mode": "read_on_query"}
    assert cli(tmp_path, "--search", "研究发现")[1]["data"]["matches"][0]["id"] == record_id


def test_corrections_are_immediate_history_not_replacement_quotes(tmp_path):
    canonical_test_config(tmp_path)
    _, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Wrong quote marker")
    record_id = saved["data"]["id"]
    rc, rejected = cli(tmp_path, "--correct", record_id, "--paper", "OTHER001", "--correction", "Do not use")
    assert rc == 1 and rejected["ok"] is False
    assert cli(tmp_path, "--search", "Wrong")[1]["data"]["matches"][0]["record_status"] == "active"
    rc, correction = cli(tmp_path, "--correct", record_id, "--paper", "PAPER001",
                         "--correction", "The direction was reversed", "--reason", "Rechecked PDF")
    assert rc == 0, correction
    assert cli(tmp_path, "--search", "Wrong")[1]["data"]["matches"] == []
    hit = cli(tmp_path, "--search", "Wrong", "--include-history")[1]["data"]["matches"][0]
    assert hit["record_status"] == "corrected"
    assert hit["corrections"][0]["id"] == correction["data"]["jsonl_id"]
    assert hit["corrections"][0]["reason"] == "Rechecked PDF"
    assert cli(tmp_path, "--search", "direction")[1]["data"]["matches"] == []
    assert cli(tmp_path, "--correct", "rln_missing", "--correction", "bad")[0] == 1


def source_vault(vault):
    import pymupdf
    from paperforge.worker.asset_index import get_index_path

    canonical_test_config(vault, system_dir="CustomSystem")
    pdf = vault / "Sources" / "paper.pdf"
    pdf.parent.mkdir()
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "First physical page")
        doc.new_page().insert_text((72, 72), "Exact bridge observation on second page")
        doc.save(pdf)
    index = get_index_path(vault)
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({"items": [
        {"zotero_key": "PAPER001", "pdf_path": "[[Sources/paper.pdf]]", "has_pdf": True},
        {"zotero_key": "OTHER001", "pdf_path": "[[Sources/other.pdf]]", "has_pdf": True},
    ]}), encoding="utf-8")
    return pdf


def test_hash_bound_physical_page_verification_and_changed_source(tmp_path):
    pdf = source_vault(tmp_path)
    source = {"path": "Sources/paper.pdf", "physical_page": 2, "printed_page": "249",
              "basis": "exact_text", "anchor": "Exact bridge observation on second page"}
    rc, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", source["anchor"],
                    "--source-json", json.dumps(source))
    assert rc == 0, saved
    record_id = saved["data"]["id"]
    hit = cli(tmp_path, "--search", "bridge")[1]["data"]["matches"][0]
    assert hit["provenance"]["status"] == "matched"
    assert hit["provenance"]["basis"] == "exact_text"
    assert hit["source"]["physical_page"] == 2 and hit["source"]["printed_page"] == "249"
    assert hit["provenance"]["evidence"]["occurrences"] == 1
    rc, opened = cli(tmp_path, "--source-check", record_id, "--paper", "PAPER001")
    assert rc == 0 and opened["data"]["path"] == "Sources/paper.pdf"
    assert opened["data"]["physical_page"] == 2
    pdf.write_bytes(pdf.read_bytes() + b"\n%changed")
    hit = cli(tmp_path, "--search", "bridge")[1]["data"]["matches"][0]
    assert hit["provenance"]["status"] == "changed"
    assert cli(tmp_path, "--source-check", record_id)[0] == 1


def test_manual_confirmation_does_not_survive_excerpt_change(tmp_path):
    from paperforge.memory.permanent import get_reading_log_path

    source_vault(tmp_path)
    source = {"path": "Sources/paper.pdf", "physical_page": 2, "basis": "user_confirmed"}
    rc, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Manual observation",
                    "--source-json", json.dumps(source))
    assert rc == 0, saved
    hit = cli(tmp_path, "--search", "Manual")[1]["data"]["matches"][0]
    assert hit["provenance"]["status"] == "confirmed"
    assert hit["provenance"]["basis"] == "user_confirmed"
    # Simulate a stale imported legacy row in this disposable vault, not a product rewrite.
    log = get_reading_log_path(tmp_path)
    row = json.loads(log.read_text(encoding="utf-8"))
    row["excerpt"] = "Modified observation"
    log.write_text(json.dumps(row) + "\n", encoding="utf-8")
    hit = cli(tmp_path, "--search", "Modified")[1]["data"]["matches"][0]
    assert hit["provenance"]["status"] == "changed"
    assert cli(tmp_path, "--source-check", saved["data"]["id"])[0] == 1


def test_record_boundaries_and_incomplete_reads_fail_closed(tmp_path):
    from paperforge.memory.permanent import get_correction_log_path, get_reading_log_path

    canonical_test_config(tmp_path, system_dir="CustomSystem")
    _, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", "literal .* marker", "--context", "contexttoken")
    record_id = saved["data"]["id"]
    assert cli(tmp_path, "--search", ".*")[1]["data"]["matches"][0]["id"] == record_id
    assert cli(tmp_path, "--search", "marker contexttoken")[1]["data"]["count"] == 1
    assert cli(tmp_path, "--search", "marker", "--paper", "OTHER001")[1]["data"]["count"] == 0
    for args in [("--search", "  "), ("--search", "marker", "--limit", "0"),
                 ("--search", "marker", "--limit", "101")]:
        rc, result = cli(tmp_path, *args)
        assert rc == 1 and result["ok"] is False
    original = get_reading_log_path(tmp_path).read_bytes()
    correction_path = get_correction_log_path(tmp_path)
    correction_path.write_text("{malformed\n", encoding="utf-8")
    rc, result = cli(tmp_path, "--search", "marker")
    assert rc == 1 and "Incomplete" in result["error"]["message"]
    assert get_reading_log_path(tmp_path).read_bytes() == original


def test_source_rejects_untrusted_paths_and_pages_but_preserves_unknowns(tmp_path):
    source_vault(tmp_path)
    for source in [
        {"path": "../outside.pdf", "physical_page": 1},
        {"path": "file:///Sources/paper.pdf", "physical_page": 1},
        {"path": "https://example.invalid/paper.pdf", "physical_page": 1},
        {"path": "C:/Sources/paper.pdf", "physical_page": 1},
        {"path": "Sources/other.pdf", "physical_page": 1},
        {"path": "Sources/paper.pdf", "physical_page": 0},
        {"path": "Sources/paper.pdf", "physical_page": 3},
    ]:
        rc, result = cli(tmp_path, "--write", "PAPER001", "--excerpt", "refused",
                         "--source-json", json.dumps(source))
        assert rc == 1 and result["data"]["written"] is False, source
    _, unknown = cli(tmp_path, "--write", "PAPER001", "--excerpt", "unknown marker")
    hit = cli(tmp_path, "--search", "unknown")[1]["data"]["matches"][0]
    assert hit["provenance"] == {"status": "unknown", "basis": "none"}
    assert cli(tmp_path, "--source-check", unknown["data"]["id"])[0] == 1
    source = {"path": "Sources/paper.pdf", "physical_page": 2, "basis": "exact_text", "anchor": "No such quote"}
    _, mismatch = cli(tmp_path, "--write", "PAPER001", "--excerpt", "No such quote",
                       "--source-json", json.dumps(source))
    hit = cli(tmp_path, "--search", "No such quote")[1]["data"]["matches"][0]
    assert hit["provenance"]["status"] == "mismatch"
    assert cli(tmp_path, "--source-check", mismatch["data"]["id"])[0] == 1


def test_search_orders_instants_limits_results_and_preserves_legacy_verified(tmp_path):
    from paperforge.memory.permanent import get_reading_log_path

    canonical_test_config(tmp_path)
    path = get_reading_log_path(tmp_path)
    path.parent.mkdir(parents=True)
    rows = [
        {"id": "older", "paper_id": "PAPER001", "created_at": "2026-10-19T14:00:00+08:00", "excerpt": "marker", "verified": True},
        {"id": "newer-b", "paper_id": "PAPER001", "created_at": "2026-10-19T07:00:00Z", "excerpt": "marker"},
        {"id": "newer-a", "paper_id": "PAPER001", "created_at": "2026-10-19T07:00:00+00:00", "excerpt": "marker"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    hits = cli(tmp_path, "--search", "marker", "--limit", "2")[1]["data"]["matches"]
    assert [hit["id"] for hit in hits] == ["newer-a", "newer-b"]
    legacy = next(hit for hit in cli(tmp_path, "--search", "marker")[1]["data"]["matches"] if hit["id"] == "older")
    assert legacy["id"] == "older" and legacy["verified"] is True


def test_lookup_export_share_search_instant_order_and_malformed_correction(tmp_path):
    from paperforge.memory.permanent import get_correction_log_path, get_reading_log_path
    canonical_test_config(tmp_path)
    path = get_reading_log_path(tmp_path)
    path.parent.mkdir(parents=True)
    rows = [
        {"id": "older", "paper_id": "PAPER001", "created_at": "2026-10-19T14:00:00+08:00", "excerpt": "shared marker"},
        {"id": "newer-b", "paper_id": "PAPER001", "created_at": "2026-10-19T07:00:00Z", "excerpt": "shared marker"},
        {"id": "newer-a", "paper_id": "PAPER001", "created_at": "2026-10-19T07:00:00+00:00", "excerpt": "shared marker"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    looked = cli(tmp_path, "--lookup", "PAPER001")[1]["data"]["entries"]
    assert [entry["id"] for entry in looked] == ["newer-a", "newer-b", "older"]
    exported = cli(tmp_path)[1]["data"]["notes"]
    assert [note["id"] for note in exported] == ["newer-a", "newer-b", "older"]
    hits = cli(tmp_path, "--search", "shared marker")[1]["data"]["matches"]
    assert [hit["id"] for hit in hits] == ["newer-a", "newer-b", "older"]
    get_correction_log_path(tmp_path).write_text("{malformed\n", encoding="utf-8")
    rc, result = cli(tmp_path, "--lookup", "PAPER001")
    assert rc == 1 and "Incomplete" in result["error"]["message"]

def test_lookup_export_render_share_status_history_and_provenance(tmp_path):
    source_vault(tmp_path)
    source = {"path": "Sources/paper.pdf", "physical_page": 1, "printed_page": None}
    rc, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Lookup shared marker",
                    "--context", "ctx", "--source-json", json.dumps(source))
    assert rc == 0, saved
    record_id = saved["data"]["id"]
    rc, fixed = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Lookup shared marker replacement")
    assert rc == 0, fixed
    assert cli(tmp_path, "--correct", record_id, "--correction", "Replacement quote")[0] == 0
    full = next(hit for hit in cli(tmp_path, "--search", "Lookup", "--include-history")[1]["data"]["matches"] if hit["id"] == record_id)
    assert full["record_status"] == "corrected" and len(full["corrections"]) == 1
    assert full["source"]["printed_page"] == ""
    rc, looked = cli(tmp_path, "--lookup", "PAPER001")
    assert rc == 0
    entry = next(e for e in looked["data"]["entries"] if e["id"] == record_id)
    assert entry["record_status"] == "corrected" and entry["context"] == "ctx"
    assert entry["provenance"] == full["provenance"] and entry["corrections"] == full["corrections"]
    rc, exported = cli(tmp_path)
    assert rc == 0
    row = next(n for n in exported["data"]["notes"] if n["id"] == record_id)
    assert row["record_status"] == "corrected" and row["provenance"] == full["provenance"]
    assert cli(tmp_path, "--correct", fixed["data"]["id"], "--correction", "x", "--paper", "OTHER001")[0] == 1
    rc, strict = cli(tmp_path, "--correct", "rln_missing", "--correction", "x")
    assert rc == 1 and strict["error"]["code"] == "VALIDATION_ERROR"


def test_malformed_record_reads_and_missing_pdf_stay_unavailable(tmp_path):
    from paperforge.memory.permanent import get_correction_log_path
    pdf = source_vault(tmp_path)
    source = {"path": "Sources/paper.pdf", "physical_page": 2,
              "basis": "exact_text", "anchor": "Exact bridge observation on second page"}
    rc, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", source["anchor"],
                    "--source-json", json.dumps(source))
    assert rc == 0, saved
    record_id = saved["data"]["id"]
    get_correction_log_path(tmp_path).write_text("{malformed\n", encoding="utf-8")
    rc, result = cli(tmp_path, "--lookup", "PAPER001")
    assert rc == 1 and "Incomplete" in result["error"]["message"]
    get_correction_log_path(tmp_path).write_text("", encoding="utf-8")
    pdf.unlink()
    hit = cli(tmp_path, "--search", "bridge")[1]["data"]["matches"][0]
    assert (hit["provenance"]["status"], hit["provenance"]["basis"]) == ("unavailable", "exact_text")
    assert cli(tmp_path, "--source-check", record_id)[0] == 1


def test_memory_rebuild_preserves_ids_corrections_and_new_source(tmp_path):
    from paperforge.memory.permanent import get_correction_log_path, get_reading_log_path
    source_vault(tmp_path)
    rc, first = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Rebuild marker one")
    assert rc == 0, first
    rc, second = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Rebuild marker two",
                    "--source-json", json.dumps({"path": "Sources/paper.pdf", "physical_page": 1}))
    assert rc == 0, second
    assert cli(tmp_path, "--correct", first["data"]["id"], "--correction", "fix")[0] == 0
    before_log = get_reading_log_path(tmp_path).read_bytes()
    before_corr = get_correction_log_path(tmp_path).read_bytes()
    proc = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(tmp_path), "memory", "build", "--json"],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHON_KEYRING_BACKEND": "keyring.backends.fail.Keyring"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert get_reading_log_path(tmp_path).read_bytes() == before_log
    assert get_correction_log_path(tmp_path).read_bytes() == before_corr
    assert cli(tmp_path, "--search", "Rebuild marker two")[1]["data"]["matches"][0]["source"]["path"] == "Sources/paper.pdf"


def test_multiple_matching_records_return_each_stable_id(tmp_path):
    canonical_test_config(tmp_path)
    _, first = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Shared cohort marker alpha")
    _, second = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Shared cohort marker beta")
    found = cli(tmp_path, "--search", "Shared cohort marker")[1]["data"]
    assert found["count"] == 2
    assert {hit["id"] for hit in found["matches"]} == {first["data"]["id"], second["data"]["id"]}


def test_paper_context_projects_live_records_and_fail_closed_on_malformed_authority(tmp_path):
    from paperforge.memory.permanent import get_correction_log_path

    source_vault(tmp_path)
    rc, saved = cli(tmp_path, "--write", "PAPER001", "--excerpt", "Context live marker",
                    "--source-json", json.dumps({"path": "Sources/paper.pdf", "physical_page": 1}))
    assert rc == 0, saved
    record_id = saved["data"]["id"]
    assert cli(tmp_path, "--correct", record_id, "--correction", "Direction fix")[0] == 0
    proc = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(tmp_path), "memory", "build", "--json"],
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHON_KEYRING_BACKEND": "keyring.backends.fail.Keyring"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    def paper_context(*args):
        proc = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(tmp_path), "paper-context", *args, "--json"],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHON_KEYRING_BACKEND": "keyring.backends.fail.Keyring"},
        )
        channel = proc.stdout if proc.stdout.strip() else proc.stderr
        assert channel.strip(), (proc.returncode, proc.stdout, proc.stderr)
        return proc.returncode, json.loads(channel)

    rc, result = paper_context("PAPER001")
    assert rc == 0, result
    assert result["ok"] is True
    note = next(n for n in result["data"]["prior_notes"] if n["id"] == record_id)
    assert note["record_status"] == "corrected" and "provenance" in note
    assert result["data"]["corrections"] and result["data"]["corrections"][0]["correction"] == "Direction fix"

    get_correction_log_path(tmp_path).write_text("{malformed\n", encoding="utf-8")
    rc, result = paper_context("PAPER001")
    assert rc == 1 and result["ok"] is False
    assert "Incomplete" in result["error"]["message"]
