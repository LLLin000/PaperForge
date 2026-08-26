from __future__ import annotations

import json
from pathlib import Path

from paperforge.figure_reconciliation import build_reconciliation_report
from paperforge.render_audit import audit_paper


def _write_fixture(tmp_path: Path) -> Path:
    ocr_root = tmp_path / "ocr"
    paper = ocr_root / "TESTREC1"
    structure = paper / "structure"
    render = paper / "render" / "figures"
    source_images = paper / "images" / "blocks"
    structure.mkdir(parents=True)
    render.mkdir(parents=True)
    source_images.mkdir(parents=True)

    (structure / "blocks.structured.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"page": 2, "block_id": 1, "role": "figure_caption", "text": "Fig. 1 Existing"},
                {"page": 4, "block_id": 2, "role": "figure_caption", "text": "Fig. 2 Missing canonical"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {
                        "figure_id": "figure_001",
                        "figure_number": 1,
                        "figure_namespace": "main",
                        "page": 2,
                        "matched_assets": [{"block_id": "asset-1", "page": 2, "bbox": [10, 10, 110, 110]}],
                        "settlement_type": "same_page",
                        "confidence": 0.95,
                    },
                    {
                        "figure_id": "figure_reserved_005",
                        "figure_number": None,
                        "figure_namespace": "main",
                        "page": 3,
                        "matched_assets": [],
                        "settlement_type": "cross_page_reservation",
                        "confidence": 0.6,
                    },
                ],
                "unmatched_captions": [],
            }
        ),
        encoding="utf-8",
    )
    (structure / "table_inventory.json").write_text(json.dumps({"tables": []}), encoding="utf-8")
    (source_images / "page_003_figure_10_10_110_110.jpg").write_bytes(b"candidate" * 1024)
    (render / "figure_001.md").write_text(
        "# Figure 1\n\n## Legend\nFig. 1 Existing\n\n*Page 2*\n", encoding="utf-8"
    )
    return ocr_root


def test_reconciliation_separates_exact_proposal_and_blocked(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path)
    paper = ocr_root / "TESTREC1"
    assets = paper / "assets" / "figures"
    assets.mkdir(parents=True)
    (assets / "figure_001.jpg").write_bytes(b"image")
    (paper / "render" / "figures" / "figure_001.md").write_text(
        "# Figure 1\n\n![](../../assets/figures/figure_001.jpg)\n\n## Legend\nFig. 1 Existing\n\n*Page 2*\n",
        encoding="utf-8",
    )
    audit = audit_paper(ocr_root, "TESTREC1", write_report=False)

    report = build_reconciliation_report(ocr_root, "TESTREC1", audit)

    assert report["formal_figure_assessment"]["supported_formal_figure_labels"] == ["1", "2"]
    assert report["summary"] == {
        "asset_claim_conflicts": 0,
        "supported_formal_figures": 2,
        "canonical_formal_figures": 1,
        "rendered_formal_figures": 1,
        "inventory_conflicts": 0,
        "exact_repairs": 0,
        "proposals": 1,
        "blocked": 1,
    }
    assert report["proposals"][0]["label"] == "2"
    assert report["blocked"][0]["reason"] == "reservation_artifact_conflict"


def test_reconciliation_blocks_duplicate_canonical_identity(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path)
    inventory = ocr_root / "TESTREC1" / "structure" / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    duplicate = json.loads(json.dumps(data["matched_figures"][0]))
    duplicate["matched_assets"] = [{"block_id": "asset-2", "page": 2, "bbox": [20, 20, 120, 120]}]
    data["matched_figures"].append(duplicate)
    inventory.write_text(json.dumps(data), encoding="utf-8")

    audit = audit_paper(ocr_root, "TESTREC1", write_report=False)
    report = build_reconciliation_report(ocr_root, "TESTREC1", audit)

    assert report["summary"]["inventory_conflicts"] == 1
    assert not report["exact_repairs"]
    assert "1" not in report["formal_figure_assessment"]["missing_canonical_labels"]
    conflict = next(
        item for item in report["blocked"] if item["reason"] == "inventory_duplicate_entry"
    )
    assert conflict["canonical_object_id"] == "figure_001"
    assert conflict["duplicate_class"] == "DUPLICATE_CONFLICTING"


def test_reconciliation_keeps_existing_canonical_render_gap_exact(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path)
    paper = ocr_root / "TESTREC1"
    (paper / "render" / "figures" / "figure_001.md").write_text(
        "# Figure 1\n\n## Legend\nFig. 1 Existing\n\n*Page 2*\n", encoding="utf-8"
    )
    report = build_reconciliation_report(ocr_root, "TESTREC1", audit_report={"issues": []})

    assert report["exact_repairs"][0]["canonical_object_id"] == "figure_001"
    assert report["exact_repairs"][0]["repair_scope"] == "render_only"


def test_dry_run_exact_repair_only_reports_preconditions(tmp_path: Path) -> None:
    from paperforge.figure_reconciliation import dry_run_exact_repairs, write_reconciliation_report

    ocr_root = _write_fixture(tmp_path)
    paper = ocr_root / "TESTREC1"
    (paper / "render" / "figures" / "figure_001.md").write_text(
        "# Figure 1\n\n## Legend\nFig. 1 Existing\n\n*Page 2*\n",
        encoding="utf-8",
    )
    audit_paper(ocr_root, "TESTREC1", write_report=True)
    write_reconciliation_report(ocr_root, "TESTREC1")

    dry_run = dry_run_exact_repairs(ocr_root, "TESTREC1")

    assert dry_run["mode"] == "dry_run"
    assert dry_run["input_snapshot_match"] is True
    assert dry_run["audit_snapshot_match"] is True
    assert dry_run["summary"]["exact_repair_candidates"] == 1
    assert dry_run["summary"]["needs_fresh_provenance"] == 1
    assert dry_run["summary"]["ready"] == 0


def test_stage_reconciliation_filters_ambiguous_inventory_from_r_materialization(
    tmp_path: Path, monkeypatch
) -> None:
    from paperforge.figure_reconciliation import stage_reconciliation

    ocr_root = tmp_path / "ocr"
    paper = ocr_root / "TESTSTAGE1"
    structure = paper / "structure"
    (paper / "render" / "figures").mkdir(parents=True)
    (paper / "render" / "tables").mkdir(parents=True)
    (paper / "assets" / "figures").mkdir(parents=True)
    structure.mkdir(parents=True)
    (paper / "meta.json").write_text(json.dumps({"source_pdf": ""}), encoding="utf-8")
    (structure / "blocks.structured.jsonl").write_text(
        "\n".join(
            json.dumps({"page": page, "page_width": 600, "page_height": 800})
            for page in (1, 2)
        )
        + "\n",
        encoding="utf-8",
    )
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {
                        "figure_id": "figure_001",
                        "figure_number": 1,
                        "page": 1,
                        "matched_assets": [{"page": 1, "block_id": "a1", "bbox": [10, 10, 50, 50]}],
                    },
                    {
                        "figure_id": "figure_001",
                        "figure_number": 1,
                        "page": 1,
                        "matched_assets": [{"page": 1, "block_id": "a2", "bbox": [60, 60, 100, 100]}],
                    },
                    {
                        "figure_id": "figure_002",
                        "figure_number": 2,
                        "page": 2,
                        "matched_assets": [{"page": 2, "block_id": "b1", "bbox": [10, 10, 50, 50]}],
                    },
                ],
                "unmatched_captions": [],
                "unresolved_clusters": [],
            }
        ),
        encoding="utf-8",
    )
    (structure / "table_inventory.json").write_text(
        json.dumps({"tables": [{"table_id": "table_001"}], "unmatched_assets": []}),
        encoding="utf-8",
    )
    audit_paper(ocr_root, "TESTSTAGE1", write_report=True)

    captured: dict[str, object] = {}

    def fake_materializer(pdf_path, figure_inventory, table_inventory, asset_root, render_root, **kwargs):
        captured["figure_ids"] = [
            row.get("figure_id") for row in figure_inventory.get("matched_figures", [])
        ]
        captured["table_inventory"] = table_inventory
        from PIL import Image

        for row in figure_inventory.get("matched_figures", []):
            figure_id = row["figure_id"]
            image_path = asset_root / "figures" / f"{figure_id}.jpg"
            markdown_path = render_root / "figures" / f"{figure_id}.md"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (2, 2), color="white").save(image_path)
            markdown_path.write_text(
                f"# Figure {row.get('figure_number')}\n\n![](../../assets/figures/{figure_id}.jpg)\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(
        "paperforge.worker.ocr_objects.extract_and_write_objects",
        fake_materializer,
    )
    result = stage_reconciliation(
        ocr_root,
        "TESTSTAGE1",
        staging_root=tmp_path / "staging",
    )

    assert captured["figure_ids"] == ["figure_002"]
    assert captured["table_inventory"] == {"tables": [], "unmatched_assets": []}
    assert result["summary"]["r_prepared_staged"] == 1
