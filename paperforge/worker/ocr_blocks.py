from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_roles import assign_block_role


def build_structured_blocks(raw_blocks: list[dict]) -> list[dict]:
    # Group raw blocks by page so assign_block_role can see page-local context
    by_page: dict[int, list[dict]] = {}
    for block in raw_blocks:
        page = block.get("page", 1)
        by_page.setdefault(page, []).append(block)

    total_pages = max(by_page.keys()) if by_page else 1  # noqa: F841 - reserved for future use

    # First pass: initial role assignment (no span profiles)
    rows: list[dict] = []
    for page in sorted(by_page.keys()):
        raw_page_blocks = by_page[page]
        page_as_role_input: list[dict] = []
        for raw_block in raw_page_blocks:
            page_as_role_input.append(
                {
                    "block_label": raw_block.get("raw_label", "unknown"),
                    "block_content": raw_block.get("text", ""),
                    "block_bbox": raw_block.get("bbox", [0, 0, 0, 0]),
                    "page": raw_block.get("page", 1),
                }
            )
        for i, block in enumerate(raw_page_blocks):
            role_input = page_as_role_input[i]
            role = assign_block_role(
                role_input,
                page_blocks=page_as_role_input,
                page_width=block.get("page_width", 0),
                page_height=block.get("page_height", 0),
            )
            render_default = role.role not in {"noise", "unknown_structural"}
            index_default = True
            if role.role in {"noise", "page_header", "page_footer", "frontmatter_noise"}:
                render_default = False
            if role.role in {"noise", "frontmatter_noise", "table_html"}:
                index_default = False
            row = {
                "paper_id": block["paper_id"],
                "page": block["page"],
                "block_id": block["block_id"],
                "raw_label": block.get("raw_label", "unknown"),
                "raw_order": block.get("raw_order", 0),
                "bbox": block.get("bbox", [0, 0, 0, 0]),
                "text": block.get("text", ""),
                "page_width": block.get("page_width", 0),
                "page_height": block.get("page_height", 0),
                "role": role.role,
                "role_confidence": role.confidence,
                "evidence": role.evidence,
                "span_metadata": block.get("span_metadata"),
                "render_default": render_default,
                "index_default": index_default,
            }
            rows.append(row)

    # Build role span profiles from first-pass results
    paper_context: dict = {}
    if len(rows) >= 10:
        from paperforge.worker.ocr_profiles import build_role_span_profiles

        paper_context["role_profiles"] = build_role_span_profiles(rows)

    # Second pass: section-aware role rescue
    if paper_context.get("role_profiles"):
        from paperforge.worker.ocr_document import (
            analyze_document_structure,
            rescue_roles_with_document_context,
        )

        document_structure = analyze_document_structure(rows)
        rows = rescue_roles_with_document_context(rows, paper_context["role_profiles"], document_structure)

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
