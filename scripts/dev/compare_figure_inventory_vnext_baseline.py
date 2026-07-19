from __future__ import annotations

import json
from pathlib import Path

from paperforge.worker.ocr_figures import build_figure_inventory


def compare_vnext_inventory_baseline(fixture_root: Path) -> dict[str, object]:
    structured_path = fixture_root / "structure" / "blocks.structured.jsonl"
    blocks = [json.loads(line) for line in structured_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    inventory = build_figure_inventory(blocks)
    return {
        "pipeline_mode": inventory.get("pipeline_mode"),
        "matched_ids": [m.get("figure_id") for m in inventory.get("matched_figures", [])],
        "match_count": len(inventory.get("matched_figures", [])),
    }
