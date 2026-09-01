from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

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
        "production_precondition": {
            "asset": {
                "exists": (paper / "assets/figures/figure_001.jpg").is_file(),
                "sha256": (
                    sha256(paper / "assets/figures/figure_001.jpg")
                    if (paper / "assets/figures/figure_001.jpg").is_file()
                    else None
                ),
            },
            "markdown": {
                "exists": (paper / "render/figures/figure_001.md").is_file(),
                "sha256": (
                    sha256(paper / "render/figures/figure_001.md")
                    if (paper / "render/figures/figure_001.md").is_file()
                    else None
                ),
            },
            "provenance": {
                "exists": (paper / "render/materialization.provenance.json").is_file(),
                "sha256": (
                    sha256(paper / "render/materialization.provenance.json")
                    if (paper / "render/materialization.provenance.json").is_file()
                    else None
                ),
            },
        },
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
        "schema_version": 2,
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


def test_promote_r_reports_post_commit_refresh_failure_without_rollback(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")

    import paperforge.promote_r as promoter_module

    original_audit = promoter_module.audit_paper

    def fail_report_refresh(*args, **kwargs):
        if kwargs.get("write_report"):
            raise OSError("report refresh unavailable")
        return original_audit(*args, **kwargs)

    monkeypatch.setattr(promoter_module, "audit_paper", fail_report_refresh)
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is True
    assert result["committed"] is True
    assert result["report_refresh"] == "failed"
    assert result["report_refresh_error"] == "OSError: report refresh unavailable"
    assert result["audit_1"]["after_state"] == "FAILED"
    assert (paper / "assets/figures/figure_001.jpg").is_file()
    assert not (paper / ".paperforge-r-promotion.json").exists()


def test_promote_r_returns_committed_when_cleanup_is_pending(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")

    import paperforge.promote_r as promoter_module

    original_cleanup = promoter_module._cleanup_backup_dir
    calls = 0

    def fail_once(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("cleanup unavailable")
        original_cleanup(path)

    monkeypatch.setattr(promoter_module, "_cleanup_backup_dir", fail_once)
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    journal = paper / ".paperforge-r-promotion.json"
    assert result["ok"] is True
    assert result["committed"] is True
    assert result["cleanup"] == "pending"
    assert result["cleanup_error"] == "OSError: cleanup unavailable"
    assert json.loads(journal.read_text(encoding="utf-8"))["state"] == "committed"
    assert (
        paper / "assets/figures/figure_001.jpg"
    ).read_bytes() == (
        staging / "assets/figures/figure_001.jpg"
    ).read_bytes()

    second = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert second["ok"] is True
    assert second["promotion_states"] == {"figure_001": "already_promoted"}
    assert not journal.exists()



def test_promote_r_separates_report_write_from_failed_audit_state(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    staging = _write_r_manifest(paper, tmp_path / "staging")

    import paperforge.promote_r as promoter_module

    def failed_final_audit(*args, **kwargs):
        if kwargs.get("write_report"):
            return {"state": "FAILED", "issues": [{"type": "audit_failed"}]}
        return {"state": "CLEAN", "issues": [], "input_snapshot": {}}

    monkeypatch.setattr(promoter_module, "audit_paper", failed_final_audit)
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is True
    assert result["committed"] is True
    assert result["report_refresh"] == "written"
    assert result["report_audit_state"] == "FAILED"
    assert result["audit_1"]["after_state"] == "FAILED"
    assert (paper / "assets/figures/figure_001.jpg").is_file()


def test_promote_r_rejects_raw_destination_symlink_without_cleanup(
    tmp_path: Path,
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    target = paper / "render" / "figures" / "sentinel.md"
    target.write_bytes(b"keep")
    destination = paper / "render" / "figures" / "figure_001.md"
    try:
        destination.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    transaction_id = "c" * 32
    transaction_relative = f".paperforge-r-promotion/{transaction_id}"
    transaction_dir = paper / transaction_relative
    transaction_dir.mkdir(parents=True)
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "committed",
                "transaction_dir": transaction_relative,
                "snapshots": [
                    {
                        "existed": False,
                        "destination_relative": "render/figures/figure_001.md",
                        "backup_relative": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == (
        "promotion_recovery_failed:ValueError:promotion_journal_destination_path_unsafe"
    )
    assert target.read_bytes() == b"keep"
    assert destination.is_symlink()
    assert journal.is_file()
    assert transaction_dir.is_dir()


def test_promote_r_rejects_raw_backup_symlink_without_rollback(
    tmp_path: Path,
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    destination = paper / "render" / "figures" / "figure_001.md"
    destination.write_bytes(b"current")
    transaction_id = "d" * 32
    transaction_relative = f".paperforge-r-promotion/{transaction_id}"
    transaction_dir = paper / transaction_relative
    transaction_dir.mkdir(parents=True)
    real_backup = transaction_dir / "real.bak"
    real_backup.write_bytes(b"before")
    backup = transaction_dir / "0.bak"
    try:
        backup.symlink_to(real_backup)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "prepared",
                "transaction_dir": transaction_relative,
                "snapshots": [
                    {
                        "existed": True,
                        "destination_relative": "render/figures/figure_001.md",
                        "backup_relative": f"{transaction_relative}/0.bak",
                        "before": {
                            "exists": True,
                            "sha256": hashlib.sha256(b"before").hexdigest(),
                        },
                        "output": {
                            "exists": True,
                            "sha256": hashlib.sha256(b"current").hexdigest(),
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == (
        "promotion_recovery_failed:ValueError:promotion_journal_backup_path_unsafe"
    )
    assert destination.read_bytes() == b"current"
    assert backup.is_symlink()
    assert journal.is_file()


def test_promote_r_recovers_committed_journal_after_backup_cleanup(
    tmp_path: Path,
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    destination = paper / "render" / "figures" / "figure_001.md"
    destination.write_bytes(b"committed")
    transaction_id = "b" * 32
    transaction_relative = f".paperforge-r-promotion/{transaction_id}"
    transaction_dir = paper / transaction_relative
    transaction_dir.mkdir(parents=True)
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "committed",
                "transaction_dir": transaction_relative,
                "snapshots": [
                    {
                        "existed": True,
                        "destination_relative": "render/figures/figure_001.md",
                        "backup_relative": f"{transaction_relative}/0.bak",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "r_manifest_missing"
    assert destination.read_bytes() == b"committed"
    assert not journal.exists()
    assert not transaction_dir.exists()


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
    old_image = paper / "assets/figures/figure_001.jpg"
    old_markdown = paper / "render/figures/figure_001.md"
    old_image.write_bytes(b"old-image")
    old_markdown.write_text("old-markdown", encoding="utf-8")
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")

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




def test_promote_r_blocks_cross_canonical_asset_claim(tmp_path: Path) -> None:
    ocr_root, paper, structure = _write_r_fixture(tmp_path)
    inventory = structure / "figure_inventory.json"
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["matched_figures"].append(
        {
            "figure_id": "figure_002",
            "figure_number": 2,
            "figure_namespace": "main",
            "page": 1,
            "matched_assets": [{"page": 1, "block_id": "asset-1", "bbox": [10, 10, 50, 50]}],
        }
    )
    inventory.write_text(json.dumps(data), encoding="utf-8")
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert "asset_claim_conflict" in result["objects"][0]["gates"]
    assert not (paper / "assets/figures/figure_001.jpg").exists()


def test_promote_r_refuses_changed_destination_precondition(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    (paper / "assets/figures/figure_001.jpg").write_bytes(b"changed-destination")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_GATE_FAILED"
    assert "STALE_R_DESTINATION" in result["objects"][0]["gates"]
    assert (paper / "assets/figures/figure_001.jpg").read_bytes() == b"changed-destination"


def test_promote_r_postcondition_failure_rolls_back(tmp_path: Path, monkeypatch) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    import paperforge.promote_r as promoter_module

    snapshots = {
        "blocks_hash": "blocks",
        "figure_inventory_hash": "inventory",
        "table_inventory_hash": "tables",
    }
    calls = 0

    def fake_audit(root, key, *, write_report):
        nonlocal calls
        calls += 1
        if calls == 2:
            return {
                "state": "DEGRADED",
                "input_snapshot": snapshots,
            "issues": [{"type": "target_failure", "severity": "P1", "evidence": {"file": "figure_001.md"}}],
            }
        return {"state": "CLEAN", "input_snapshot": snapshots, "issues": []}

    monkeypatch.setattr(promoter_module, "audit_paper", fake_audit)
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_POSTVERIFY_FAILED"
    assert result["rolled_back"] is True
    assert not (paper / "assets/figures/figure_001.jpg").exists()
    assert not (paper / ".paperforge-r-promotion.json").exists()



def test_promote_r_refuses_failed_pre_audit(tmp_path: Path, monkeypatch) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    import paperforge.promote_r as promoter_module

    monkeypatch.setattr(
        promoter_module,
        "audit_paper",
        lambda *args, **kwargs: {
            "state": "FAILED",
            "issues": [{"type": "audit_execution_failure"}],
        },
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_PREAUDIT_FAILED"
    assert result["audit_0"]["state"] == "FAILED"
    assert result["production_write"] is False
    assert not (paper / "assets/figures/figure_001.jpg").exists()
    assert not (paper / ".paperforge-r-promotion.json").exists()


def test_promote_r_failed_post_audit_rolls_back_and_records_rollback_audit(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    import paperforge.promote_r as promoter_module

    calls = 0

    def fake_audit(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return {
                "state": "FAILED",
                "issues": [{"type": "audit_execution_failure"}],
            }
        return {"state": "CLEAN", "issues": [], "input_snapshot": {}}

    monkeypatch.setattr(promoter_module, "audit_paper", fake_audit)

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_POSTVERIFY_FAILED"
    assert result["post_audit_state"] == "FAILED"
    assert result["rollback_audit_state"] == "CLEAN"
    assert result["rolled_back"] is True
    assert not (paper / "assets/figures/figure_001.jpg").exists()
    assert not (paper / ".paperforge-r-promotion.json").exists()


def test_promote_r_recovery_refuses_external_destination_conflict(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    import paperforge.promote_r as promoter_module

    original_copy = promoter_module._atomic_copy
    calls = 0

    def interrupt_on_second_copy(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        original_copy(source, destination)

    monkeypatch.setattr(promoter_module, "_atomic_copy", interrupt_on_second_copy)
    with pytest.raises(KeyboardInterrupt):
        promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    image = paper / "assets/figures/figure_001.jpg"
    image.write_bytes(b"external-writer")
    monkeypatch.undo()

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert "promotion_recovery_conflict" in result["error"]
    assert image.read_bytes() == b"external-writer"
    assert (paper / ".paperforge-r-promotion.json").is_file()


def test_promote_r_blocks_duplicate_staging_provenance(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    provenance_path = staging / "render" / "materialization.provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["objects"].append(json.loads(json.dumps(provenance["objects"][0])))
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_GATE_FAILED"
    assert result["objects"][0]["gates"] == ["staging_provenance_unreadable"]
    assert not (paper / "assets/figures/figure_001.jpg").exists()


def test_promote_r_keeps_malformed_pending_journal(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "prepared",
                "transaction_dir": ".paperforge-r-promotion/" + ("a" * 32),
                "snapshots": [],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == (
        "promotion_recovery_failed:ValueError:promotion_journal_snapshots_invalid"
    )
    assert journal.is_file()

def test_promote_r_rejects_unsafe_object_id(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    manifest_path = staging / "r-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan = manifest["plans"][0]
    plan["object_id"] = "../outside"
    plan["canonical_identity"]["figure_id"] = "../outside"
    plan["staged_asset"] = "assets/figures/../outside.jpg"
    plan["staged_markdown"] = "render/figures/../outside.md"
    plan["production_asset"] = "assets/figures/../outside.jpg"
    plan["production_markdown"] = "render/figures/../outside.md"
    plan["plan_hash"] = _plan_hash(plan)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is False
    assert result["reason"] == "R_GATE_FAILED"
    assert "object_id_unsafe" in result["objects"][0]["gates"]
    assert not (paper / "outside.jpg").exists()


def test_promote_r_rejects_unsafe_transaction_directory_without_cleanup(
    tmp_path: Path,
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    sentinel = paper / "render" / "figures" / "sentinel.md"
    sentinel.write_bytes(b"keep")
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "committed",
                "transaction_dir": "render/figures",
                "snapshots": [],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == (
        "promotion_recovery_failed:ValueError:promotion_journal_transaction_path_invalid"
    )
    assert sentinel.read_bytes() == b"keep"
    assert journal.is_file()


def test_promote_r_rejects_unsafe_journal_destination_without_cleanup(
    tmp_path: Path,
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    sentinel = paper / "render" / "figures" / "sentinel.md"
    sentinel.write_bytes(b"keep")
    transaction_id = "a" * 32
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "committed",
                "transaction_dir": f".paperforge-r-promotion/{transaction_id}",
                "snapshots": [
                    {
                        "existed": False,
                        "destination_relative": "render/figures",
                        "backup_relative": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == (
        "promotion_recovery_failed:ValueError:promotion_journal_destination_path_invalid"
    )
    assert sentinel.read_bytes() == b"keep"
    assert journal.is_file()


def test_promote_r_rejects_unsupported_journal_schema(tmp_path: Path) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "committed",
                "transaction_dir": ".paperforge-r-promotion/" + ("a" * 32),
                "snapshots": [],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == "promotion_journal_schema_invalid"
    assert journal.is_file()


def test_promote_r_rejects_backup_outside_transaction_directory(
    tmp_path: Path,
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    sentinel = paper / "render" / "figures" / "sentinel.md"
    sentinel.write_bytes(b"keep")
    transaction_id = "a" * 32
    journal = paper / ".paperforge-r-promotion.json"
    journal.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "committed",
                "transaction_dir": f".paperforge-r-promotion/{transaction_id}",
                "snapshots": [
                    {
                        "existed": True,
                        "destination_relative": "render/figures/figure_001.md",
                        "backup_relative": "render/figures/0.bak",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=tmp_path / "missing")

    assert result["ok"] is False
    assert result["reason"] == "R_PROMOTION_RECOVERY_REQUIRED"
    assert result["error"] == (
        "promotion_recovery_failed:ValueError:promotion_journal_backup_path_invalid"
    )
    assert sentinel.read_bytes() == b"keep"
    assert journal.is_file()



def test_promote_r_recovers_persisted_journal_after_interruption(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    import paperforge.promote_r as promoter_module

    original_copy = promoter_module._atomic_copy
    calls = 0

    def interrupt_on_second_copy(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        original_copy(source, destination)

    monkeypatch.setattr(promoter_module, "_atomic_copy", interrupt_on_second_copy)
    with pytest.raises(KeyboardInterrupt):
        promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)
    assert (paper / ".paperforge-r-promotion.json").is_file()

    monkeypatch.undo()
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is True
    assert not (paper / ".paperforge-r-promotion.json").exists()
    assert (paper / "assets/figures/figure_001.jpg").is_file()


@pytest.mark.parametrize(
    "injection",
    ["image_temp_write", "markdown_temp_write", "before_image_rename", "after_image_rename"],
)
def test_promote_r_recovers_four_hard_kill_points(
    tmp_path: Path, monkeypatch, injection: str
) -> None:
    ocr_root, paper, _ = _write_r_fixture(tmp_path)
    audit_paper(ocr_root, "TESTRPROMO1", write_report=True)
    staging = _write_r_manifest(paper, tmp_path / "staging")
    import paperforge.promote_r as promoter_module

    original_copy2 = promoter_module.shutil.copy2
    original_replace = promoter_module.os.replace
    copy_calls = 0

    def injected_copy2(source: Path, destination: Path, *args, **kwargs):
        nonlocal copy_calls
        if destination.name.endswith(".tmp") and "figure_001" in destination.name:
            copy_calls += 1
            if (
                injection == "image_temp_write"
                or injection == "markdown_temp_write"
                and copy_calls == 2
            ):
                raise KeyboardInterrupt
        return original_copy2(source, destination, *args, **kwargs)

    def injected_replace(source: Path, destination: Path, *args, **kwargs):
        if destination.name == "figure_001.jpg" and source.name.endswith(".tmp"):
            if injection == "before_image_rename":
                raise KeyboardInterrupt
            result = original_replace(source, destination, *args, **kwargs)
            if injection == "after_image_rename":
                raise KeyboardInterrupt
            return result
        return original_replace(source, destination, *args, **kwargs)

    if injection in {"image_temp_write", "markdown_temp_write"}:
        monkeypatch.setattr(promoter_module.shutil, "copy2", injected_copy2)
    else:
        monkeypatch.setattr(promoter_module.os, "replace", injected_replace)

    with pytest.raises(KeyboardInterrupt):
        promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)
    assert (paper / ".paperforge-r-promotion.json").is_file()

    monkeypatch.undo()
    result = promote_r(ocr_root, "TESTRPROMO1", staging_root=staging)

    assert result["ok"] is True
    assert not (paper / ".paperforge-r-promotion.json").exists()
    assert (paper / "assets/figures/figure_001.jpg").is_file()
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

    all_args = build_parser().parse_args(
        ["--vault", str(tmp_path), "render", "promote-r", "TESTRPROMO1", "--all"]
    )
    assert all_args.object_ids == []
    assert all_args.all is True
