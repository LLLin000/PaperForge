from __future__ import annotations

import json
from pathlib import Path


FIXTURE_ROOT = Path("tests/fixtures/ocr_synthetic")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_synthetic_fixtures_load() -> None:
    for path in FIXTURE_ROOT.glob("*.jsonl"):
        blocks = _load_jsonl(path)
        assert blocks
        assert all("block_id" in b and "role" in b and "bbox" in b for b in blocks)


def test_synthetic_fixture_runs_core_downstream_modules() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_tables import build_table_inventory
    from paperforge.worker.ocr_render import render_fulltext_markdown
    from paperforge.worker.ocr_health import build_ocr_health

    blocks = _load_jsonl(FIXTURE_ROOT / "figure_table_tail_structured.jsonl")
    figure_inventory = build_figure_inventory(blocks)
    table_inventory = build_table_inventory(blocks)
    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={"title": {"value": "Synthetic OCR Paper"}, "authors": {"value": ["A. Author"]}},
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
        page_count=max(int(b.get("page", 1)) for b in blocks),
    )
    health = build_ocr_health(
        page_count=3,
        raw_blocks_count=len(blocks),
        structured_blocks=blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )
    assert "Synthetic OCR Paper" in markdown
    assert health["blocks_count"] == len(blocks)
