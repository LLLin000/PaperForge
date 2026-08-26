from __future__ import annotations

import json
from pathlib import Path

from paperforge.render_audit import audit_paper


def _write_fixture(root: Path, *, mismatch: bool = False, dangling: bool = False) -> Path:
    key = "TESTFIG1"
    paper = root / key
    structure = paper / "structure"
    figures = paper / "render" / "figures"
    tables = paper / "render" / "tables"
    assets = paper / "assets" / "figures"
    structure.mkdir(parents=True)
    figures.mkdir(parents=True)
    tables.mkdir(parents=True)
    assets.mkdir(parents=True)
    (structure / "blocks.structured.jsonl").write_text('{"block_id": "asset-1"}\n', encoding="utf-8")
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {
                        "figure_id": "figure_001",
                        "figure_number": 1,
                        "page": 2,
                        "matched_assets": [{"block_id": "asset-1", "page": 2}],
                    }
                ],
                "unmatched_captions": [],
            }
        ),
        encoding="utf-8",
    )
    (structure / "table_inventory.json").write_text(
        json.dumps(
            {
                "tables": [
                    {
                        "table_id": "table_001",
                        "table_number": 1,
                        "page": 3,
                        "matched_assets": [{"block_id": "table-1", "page": 3}],
                    }
                ],
                "held_tables": [],
                "unmatched_captions": [],
            }
        ),
        encoding="utf-8",
    )
    (assets / "figure_001.jpg").write_bytes(b"fixture-image")
    header = "5" if mismatch else "1"
    legend = "2" if mismatch else "1"
    image = "missing.jpg" if dangling else "../../assets/figures/figure_001.jpg"
    (figures / "figure_001.md").write_text(
        f"# Figure {header}\n\n![]( {image})\n\n## Legend\nFig. {legend} fixture\n\n*Page 2*\n",
        encoding="utf-8",
    )
    (tables / "table_001.md").write_text(
        "# Table 1\n\n## Legend\nTable 1 fixture\n\n*Page 3*\n",
        encoding="utf-8",
    )
    return root


def test_audit_clean_fixture_writes_snapshot_and_report(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr")

    result = audit_paper(ocr_root, "TESTFIG1")

    assert result["state"] == "CLEAN"
    assert result["summary"]["issues_found"] == 0
    assert result["input_snapshot"]["figure_inventory_hash"]
    assert result["input_snapshot"]["render_hash"]
    report = ocr_root / "TESTFIG1" / "render" / "render.consistency.json"
    assert report.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["state"] == "CLEAN"


def test_audit_reports_caption_mismatch_and_dangling_asset(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr", mismatch=True, dangling=True)

    result = audit_paper(ocr_root, "TESTFIG1", write_report=False)
    issue_types = {issue["type"] for issue in result["issues"]}
    assert result["state"] == "DEGRADED"
    assert "render_caption_mismatch" in issue_types
    assert "render_dangling_asset_reference" in issue_types
    mismatch_issue = next(issue for issue in result["issues"] if issue["type"] == "render_caption_mismatch")
    assert mismatch_issue["diagnosis"] == "canonical_identity_ambiguous"
    assert mismatch_issue["domain"] == "inventory_layer"



def test_audit_reports_conflicting_duplicate_canonical_rows(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr")
    inventory = ocr_root / "TESTFIG1" / "structure" / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    duplicate = json.loads(json.dumps(data["matched_figures"][0]))
    duplicate["matched_assets"] = [{"block_id": "asset-2", "page": 2, "bbox": [1, 2, 3, 4]}]
    data["matched_figures"].append(duplicate)
    inventory.write_text(json.dumps(data), encoding="utf-8")

    result = audit_paper(ocr_root, "TESTFIG1", write_report=False)

    issue = next(issue for issue in result["issues"] if issue["type"] == "inventory_duplicate_entry")
    assert issue["domain"] == "inventory_layer"
    assert issue["diagnosis"] == "inventory_identity_ambiguous"
    assert issue["evidence"]["canonical_object_id"] == "figure_001"
    assert issue["evidence"]["count"] == 2
    assert issue["evidence"]["duplicate_class"] == "DUPLICATE_CONFLICTING"
    assert len(issue["evidence"]["row_digests"]) == 2


def test_audit_classifies_identical_duplicate_canonical_rows(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr")
    inventory = ocr_root / "TESTFIG1" / "structure" / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["matched_figures"].append(json.loads(json.dumps(data["matched_figures"][0])))
    inventory.write_text(json.dumps(data), encoding="utf-8")

    result = audit_paper(ocr_root, "TESTFIG1", write_report=False)

    issue = next(issue for issue in result["issues"] if issue["type"] == "inventory_duplicate_entry")
    assert issue["evidence"]["duplicate_class"] == "DUPLICATE_IDENTICAL"


def test_audit_reports_cross_canonical_asset_claim_conflict(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr")
    inventory = ocr_root / "TESTFIG1" / "structure" / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    second = json.loads(json.dumps(data["matched_figures"][0]))
    second["figure_id"] = "figure_002"
    second["figure_number"] = 2
    data["matched_figures"].append(second)
    inventory.write_text(json.dumps(data), encoding="utf-8")

    result = audit_paper(ocr_root, "TESTFIG1", write_report=False)

    issue = next(issue for issue in result["issues"] if issue["type"] == "inventory_asset_claim_conflict")
    assert issue["domain"] == "inventory_layer"
    assert issue["evidence"]["owners"] == ["figure_001", "figure_002"]

def test_missing_figure_image_is_upstream_caption_without_asset(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr")
    figure = ocr_root / "TESTFIG1" / "render" / "figures" / "figure_001.md"
    figure.write_text("# Figure 1\n\n## Legend\nFig. 1 fixture\n\n*Page 2*\n", encoding="utf-8")
    inventory = ocr_root / "TESTFIG1" / "structure" / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["matched_figures"][0]["matched_assets"] = []
    inventory.write_text(json.dumps(data), encoding="utf-8")

    result = audit_paper(ocr_root, "TESTFIG1", write_report=False)

    assert {issue["type"] for issue in result["issues"]} == {"caption_without_asset"}


def test_audit_does_not_modify_source_or_inventory(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr")
    inventory = ocr_root / "TESTFIG1" / "structure" / "figure_inventory.json"
    before = inventory.read_bytes()

    audit_paper(ocr_root, "TESTFIG1")

    assert inventory.read_bytes() == before


def test_audit_projects_existing_materialization_provenance(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path / "ocr", dangling=True)
    report_path = ocr_root / "TESTFIG1" / "render" / "materialization.provenance.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "objects": [
                    {
                        "object_id": "figure_001",
                        "kind": "figure",
                        "status": "failed",
                        "stage": "pdf_open",
                        "reason": "pdf_not_found",
                        "pdf_input": "missing",
                        "asset_path": "assets/figures/figure_001.jpg",
                        "render_path": "render/figures/figure_001.md",
                        "attempts": [],
                    }
                ],
                "summary": {"objects": 1, "reason": {"pdf_not_found": 1}},
            }
        ),
        encoding="utf-8",
    )

    result = audit_paper(ocr_root, "TESTFIG1", write_report=False)
    issue = next(issue for issue in result["issues"] if issue["type"] == "render_dangling_asset_reference")

    assert result["materialization_provenance"]["state"] == "available"
    assert issue["evidence"]["materialization"]["reason"] == "pdf_not_found"
