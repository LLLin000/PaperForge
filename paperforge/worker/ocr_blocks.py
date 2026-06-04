from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_raw_blocks_for_page(paper_id: str, page: int, result: dict) -> list[dict[str, Any]]:
    pruned = result.get("prunedResult", {})
    width = pruned.get("width", 0)
    height = pruned.get("height", 0)
    blocks = pruned.get("parsing_res_list", [])
    rows = []
    for i, block in enumerate(blocks):
        rows.append({
            "paper_id": paper_id,
            "page": page,
            "block_id": block.get("block_id", f"p{page}_b{i}"),
            "raw_label": block.get("block_label", "unknown"),
            "raw_order": block.get("block_order", i),
            "bbox": block.get("block_bbox", [0, 0, 0, 0]),
            "text": block.get("block_content", "") or "",
            "page_width": width,
            "page_height": height,
            "source": "ocr_raw",
        })
    return rows


def build_raw_blocks_for_result_lines(paper_id: str, all_results: list[dict]) -> list[dict[str, Any]]:
    rows = []
    page_num = 0
    for payload in all_results:
        for res in payload.get("layoutParsingResults", []):
            page_num += 1
            rows.extend(build_raw_blocks_for_page(paper_id, page_num, res))
    return rows


def write_raw_blocks_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
