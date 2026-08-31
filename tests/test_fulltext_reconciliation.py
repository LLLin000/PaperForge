from __future__ import annotations

import json
from pathlib import Path

from paperforge.fulltext_reconciliation import fulltext_reconcile


def test_duplicate_canonical_figure_ids_block_fulltext_patches(tmp_path: Path) -> None:
    paper = tmp_path / "ocr" / "TESTFULLTEXT1"
    structure = paper / "structure"
    (paper / "render" / "figures").mkdir(parents=True)
    structure.mkdir(parents=True)
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {"figure_id": "figure_001", "figure_number": 1},
                    {"figure_id": "figure_001", "figure_number": 1},
                    {"figure_id": "figure_002", "figure_number": 2},
                ]
            }
        ),
        encoding="utf-8",
    )
    (paper / "fulltext.md").write_text(
        "![[render/figures/figure_001.md]]\n", encoding="utf-8"
    )

    result = fulltext_reconcile(tmp_path / "ocr", "TESTFULLTEXT1")

    assert result["canonical_ids"] == ["figure_001", "figure_002"]
    assert result["canonical_identity_conflicts"] == {"figure_001": 2}
    assert result["mutation_blocked"] is True
    assert result["patches"] == []
    issue = next(
        issue
        for issue in result["issues"]
        if issue["type"] == "fulltext_canonical_identity_ambiguous"
    )
    assert issue["classification"] == "F0_CANONICAL_DUPLICATE"
    assert issue["recommended_action"] == "BLOCK"
    assert result["summary"]["canonical_ambiguous"] == 1


def test_unique_canonical_ids_keep_existing_fulltext_patch_behavior(tmp_path: Path) -> None:
    paper = tmp_path / "ocr" / "TESTFULLTEXT2"
    structure = paper / "structure"
    structure.mkdir(parents=True)
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {"matched_figures": [{"figure_id": "figure_001", "figure_number": 1}]}
        ),
        encoding="utf-8",
    )
    (paper / "fulltext.md").write_text("", encoding="utf-8")

    result = fulltext_reconcile(tmp_path / "ocr", "TESTFULLTEXT2")

    assert result["mutation_blocked"] is False
    assert result["patches"][0]["op"] == "INSERT"
    assert result["patches"][0]["object_id"] == "figure_001"


def test_fulltext_source_unavailable_blocks_all_patches(tmp_path: Path) -> None:
    paper = tmp_path / "ocr" / "TESTFULLTEXT3"
    structure = paper / "structure"
    structure.mkdir(parents=True)
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {"matched_figures": [{"figure_id": "figure_001", "figure_number": 1}]}
        ),
        encoding="utf-8",
    )

    result = fulltext_reconcile(tmp_path / "ocr", "TESTFULLTEXT3")

    assert result["fulltext_available"] is False
    assert result["mutation_blocked"] is True
    assert result["patches"] == []
    assert result["issues"][0]["type"] == "fulltext_source_unavailable"


def test_fulltext_ignores_malformed_inventory_collection(tmp_path: Path) -> None:
    paper = tmp_path / "ocr" / "TESTFULLTEXT4"
    structure = paper / "structure"
    structure.mkdir(parents=True)
    (structure / "figure_inventory.json").write_text(
        json.dumps({"matched_figures": {"not": "a-list"}}), encoding="utf-8"
    )
    (paper / "fulltext.md").write_text("", encoding="utf-8")

    result = fulltext_reconcile(tmp_path / "ocr", "TESTFULLTEXT4")

    assert result["canonical_ids"] == []
    assert result["mutation_blocked"] is False
    assert result["patches"] == []


def test_fulltext_ignores_malformed_reserved_mapping_rows(tmp_path: Path) -> None:
    paper = tmp_path / "ocr" / "TESTFULLTEXT5"
    structure = paper / "structure"
    structure.mkdir(parents=True)
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {"matched_figures": [{"figure_id": "figure_001", "figure_number": 1}]}
        ),
        encoding="utf-8",
    )
    (paper / "fulltext.md").write_text(
        "![[render/figures/figure_reserved_001.md]]\n", encoding="utf-8"
    )
    (paper / "render").mkdir()
    (paper / "render" / "reconciliation.proposals.json").write_text(
        json.dumps({"blocked": ["malformed-row"]}), encoding="utf-8"
    )

    result = fulltext_reconcile(tmp_path / "ocr", "TESTFULLTEXT5")

    issue = next(issue for issue in result["issues"] if issue["type"] == "fulltext_wrong_target")
    assert issue["classification"] == "F2_AMBIGUOUS"
    assert result["patches"]
    assert all(patch["op"] == "INSERT" for patch in result["patches"])
    assert all(patch["object_id"] == "figure_001" for patch in result["patches"])
