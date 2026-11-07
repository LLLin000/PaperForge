from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from paperforge.worker.layout.evaluate import evaluate_plan
from paperforge.worker.layout.model import (
    SEVERITY_HOLD,
    Conflict,
    LayoutPlan,
    PagePlan,
    Region,
)


def _blocks() -> list[dict]:
    return [
        {"page": 1, "block_id": "a", "bbox": [0, 10, 20, 20], "page_width": 100, "page_height": 100, "text": "a"},
        {"page": 1, "block_id": "b", "bbox": [0, 30, 20, 40], "page_width": 100, "page_height": 100, "text": "b"},
    ]


def test_metrics_count_coverage_inversions_and_conflicts() -> None:
    regions = [
        Region("r1", 1, "column", 0, 100, 0, 100, ("p1:0000", "p1:0001"), None, 1.0),
        Region("r2", 1, "container", 0, 100, 0, 100, ("p1:0000",), "r1", 1.0),
    ]
    conflict = Conflict("c1", 1, "ambiguous_column", SEVERITY_HOLD, (), "test")
    plan = LayoutPlan(pages=[PagePlan(1, 100, 100, regions, ["p1:0001", "p1:0000"], ["p1:0001"], conflicts=[conflict])])
    metrics = evaluate_plan(plan, _blocks())
    assert metrics["coverage"] == {"covered": 3, "unique": 1, "duplicated": 1, "missing": 0, "margin": 0}
    assert metrics["pair_inversions"] == [{"page": 1, "before": "p1:0001", "after": "p1:0000"}]
    assert metrics["holds"] == {"count": 1, "ratio": 0.5}
    assert metrics["conflicts"] == {"by_kind": {"ambiguous_column": 1}, "by_severity": {"hold": 1}, "total": 1}


def test_report_smoke_with_tiny_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    paper = vault / "PAPER"
    canonical = paper / "canonical"
    raw = paper / "raw"
    canonical.mkdir(parents=True)
    raw.mkdir()
    entries = [
        {"paper_id": "PAPER", "page": page, "block_id": bid, "raw_label": "text", "raw_order": index,
         "bbox": bbox, "page_width": 100, "page_height": 100, "text": text}
        for page, bid, index, bbox, text in (
            (1, "a", 0, [5, 10, 90, 20], "Introduction"),
            (1, "b", 1, [5, 30, 90, 40], "Some body text."),
            (2, "c", 2, [5, 10, 90, 20], "More body text."),
        )
    ]
    (canonical / "blocks.raw.jsonl").write_text("\n".join(json.dumps(row) for row in entries) + "\n", encoding="utf-8")
    (raw / "source_metadata.json").write_text("{}", encoding="utf-8")
    output = tmp_path / "report.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "dev" / "layout_plan_report.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--vault", str(vault), "--keys", "PAPER", "--out", str(output)],
        check=True, capture_output=True, text=True,
    )
    assert "| Key | Pages | Blocks | Regions |" in completed.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert set(report) == {"papers"}
    assert len(report["papers"]) == 1
    metrics = report["papers"][0]["metrics"]
    assert {"pages", "blocks", "coverage", "pair_inversions", "holds", "conflicts", "figure_caption"} <= set(metrics)


def test_margin_blocks_are_reported_without_counting_as_body_inversions() -> None:
    from paperforge.worker.layout.model import REGION_MARGIN

    refs_blocks = [
        {"page": 1, "block_id": "head", "bbox": [10, 5, 400, 20], "page_width": 500, "page_height": 1000, "role": "body_paragraph", "text": "RUNNING HEAD"},
        {"page": 1, "block_id": "a", "bbox": [10, 300, 400, 340], "page_width": 500, "page_height": 1000, "role": "body_paragraph", "text": "Body."},
    ]
    regions = [
        Region("m", 1, REGION_MARGIN, 0, 500, 0, 30, ("p1:0000",), None, 0.8),
        Region("c", 1, "column", 0, 500, 30, 1000, ("p1:0001",), None, 0.9),
    ]
    plan = LayoutPlan(pages=[PagePlan(1, 500, 1000, regions, ["p1:0001", "p1:0000"], [], [])])
    metrics = evaluate_plan(plan, refs_blocks)
    assert metrics["coverage"]["margin"] == 1
    assert metrics["margin_blocks"] == 1
    assert metrics["pair_inversions"] == []
