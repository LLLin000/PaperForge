from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_roles import assign_block_role


def build_structured_blocks(raw_blocks: list[dict]) -> list[dict]:
    rows = []
    for block in raw_blocks:
        mapped = {
            "block_label": block.get("raw_label", "unknown"),
            "block_content": block.get("text", ""),
            "block_bbox": block.get("bbox", [0, 0, 0, 0]),
        }
        role = assign_block_role(
            mapped,
            page_blocks=[],
            page_width=block.get("page_width", 0),
            page_height=block.get("page_height", 0),
        )
        render_default = role.role not in {"noise", "unknown_structural"}
        index_default = True
        if role.role in {"noise", "page_header", "page_footer", "frontmatter_noise"}:
            render_default = False
        if role.role in {"noise", "frontmatter_noise"}:
            index_default = False
        row = {
            "paper_id": block["paper_id"],
            "page": block["page"],
            "block_id": block["block_id"],
            "raw_label": block.get("raw_label", "unknown"),
            "raw_order": block.get("raw_order", 0),
            "bbox": block.get("bbox", [0, 0, 0, 0]),
            "text": block.get("text", ""),
            "role": role.role,
            "role_confidence": role.confidence,
            "evidence": role.evidence,
            "render_default": render_default,
            "index_default": index_default,
        }
        rows.append(row)
    return rows


def write_structured_blocks_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_raw_blocks_for_page(paper_id: str, page: int, result: dict) -> list[dict[str, Any]]:
    pruned = result.get("prunedResult", {})
    width = pruned.get("width", 0)
    height = pruned.get("height", 0)
    blocks = pruned.get("parsing_res_list", [])
    rows = []
    for i, block in enumerate(blocks):
        rows.append(
            {
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
            }
        )
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
