from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_document import DocumentStructure
from paperforge.worker.ocr_families import discover_body_family_anchor
from paperforge.worker.ocr_roles import assign_block_role
from paperforge.worker.ocr_signatures import build_block_signatures

_CANDIDATE_ROLES = frozenset(
    {
        "figure_caption_candidate",
        "backmatter_heading_candidate",
        "structured_insert_candidate",
    }
)


def _summarize_page_text_coverage(*, ocr_text: str, pdf_text: str) -> dict:
    ocr_chars = len((ocr_text or "").strip())
    pdf_chars = len((pdf_text or "").strip())
    if pdf_chars == 0:
        return {"page_text_coverage_status": "missing_pdf_text", "page_text_coverage_ratio_chars": None}
    ratio = ocr_chars / max(pdf_chars, 1)
    return {
        "page_text_coverage_status": "low" if ratio < 0.6 else "ok",
        "page_text_coverage_ratio_chars": ratio,
    }


def _classify_region_text_completeness(*, ocr_text: str, pdf_region_text: str) -> dict:
    ocr = (ocr_text or "").strip()
    pdf = (pdf_region_text or "").strip()
    if not pdf:
        return {"text_completeness_status": "pdf_unavailable", "text_completeness_confidence": 0.0}
    if not ocr:
        return {"text_completeness_status": "empty_vs_pdf", "text_completeness_confidence": 0.95}
    if len(ocr) < len(pdf) * 0.45:
        return {"text_completeness_status": "short_vs_pdf", "text_completeness_confidence": 0.8}
    if pdf.startswith(ocr) and len(pdf) > len(ocr) + 24:
        return {"text_completeness_status": "likely_missing_tail", "text_completeness_confidence": 0.85}
    return {"text_completeness_status": "complete", "text_completeness_confidence": 0.7}


def _vertical_gap(a, b) -> float:
    """Distance from bottom of a to top of b (positive = gap, negative = overlap)."""
    ba = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    if len(ba) < 4 or len(bb) < 4:
        return 999
    return float(bb[1]) - float(ba[3])


def _merge_adjacent_headings(rows: list[dict]) -> None:
    """Merge consecutive heading-labeled raw blocks split by OCR line breaks.
    Called BEFORE seed role assignment on raw_blocks, using raw_label only.

    Does NOT merge when the second heading has a deeper numbering level
    (e.g. ``"2.1. Materials"`` after ``"2. Methods"``), which indicates a
    subsection that should stay separate from its parent section heading.
    """
    import re
    _HEADING_NUMBER_DEPTH = re.compile(r"^\s*(\d+(?:\.\d+)*)")
    _COL_SPLIT_RATIO = 0.5

    def _col(b):
        bb = b.get("bbox") or [0, 0, 0, 0]
        pw = float(b.get("page_width", 0) or 0)
        if pw <= 0 or len(bb) < 4:
            return 0
        cx = (bb[0] + bb[2]) / 2
        return 0 if cx < pw * _COL_SPLIT_RATIO else 1

    def _heading_depth(b: dict) -> int:
        m = _HEADING_NUMBER_DEPTH.match(str(b.get("text") or ""))
        if not m:
            return 0
        return m.group(1).count(".") + 1

    i = 0
    while i < len(rows) - 1:
        cur = rows[i]
        nxt = rows[i + 1]
        if (
            cur.get("raw_label") == "paragraph_title"
            and nxt.get("raw_label") == "paragraph_title"
            and cur.get("page") == nxt.get("page")
            and _col(cur) == _col(nxt)
            and _vertical_gap(cur, nxt) <= 30  # OCR line-wrap within same heading
            and _heading_depth(cur) >= _heading_depth(nxt)  # don't swallow deeper subsections
        ):
            cur["text"] = (str(cur.get("text", "")) + " " + str(nxt.get("text", ""))).strip()
            cur["bbox"] = _union_bbox(cur.get("bbox"), nxt.get("bbox"))
            nxt["text"] = ""
            nxt["raw_label"] = "footer"  # suppress from further processing
            i += 2
        else:
            i += 1


def _union_bbox(bbox_a, bbox_b):
    try:
        a = list(bbox_a) if bbox_a else [0, 0, 0, 0]
        b = list(bbox_b) if bbox_b else [0, 0, 0, 0]
        if len(a) < 4 or len(b) < 4:
            return a or b or [0, 0, 0, 0]
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
    except (TypeError, ValueError):
        return bbox_a or bbox_b or [0, 0, 0, 0]


def _has_preproof_cover_page_one(rows: list[dict]) -> bool:
    from paperforge.worker.ocr_roles import is_preproof_marker

    for row in rows:
        if int(row.get("page", 0) or 0) != 1:
            continue
        marker_type = str((row.get("marker_signature") or {}).get("type") or "")
        text = str(row.get("text", "") or row.get("block_content", "") or "")
        if marker_type == "preproof_marker" or is_preproof_marker(text):
            return True
    return False


def _annotate_preproof_cover_drop(rows: list[dict]) -> None:
    for row in rows:
        if int(row.get("page", 0) or 0) <= 1:
            continue
        evidence = row.setdefault("evidence", [])
        if "page_1_preproof_cover_dropped_upstream" not in evidence:
            evidence.append("page_1_preproof_cover_dropped_upstream")
        return


def build_structured_blocks(
    raw_blocks: list[dict],
    source_metadata: dict | None = None,
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

    # Merge raw blocks: adjacent paragraph_title blocks split by OCR line breaks
    for page in by_page:
        _merge_adjacent_headings(by_page[page])

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
            # Structural signatures: observation-first, before any semantic role
            sig_result = build_block_signatures(block)

            role_input = page_as_role_input[i]
            role = assign_block_role(
                role_input,
                page_blocks=page_as_role_input,
                page_width=block.get("page_width", 0),
                page_height=block.get("page_height", 0),
            )
            render_default = role.role not in ({"noise", "unknown_structural", "ocr_raw_error"} | _CANDIDATE_ROLES)
            index_default = role.role not in _CANDIDATE_ROLES
            if role.role in {
                "noise",
                "page_header",
                "page_footer",
                "frontmatter_noise",
                "non_body_insert",
                "structured_insert",
                "ocr_raw_error",
            }:
                render_default = False
            if role.role in {
                "noise", "frontmatter_noise", "table_html",
                "non_body_insert", "structured_insert", "ocr_raw_error",
            }:
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
                "role": "unassigned",
                "role_confidence": role.confidence,
                "evidence": role.evidence,
                "seed_role": role.role,
                "seed_confidence": role.confidence,
                "seed_evidence": list(role.evidence),
                "span_metadata": block.get("span_metadata"),
                "raw_observation": sig_result["raw_observation"],
                "marker_signature": sig_result["marker_signature"],
                "layout_signature": sig_result["layout_signature"],
                "span_signature": sig_result["span_signature"],
                "_in_visual_container": block.get("_in_visual_container", None),
                "_container_bbox": block.get("_container_bbox", None),
                "_container_text": block.get("_container_text", None),
                "render_default": render_default,
                "index_default": index_default,
            }
            from paperforge.worker.ocr_decisions import record_decision

            record_decision(
                row,
                stage="assign_block_role",
                old_role=str(block.get("raw_label", "")),
                new_role=row.get("seed_role"),
                reason="seed role assigned from raw OCR label and local heuristics",
                confidence=row.get("seed_confidence"),
                evidence=row.get("seed_evidence", []),
            )

            rows.append(row)

    if _has_preproof_cover_page_one(rows):
        rows = [row for row in rows if (row.get("page", 0) or 0) != 1]
        _annotate_preproof_cover_drop(rows)

    body_family_anchor = discover_body_family_anchor(rows, page_count=total_pages)
    doc_structure = DocumentStructure(body_family_anchor=body_family_anchor)

    # Build source frontmatter anchors before normalization so the structural gate
    # can verify paper_title and authors roles against source-backed block IDs.
    _sfm_anchors = None
    if source_metadata:
        from paperforge.worker.ocr_metadata import build_source_backed_frontmatter_anchors

        _sfm_anchors = build_source_backed_frontmatter_anchors(
            source_metadata,
            raw_blocks,
        )
        doc_structure.source_frontmatter_anchors = _sfm_anchors

    # Normalize document structure (backmatter boundary, role regime, tail promotion)
    from paperforge.worker.ocr_document import normalize_document_structure

    try:
        doc_structure, rows = normalize_document_structure(rows, source_frontmatter_anchors=_sfm_anchors)
        doc_structure.body_family_anchor = body_family_anchor
        if _sfm_anchors:
            doc_structure.source_frontmatter_anchors = _sfm_anchors
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Document structure normalization failed: %s", exc)

    # Build role span profiles from normalized results
    paper_context: dict = {}
    if len(rows) >= 10:
        from paperforge.worker.ocr_profiles import build_role_span_profiles

        paper_context["role_profiles"] = build_role_span_profiles(rows)

    # Third pass: section-aware role rescue with normalized profiles
    source_anchors = getattr(doc_structure, "source_frontmatter_anchors", {}) if doc_structure else {}
    legacy_rescue_enabled = not bool(source_anchors)

    if paper_context.get("role_profiles") and doc_structure and legacy_rescue_enabled:
        from paperforge.worker.ocr_document import (
            rescue_roles_with_document_context,
        )

        rows = rescue_roles_with_document_context(rows, paper_context["role_profiles"], doc_structure)

    from paperforge.worker.ocr_document import (
        _exclude_tail_nonref_from_body_flow,
        _restore_numbered_body_from_tail_hold,
    )

    _exclude_tail_nonref_from_body_flow(rows)
    _restore_numbered_body_from_tail_hold(rows)

    # Sync render_default/index_default after role normalizations
    for row in rows:
        role = row.get("role", "")
        if row.get("_suppressed_heading"):
            row["render_default"] = False
            row["index_default"] = False
        else:
            row["render_default"] = role not in ({"noise", "unknown_structural", "ocr_raw_error"} | _CANDIDATE_ROLES)
            if role in {
                "noise",
                "page_header",
                "page_footer",
                "frontmatter_noise",
                "non_body_insert",
                "structured_insert",
                "ocr_raw_error",
            }:
                row["render_default"] = False
            row["index_default"] = role not in _CANDIDATE_ROLES
            if role in {
                "noise", "frontmatter_noise", "table_html",
                "non_body_insert", "structured_insert", "ocr_raw_error",
            }:
                row["index_default"] = False

    # Persist document structure artifact for downstream debugging
    if doc_structure and structure_output_dir:
        _write_document_structure_json(doc_structure, structure_output_dir, rows)

    return rows, doc_structure


def _write_document_structure_json(doc_structure, output_dir: str | Path, rows: list[dict] | None = None) -> None:
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
    rows = rows or []
    data["structural_signatures"] = [
        {
            "block_id": row.get("block_id"),
            "page": row.get("page"),
            "raw_observation": row.get("raw_observation"),
            "marker_signature": row.get("marker_signature"),
            "layout_signature": row.get("layout_signature"),
            "span_signature": row.get("span_signature"),
        }
        for row in rows
        if row.get("block_id")
    ]
    data["anchors"] = {
        "body_family_anchor": data.get("body_family_anchor"),
        "reference_family_anchor": data.get("reference_family_anchor"),
    }
    data["zones"] = data.get("region_bus") or {}
    output_path = Path(output_dir) / "document_structure.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_structured_blocks_jsonl(path: Path, rows: list[dict]) -> None:
    from paperforge.worker.ocr_decisions import strip_decision_logs

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in strip_decision_logs(rows):
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
