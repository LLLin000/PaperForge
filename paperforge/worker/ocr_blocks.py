from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_roles import assign_block_role

_CANDIDATE_ROLES = frozenset({
    "figure_caption_candidate",
    "backmatter_heading_candidate",
    "backmatter_boundary_candidate",
})


def build_structured_blocks(
    raw_blocks: list[dict],
    structure_output_dir: str | Path | None = None,
) -> tuple[list[dict], Any]:
    """Build structured blocks with role assignment, normalization, and rescue.

    Returns (rows, doc_structure_or_None) so callers can pass the
    document structure artifact downstream without re-computing it.
    """
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
            render_default = role.role not in ({"noise", "unknown_structural"} | _CANDIDATE_ROLES)
            index_default = role.role not in _CANDIDATE_ROLES
            if role.role in {"noise", "page_header", "page_footer", "frontmatter_noise", "non_body_insert"}:
                render_default = False
            if role.role in {"noise", "frontmatter_noise", "table_html", "non_body_insert"}:
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

    # Normalize document structure (backmatter boundary, role regime, tail promotion)
    from paperforge.worker.ocr_document import normalize_document_structure

    doc_structure = None
    try:
        doc_structure, rows = normalize_document_structure(rows)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Document structure normalization failed: %s", exc
        )

    # Build role span profiles from normalized results
    paper_context: dict = {}
    if len(rows) >= 10:
        from paperforge.worker.ocr_profiles import build_role_span_profiles

        paper_context["role_profiles"] = build_role_span_profiles(rows)

    # Third pass: section-aware role rescue with normalized profiles
    if paper_context.get("role_profiles") and doc_structure:
        from paperforge.worker.ocr_document import (
            rescue_roles_with_document_context,
        )

        rows = rescue_roles_with_document_context(rows, paper_context["role_profiles"], doc_structure)

    # Sync render_default/index_default after role normalizations
    for row in rows:
        role = row.get("role", "")
        row["render_default"] = role not in ({"noise", "unknown_structural"} | _CANDIDATE_ROLES)
        if role in {"noise", "page_header", "page_footer", "frontmatter_noise", "non_body_insert"}:
            row["render_default"] = False
        row["index_default"] = role not in _CANDIDATE_ROLES
        if role in {"noise", "frontmatter_noise", "table_html", "non_body_insert"}:
            row["index_default"] = False

    # Persist document structure artifact for downstream debugging
    if doc_structure and structure_output_dir:
        _write_document_structure_json(doc_structure, structure_output_dir)

    return rows, doc_structure


def _write_document_structure_json(doc_structure, output_dir: str | Path) -> None:
    """Serialize DocumentStructure to JSON for downstream inspection."""
    import dataclasses

    if hasattr(doc_structure, "_asdict"):
        data = doc_structure._asdict()
    elif dataclasses.is_dataclass(doc_structure):
        data = dataclasses.asdict(doc_structure)
    else:
        return
    # Convert non-serializable types
    for k, v in data.items():
        if hasattr(v, "_asdict"):
            data[k] = v._asdict()
        elif dataclasses.is_dataclass(v):
            data[k] = dataclasses.asdict(v)
    output_path = Path(output_dir) / "document_structure.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
