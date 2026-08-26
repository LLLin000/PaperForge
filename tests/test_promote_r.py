from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperforge.promote_r import _plan_hash, _snapshot_hash, promote_r
from paperforge.render_audit import audit_paper


def _write_r_fixture(tmp_path: Path, *, duplicate: bool = False) -> tuple[Path, Path, Path]:
    ocr_root = tmp_path / "ocr"
    paper_key = "TESTRPROMO1"
    paper = ocr_root / paper_key
    structure = paper / "structure"
    (paper / "render" / "figures").mkdir(parents=True)
    (paper / "assets" / "figures").mkdir(parents=True)
    structure.mkdir(parents=True)
    (structure / "blocks.structured.jsonl").write_text("", encoding="utf-8")
    rows = [
        {
            "figure_id": "figure_001",
            "figure_number": 1,
            "figure_namespace": "main",
            "page": 1,
            "matched_assets": [{"page": 1, "block_id": "asset-1", "bbox": [10, 10, 50, 50]}],
        }
    ]
    if duplicate:
        rows.append(
            {
                "figure_id": "figure_001",
                "figure_number": 1,
                "figure_namespace": "main",
                "page": 1,
                "matched_assets": [{"page": 1, "block_id": "asset-2", "bbox": [60, 60, 100, 100]}],
            }
        )
    (structure / "figure_inventory.json").write_text(
        json.dumps({"matched_figures": rows, "unmatched_captions": []}), encoding="utf-8"
    )
    (structure / "table_inventory.json").write_text(json.dumps({"tables": []}), encoding="utf-8")
    return ocr_root, paper, structure


def _write_r_manifest(paper: Path, staging_root: Path) -> Path:
    from PIL import Image

    staged = staging_root / "TESTRPROMO1"
    image_path = staged / "assets" / "figures" / "figure_001.jpg"
    markdown_path = staged / "render" / "figures" / "figure_001.md"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (2, 3), color="white").save(image_path)
    markdown_path.write_text(
        "# Figure 1\n\n![](../../assets/figures/figure_001.jpg)\n", encoding="utf-8"
    )

    import hashlib

    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    plan: dict[str, Any] = {
        "object_id": "figure_001",
        "canonical_identity": {
            "figure_id": "figure_001",
            "figure_namespace": "main",
            "figure_number": 1,
            "page": 1,
        },
        "input_snapshot_hash": _snapshot_hash(paper),
        "ordered_asset_refs": [{"page": 1, "block_id": "asset-1", "bbox": [10, 10, 50, 50]}],
        "staged_asset": "assets/figures/figure_001.jpg",
        "staged_markdown": "render/figures/figure_001.md",
        "production_asset": "assets/figures/figure_001.jpg",
        "production_markdown": "render/figures/figure_001.md",
    }
    plan["plan_hash"] = _plan_hash(plan)
    plan["staged_verification"] = {
        "status": "passed",
        "image": {"sha256": sha256(image_path), "width": 2, "height": 3},
        "markdown_sha256": sha256(markdown_path),
    }
    provenance = {
        "schema_version": 1,
        "objects": [
            {
                "object_id": "figure_001",
                "kind": "figure",
                "status": "materialized",
                "stage": "materialize",
                "reason": "success",
                "asset_path": "assets/figures/figure_001.jpg",
                "render_path": "render/figures/figure_001.md",
            }
        ],
    }
    provenance_path = staged / "render" / "materialization.provenance.json"
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "kind": "R",
        "paper_key": "TESTRPROMO1",
        "input_snapshot_hash": plan["input_snapshot_hash"],
        "staging_provenance": "render/materialization.provenance.json",
        "plans": [plan],
    }
    manifest_path = staged / "r-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return staged


def test_promote_r_copies_verified_artifacts_and_refreshes_audit(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    before_inventory = (paper / "structure" / "figure_inventory.json").read_bytes()
    staging = _write_r_manifest(paper, tmp_path / "staging")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is True
    assert result["promoted"] == ["figure_001"]
    assert (paper / "assets/figures/figure_001.jpg").is_file()
    assert (paper / "render/figures/figure_001.md").is_file()
    assert (paper / "render/materialization.provenance.json").is_file()
    assert (paper / "structure/figure_inventory.json").read_bytes() == before_inventory
    assert result["audit_1"]["target_delta"]["figure_001"]["after"] == []



def test_promote_r_second_run_is_artifact_noop(tmp_path: Path, monkeypatch) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    assert promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)["ok"] is True

    import paperforge.promote_r as promoter_module

    def fail_if_copy_called(*args, **kwargs):
        raise AssertionError("second promotion must not copy identical artifacts")

    monkeypatch.setattr(promoter_module, "_atomic_copy", fail_if_copy_called)
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is True
    assert result["promotion_states"] == {"figure_001": "already_promoted"}



def test_promote_r_rolls_back_after_mid_batch_write_failure(tmp_path: Path, monkeypatch) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    old_image = paper / "assets/figures/figure_001.jpg"
    old_markdown = paper / "render/figures/figure_001.md"
    old_image.write_bytes(b"old-image")
    old_markdown.write_text("old-markdown", encoding="utf-8")

    import paperforge.promote_r as promoter_module

    original_copy = promoter_module._atomic_copy
    calls = 0

    def fail_on_second_copy(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected-after-first-file")
        original_copy(source, destination)

    monkeypatch.setattr(promoter_module, "_atomic_copy", fail_on_second_copy)
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_WRITE_FAILED"
    assert result["rolled_back"] is True
    assert old_image.read_bytes() == b"old-image"
    assert old_markdown.read_text(encoding="utf-8") == "old-markdown"
def test_promote_r_refuses_stale_manifest_without_writes(tmp_path: Path) -> None:
    ocr_root, paper, structure = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    inventory = structure / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["marker"] = "changed-after-staging"
    inventory.write_text(json.dumps(data), encoding="utf-8")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "STALE_R_MANIFEST"
    assert not (paper / "assets/figures/figure_001.jpg").exists()


def test_promote_r_blocks_duplicate_live_identity(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path, duplicate=True)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_GATE_FAILED"
    assert "inventory_duplicate_entry" in result["objects"][0]["gates"]
    assert not (paper / "assets/figures/figure_001.jpg").exists()


def test_render_promote_r_parser_contract(tmp_path: Path) -> None:
    from paperforge.cli import build_parser

    args = build_parser().parse_args(
        [
            "--vault",
            str(tmp_path),
            "render",
            "promote-r",
            "TESTRPROMO1",
            "figure_001",
            "--json",
        ]
    )

    assert args.render_subcommand == "promote-r"
    assert args.key == "TESTRPROMO1"
    assert args.object_ids == ["figure_001"]
    assert args.json is True
