"""Tests for figure quality eval harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "figure_quality_eval",
    Path(__file__).resolve().parents[1] / "scripts/dev/figure_quality_eval.py",
)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)

ROOT = Path(__file__).resolve().parents[1]
SET_DIR = ROOT / "docs" / "evidence" / "figure-quality" / "sets"


def test_frozen_sets_counts_and_disjoint():
    smoke = json.loads((SET_DIR / "smoke.json").read_text())
    dev = json.loads((SET_DIR / "dev.json").read_text())
    reg = json.loads((SET_DIR / "regression.json").read_text())
    assert smoke["count"] == 10 and len(smoke["keys"]) == 10
    assert dev["count"] == 50 and len(dev["keys"]) == 50
    assert reg["count"] == 100 and len(reg["keys"]) == 100
    s, d, r = set(smoke["keys"]), set(dev["keys"]), set(reg["keys"])
    assert not (s & d) and not (s & r) and not (d & r)


def test_scoring_math():
    labels = [
        {"figure_id": "f1", "expected_owner": "a b", "current_assets": "a x", "reviewer": "r", "crop_ok": True, "delivery_ok": True, "caption_ok": True, "panels_ok": True},
        {"figure_id": "f2", "expected_owner": "c", "current_assets": "c", "reviewer": "r", "crop_ok": False, "delivery_ok": True, "caption_ok": True, "panels_ok": True},
    ]
    replay = {"figures": [
        {"figure_id": "f1", "matched_assets": [{"block_id": "a"}, {"block_id": "x"}]},
        {"figure_id": "f2", "matched_assets": [{"block_id": "c"}]},
    ]}
    sc = module.score_labels(labels, replay)
    assert sc["reviewed"] == 2
    assert sc["crop_failures"] == 1
    assoc = sc["association"]
    # f1: tp a, fp x; f2: tp c => tp2 fp1 fn1 (expected b missing)
    assert assoc["tp"] == 2
    assert assoc["fp"] == 1
    assert assoc["fn"] == 1


def test_unreviewed_filtering():
    labels = [
        {"figure_id": "f1", "reviewer": "", "crop_ok": False},
        {"figure_id": "f2", "reviewer": "unreviewed", "crop_ok": False},
        {"figure_id": "f3", "reviewer": "human", "crop_ok": False},
    ]
    rev = module.filter_reviewed(labels)
    assert len(rev) == 1 and rev[0]["figure_id"] == "f3"
    sc = module.score_labels(labels, {"figures": []})
    assert sc["reviewed"] == 1
    assert sc["unreviewed"] == 2


def test_ocr_to_pdf_bbox_conversion():
    bbox = [80, 113, 583, 357]
    out = module.ocr_to_pdf_bbox(bbox, 1191, 1582, 596, 791)
    assert [round(v) for v in out] == [40, 56, 292, 178]


def test_label_schema():
    expected = set(module.LABEL_FIELDS)
    sample = {f: None for f in module.LABEL_FIELDS}
    assert set(sample) == expected

def test_replay_inventory_takes_precedence(tmp_path):
    paper_dir = tmp_path / "paper"
    inventory_path = paper_dir / "structure" / "figure_inventory.json"
    inventory_path.parent.mkdir(parents=True)
    inventory_path.write_text(json.dumps({"unmatched_legends": [], "unmatched_assets": []}))
    replay_inventory = {
        "unmatched_legends": [{"page": 15, "block_id": 99, "text": "replayed caption"}],
        "unmatched_assets": [{"page": 14, "bbox": [1, 2, 3, 4]}],
    }
    selected = module._review_inventory(replay_inventory, paper_dir)
    assert selected is replay_inventory
    assert selected["unmatched_legends"][0]["text"] == "replayed caption"


def test_diff_results():
    prev = {"cases": [{"key": "A", "passed": False}, {"key": "B", "passed": True}]}
    curr = {"cases": [{"key": "A", "passed": True}, {"key": "B", "passed": False}]}
    d = module.diff_results(prev, curr)
    assert d["fixed"] == ["A"]
    assert d["regressed"] == ["B"]


def test_manual_findings_score_without_mutating_agent_labels():
    labels = [{"key": "28JLIHLS", "figure_id": "figure_002", "reviewer": "agent",
               "expected_owner": "0", "current_assets": "0", "crop_ok": True,
               "delivery_ok": True, "caption_ok": True, "panels_ok": True}]
    findings = [
        {"id": "crop", "key": "28JLIHLS", "status": "confirmed", "source": "user-manual",
         "figure": "figure_002", "crop_ok": False, "recorded_at": "2026-11-09"},
        {"id": "missing", "key": "28JLIHLS", "status": "confirmed", "source": "user-manual",
         "figure": "figure_009", "missing_figure": True, "expected_asset_blocks": [8],
         "actual_asset_blocks": [], "delivery_ok": False, "recorded_at": "2026-11-09"},
    ]
    original = json.dumps(labels)
    score = module.score_labels(labels, {"figures": []}, findings, "28JLIHLS")
    assert score["agent_scored"]["crop_failures"] == 0
    assert score["human_verified"]["crop_failures"] == 1
    assert score["human_verified"]["association"]["fn"] == 1
    assert score["human_verified"]["delivery_failures"] == 1
    assert json.dumps(labels) == original


def test_unknown_manual_values_do_not_become_pass():
    labels = [{"figure_id": "figure_002", "reviewer": "agent", "crop_ok": None}]
    finding = {"id": "unknown", "key": "K", "status": "confirmed", "source": "user-manual",
               "figure": "figure_002", "crop_ok": None, "recorded_at": "now"}
    score = module.score_labels(labels, {"figures": []}, [finding], "K")
    assert score["crop_failures"] == 0
    assert score["known"]["crop_ok"] == 0
def test_lifecycle_scoring_separates_human_and_excludes_stale_findings():
    labels = [{"key": "K", "figure_id": "f1", "reviewer": "agent", "expected_owner": "1",
               "crop_ok": True, "delivery_ok": True}]
    findings = [
        {"id": "confirmed", "key": "K", "status": "confirmed", "figure": "f1",
         "expected_asset_blocks": [1], "actual_asset_blocks": [1], "crop_ok": False,
         "delivery_ok": None, "panel_ok": None},
        {"id": "superseded", "key": "K", "status": "superseded", "figure": "old",
         "missing_figure": True, "expected_asset_blocks": [8], "crop_ok": False,
         "delivery_ok": False},
        {"id": "disputed", "key": "K", "status": "disputed", "figure": "unknown",
         "missing_figure": True, "expected_asset_blocks": None, "crop_ok": False,
         "delivery_ok": False},
    ]
    original = json.dumps(findings)
    score = module.score_labels(labels, {"figures": [
        {"figure_id": "f1", "matched_assets": [{"block_id": 1}]},
    ]}, findings, "K")
    assert score["agent_scored"]["crop_failures"] == 0
    assert score["human_verified"]["crop_failures"] == 1
    assert score["human_verified"]["delivery_failures"] == 0
    assert score["human_verified"]["association"]["fn"] == 0
    assert score["unknown"]["delivery_ok"] == 1
    assert score["superseded"] == score["disputed"] == 1
    assert score["lifecycle_counts"]["confirmed"] == 1
    assert json.dumps(findings) == original


def test_unknown_human_association_is_not_a_pass():
    finding = {"id": "unknown", "key": "K", "status": "confirmed", "figure": "f1",
               "expected_asset_blocks": None, "crop_ok": None, "delivery_ok": None}
    score = module.score_labels([], {"figures": []}, [finding], "K")
    assert score["unknown"]["expected_asset_blocks"] == 1
    assert score["human_verified"]["association"]["unknown_expected"] == 1
    assert score["human_verified"]["association"]["fn"] == 0

def test_manual_findings_lifecycle_preserves_source_records():
    path = ROOT / "docs" / "evidence" / "figure-quality" / "smoke" / "manual_findings.jsonl"
    findings = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    by_id = {finding["id"]: finding for finding in findings}
    original_ids = {
        "manual-3QYCST4E-figure_001B", "manual-28JLIHLS-figure_002",
        "manual-28JLIHLS-figure_005", "manual-28JLIHLS-figure_006",
        "manual-28JLIHLS-figure_009",
    }
    assert original_ids <= by_id.keys()
    assert all(by_id[finding_id]["recorded_at"] == "2026-11-09" for finding_id in original_ids)
    assert all({"status", "superseded_by", "reason", "resolved_at", "evidence_refs"} <= finding.keys()
               for finding in findings)
    assert {finding["status"] for finding in findings} <= {"confirmed", "superseded", "disputed"}
    assert by_id["manual-28JLIHLS-figure_005"]["status"] == "confirmed"
