"""Unit coverage for the Phase B quality-gate scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.dev.layout_figcaption_audit import bucket, crop_box, stratify
from scripts.dev.layout_regression_triage import _tags

REPO = Path(__file__).resolve().parents[1]


def test_figcaption_buckets_and_crop_box() -> None:
    assert bucket(0.03) == "2-5%"
    assert bucket(0.0501) == "5-15%"
    assert bucket(0.16) == ">15%"
    assert crop_box([100.0, 200.0, 300.0, 260.0], [120.0, 400.0, 500.0, 800.0], 1000.0, 1000.0) == [
        80.0,
        180.0,
        520.0,
        820.0,
    ]


def _report(pairs: list[dict]) -> dict:
    return {
        "papers": [
            {
                "key": "PAPER",
                "metrics": {"figure_caption": {"matched": len(pairs), "suspicious": pairs}},
                "plan": {
                    "pages": [
                        {
                            "page": 1,
                            "width": 1000,
                            "height": 1000,
                            "regions": [
                                {"region_id": "r0", "kind": "column", "members": [pair["caption"] for pair in pairs]},
                            ],
                        }
                    ]
                },
            }
        ]
    }


def test_figcaption_stratify_groups_and_sorts() -> None:
    result = stratify(
        _report(
            [
                {"page": 1, "caption": "c1", "asset": "a1", "caption_bbox": [0, 100, 50, 120], "asset_bbox": [0, 400, 50, 500]},
                {"page": 1, "caption": "c2", "asset": "a2", "caption_bbox": [0, 100, 50, 120], "asset_bbox": [0, 140, 50, 180]},
            ]
        )
    )
    assert result["total"] == 2
    assert result["buckets"] == {"2-5%": 1, "5-15%": 0, ">15%": 1}
    assert result["entries"][0]["distance_ratio"] > result["entries"][1]["distance_ratio"]


def test_triage_tags_name_the_structural_context() -> None:
    regions = [
        {"kind": "container", "y_top": 300.0, "y_bottom": 500.0},
    ]
    tags = _tags("a", "b", (0, 100, 50, 120), (0, 600, 50, 640), "a", "B", regions, {"a": "column", "b": "margin"})
    assert "panel_label" in tags  # the one-letter label is on the pair
    assert "margin_block" in tags
    assert "column_switch" in tags
    assert "container_between" in tags


def test_triage_tags_clean_pair() -> None:
    tags = _tags("a", "b", (0, 100, 50, 120), (0, 140, 50, 160), "text", "more", [], {"a": "column", "b": "column"})
    assert tags == []


def test_figcaption_cli_writes_json(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            _report(
                [
                    {"page": 1, "caption": "c1", "asset": "a1", "caption_bbox": [0, 100, 50, 120], "asset_bbox": [0, 400, 50, 500]},
                ]
            )
        ),
        encoding="utf-8",
    )
    out = tmp_path / "figcap.json"
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts/dev/layout_figcaption_audit.py"), "--report", str(report), "--out", str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["total"] == 1 and payload["entries"][0]["bucket"] == ">15%"
