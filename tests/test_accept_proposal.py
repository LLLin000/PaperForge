from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from PIL import Image

import paperforge.accept_proposal as accept_module
from paperforge.accept_proposal import _snapshot_hash, accept_proposal

PAPER_KEY = "TESTACCEPT1"
LABEL = "2"
MEMBER_REFS = [{"page": 3, "block_id": "asset-2", "bbox": [10, 20, 110, 120]}]


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    ocr_root = tmp_path / "ocr"
    paper = ocr_root / PAPER_KEY
    structure = paper / "structure"
    render_figures = paper / "render" / "figures"
    structure.mkdir(parents=True)
    render_figures.mkdir(parents=True)
    (paper / "assets" / "figures").mkdir(parents=True)
    (structure / "blocks.structured.jsonl").write_text("", encoding="utf-8")
    (structure / "table_inventory.json").write_text(json.dumps({"tables": []}), encoding="utf-8")
    (structure / "figure_inventory.json").write_text(
        json.dumps(
            {
                "matched_figures": [
                    {
                        "figure_id": "figure_reserved_002",
                        "figure_number": None,
                        "figure_namespace": "main",
                        "matched_assets": [],
                        "settlement_type": "cross_page_reservation",
                    }
                ],
                "unmatched_captions": [],
            }
        ),
        encoding="utf-8",
    )
    (paper / "fulltext.md").write_text("# Paper\n", encoding="utf-8")
    (paper / "render" / "fulltext.md").write_text("# Paper\n", encoding="utf-8")
    (paper / "render" / "reconciliation.proposals.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "summary": {"exact_repairs": 0, "proposals": 1, "blocked": 0},
                "exact_repairs": [],
                "proposals": [{"label": LABEL, "proposal_id": "figure_proposal_2"}],
                "blocked": [],
            }
        ),
        encoding="utf-8",
    )

    preview = (
        tmp_path
        / "paperforge-staging"
        / f"run_{PAPER_KEY}"
        / PAPER_KEY
        / "previews"
        / f"figure_{LABEL}"
    )
    staged_image = preview / "assets" / "figures" / f"figure_proposal_{LABEL}.jpg"
    staged_markdown = preview / "render" / "figures" / f"figure_proposal_{LABEL}.md"
    staged_image.parent.mkdir(parents=True)
    staged_markdown.parent.mkdir(parents=True)
    Image.new("RGB", (3, 4), color="white").save(staged_image)
    staged_markdown.write_text(
        "# Figure 2 (proposed)\n\n"
        "![](../../assets/figures/figure_proposal_2.jpg)\n",
        encoding="utf-8",
    )

    plan = {
        "schema_version": 1,
        "label": LABEL,
        "proposal_id": "figure_proposal_2",
        "decision": "structurally_unique_proposal",
        "page": 3,
        "member_refs": MEMBER_REFS,
        "caption_text": "Figure 2 Proposed",
        "input_snapshot_hash": _snapshot_hash(paper),
        "staged_jpg": "assets/figures/figure_proposal_2.jpg",
        "staged_md": "render/figures/figure_proposal_2.md",
    }
    plan_path = preview / "final-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return ocr_root, paper, plan_path


def test_accept_proposal_commits_atomically_and_refreshes_provenance(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, plan_path = _write_fixture(tmp_path)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    expected_plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = accept_proposal(ocr_root, PAPER_KEY, LABEL)

    assert result["ok"] is True
    assert result["committed"] is True
    assert result["cleanup"] == "done"
    assert result["report_refresh"] == "written"
    assert result["audit_1"]["after_state"] in {"CLEAN", "DEGRADED"}
    assert not (paper / ".paperforge-r-promotion.json").exists()

    inventory = json.loads(
        (paper / "structure" / "figure_inventory.json").read_text(encoding="utf-8")
    )
    accepted = next(row for row in inventory["matched_figures"] if row["figure_id"] == "figure_002")
    assert accepted["matched_assets"] == MEMBER_REFS
    assert any(row["figure_id"] == "figure_reserved_002" for row in inventory["matched_figures"])
    assert "../../assets/figures/figure_002.jpg" in (
        paper / "render" / "figures" / "figure_002.md"
    ).read_text(encoding="utf-8")

    provenance = json.loads(
        (paper / "render" / "materialization.provenance.json").read_text(encoding="utf-8")
    )
    record = next(item for item in provenance["objects"] if item["object_id"] == "figure_002")
    assert record["plan_hash"] == expected_plan_hash
    assert record["ordered_asset_refs"] == MEMBER_REFS
    assert record["output"]["width"] == 3
    assert record["output"]["height"] == 4

    reconciliation = json.loads(
        (paper / "render" / "reconciliation.proposals.json").read_text(encoding="utf-8")
    )
    assert reconciliation["proposals"] == []
    assert reconciliation["summary"]["proposals"] == 0
    assert (paper / "render" / "render.consistency.json").is_file()


def test_accept_proposal_requires_plan_snapshot(tmp_path: Path, monkeypatch) -> None:
    ocr_root, paper, plan_path = _write_fixture(tmp_path)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan.pop("input_snapshot_hash")
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    before_inventory = (paper / "structure" / "figure_inventory.json").read_bytes()

    result = accept_proposal(ocr_root, PAPER_KEY, LABEL)

    assert result == {
        "ok": False,
        "reason": "proposal_snapshot_missing",
        "paper_key": PAPER_KEY,
        "label": LABEL,
    }
    assert (paper / "structure" / "figure_inventory.json").read_bytes() == before_inventory
    assert not (paper / "assets" / "figures" / "figure_002.jpg").exists()


def test_accept_proposal_rolls_back_when_post_audit_fails(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, plan_path = _write_fixture(tmp_path)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    before_inventory = (paper / "structure" / "figure_inventory.json").read_bytes()
    before_reconciliation = (paper / "render" / "reconciliation.proposals.json").read_bytes()
    calls = 0
    original_audit = accept_module._promotion_audit

    def fail_post_audit(*args, **kwargs):
        nonlocal calls
        calls += 1
        if not kwargs.get("write_report") and calls == 2:
            return {"state": "FAILED", "issues": [{"type": "injected_failure"}]}
        return original_audit(*args, **kwargs)

    monkeypatch.setattr(accept_module, "_promotion_audit", fail_post_audit)

    result = accept_proposal(ocr_root, PAPER_KEY, LABEL)

    assert result["ok"] is False
    assert result["reason"] == "ACCEPT_PROPOSAL_POSTVERIFY_FAILED"
    assert result["rolled_back"] is True
    assert (paper / "structure" / "figure_inventory.json").read_bytes() == before_inventory
    assert (paper / "render" / "reconciliation.proposals.json").read_bytes() == before_reconciliation
    assert not (paper / "assets" / "figures" / "figure_002.jpg").exists()
    assert not (paper / "render" / "figures" / "figure_002.md").exists()
    assert not (paper / "render" / "materialization.provenance.json").exists()
    assert not (paper / ".paperforge-r-promotion.json").exists()
    assert plan_path.is_file()


def test_accept_proposal_returns_committed_when_cleanup_is_pending(
    tmp_path: Path, monkeypatch
) -> None:
    ocr_root, paper, _ = _write_fixture(tmp_path)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    original_cleanup = accept_module._cleanup_backup_dir
    calls = 0

    def fail_once(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("cleanup unavailable")
        original_cleanup(path)

    monkeypatch.setattr(accept_module, "_cleanup_backup_dir", fail_once)

    result = accept_proposal(ocr_root, PAPER_KEY, LABEL)

    journal = paper / ".paperforge-r-promotion.json"
    assert result["ok"] is True
    assert result["committed"] is True
    assert result["cleanup"] == "pending"
    assert result["cleanup_error"] == "OSError: cleanup unavailable"
    assert result["report_refresh"] == "written"
    assert json.loads(journal.read_text(encoding="utf-8"))["state"] == "committed"
    assert (paper / "assets" / "figures" / "figure_002.jpg").is_file()
