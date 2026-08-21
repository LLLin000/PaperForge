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
        "supported_formal_figures": 2,
        "canonical_formal_figures": 1,
        "rendered_formal_figures": 1,
        "exact_repairs": 0,
        "proposals": 1,
        "blocked": 1,
    }
    assert report["proposals"][0]["label"] == "2"
    assert report["blocked"][0]["reason"] == "reservation_artifact_conflict"


def test_reconciliation_keeps_existing_canonical_render_gap_exact(tmp_path: Path) -> None:
    ocr_root = _write_fixture(tmp_path)
    paper = ocr_root / "TESTREC1"
    (paper / "render" / "figures" / "figure_001.md").write_text(
        "# Figure 1\n\n## Legend\nFig. 1 Existing\n\n*Page 2*\n", encoding="utf-8"
    )
    report = build_reconciliation_report(ocr_root, "TESTREC1", audit_report={"issues": []})

    assert report["exact_repairs"][0]["canonical_object_id"] == "figure_001"
    assert report["exact_repairs"][0]["repair_scope"] == "render_only"
