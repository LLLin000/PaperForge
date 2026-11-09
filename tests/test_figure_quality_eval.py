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


def test_label_schema():
    expected = set(module.LABEL_FIELDS)
    sample = {f: None for f in module.LABEL_FIELDS}
    assert set(sample) == expected


def test_diff_results():
    prev = {"cases": [{"key": "A", "passed": False}, {"key": "B", "passed": True}]}
    curr = {"cases": [{"key": "A", "passed": True}, {"key": "B", "passed": False}]}
    d = module.diff_results(prev, curr)
    assert d["fixed"] == ["A"]
    assert d["regressed"] == ["B"]
