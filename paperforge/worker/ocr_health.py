from __future__ import annotations

from pathlib import Path
from typing import Any


def build_ocr_health(
    *,
    page_count: int,
    raw_blocks_count: int,
    structured_blocks: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    doc_structure: Any = None,
) -> dict[str, Any]:
    section_heading_count = sum(1 for b in structured_blocks if b.get("role") == "section_heading")
    abstract_found = any(
        b.get("role") in ("abstract_heading", "abstract_body") or b.get("raw_label") == "abstract"
        for b in structured_blocks
    )
    references_found = any(
        b.get("role") in ("reference_heading", "reference_item") or b.get("raw_label") == "reference_content"
        for b in structured_blocks
    )
    figure_caption_count = sum(1 for b in structured_blocks if b.get("role") == "figure_caption")
    table_caption_count = sum(1 for b in structured_blocks if b.get("role") == "table_caption")

    figure_asset_count = len(figure_inventory.get("matched_figures", []))
    unmatched_legends = len(figure_inventory.get("unmatched_legends", []))
    unmatched_figure_assets = len(figure_inventory.get("unmatched_assets", []))
    tables = table_inventory.get("tables", [])
    table_asset_count = sum(1 for t in tables if t.get("has_asset"))
    empty_tables = sum(1 for t in tables if not t.get("has_asset"))
    formal_table_count = len([t for t in tables if not t.get("is_continuation")])
    entries_with_asset = sum(1 for t in tables if t.get("has_asset"))
    table_segment_count = entries_with_asset + len(table_inventory.get("unmatched_assets", []))

    media_without_caption = unmatched_figure_assets
    caption_without_media = unmatched_legends + len(table_inventory.get("unmatched_captions", []))

    frontmatter_quality = 1.0 if abstract_found and references_found else 0.5

    issues = 0
    if caption_without_media > 0:
        issues += 1
    if media_without_caption > 0:
        issues += 1
    if empty_tables > 0:
        issues += 1
    if not abstract_found:
        issues += 1
    if not references_found:
        issues += 1
    if section_heading_count < 2:
        issues += 1

    if issues == 0 and frontmatter_quality >= 0.5:
        overall = "green"
    elif issues <= 2:
        overall = "yellow"
    else:
        overall = "red"

    # Compute structural health signals
    from paperforge.worker.ocr_document import _compute_span_coverage, _detect_body_spine, _run_layout_audit

    span = _compute_span_coverage(structured_blocks)
    spine = _detect_body_spine(structured_blocks, doc=doc_structure)
    layout = _run_layout_audit(structured_blocks)

    tail_score = {}
    if doc_structure is not None and hasattr(doc_structure, "tail_boundary_score"):
        tail_score = doc_structure.tail_boundary_score or {}

    # Collect decision log summaries
    from paperforge.worker.ocr_decisions import collect_decisions, summarize_decisions

    decision_summary = summarize_decisions(collect_decisions(structured_blocks))

    report = {
        "page_count": page_count,
        "blocks_count": raw_blocks_count,
        "section_heading_count": section_heading_count,
        "abstract_found": abstract_found,
        "references_found": references_found,
        "figure_caption_count": figure_caption_count,
        "figure_asset_count": figure_asset_count,
        "table_caption_count": table_caption_count,
        "table_asset_count": table_asset_count,
        "formal_table_count": formal_table_count,
        "table_segment_count": table_segment_count,
        "media_without_caption_count": media_without_caption,
        "caption_without_media_count": caption_without_media,
        "empty_table_count": empty_tables,
        "frontmatter_quality": frontmatter_quality,
        "overall": overall,
        "span_coverage": span,
        "span_coverage_quality": span.get("coverage_quality", "weak"),
        "degraded_mode_active": span.get("degraded_mode_active", True),
        "body_spine_quality": spine.get("_meta", {}).get("quality", "weak"),
        "body_anchor_pages": spine.get("_meta", {}).get("anchor_pages", []),
        "body_spine_sample_count": spine.get("_meta", {}).get("sample_count", 0),
        "layout_audit_status": layout.get("status", "unknown"),
        "layout_anomaly_pages": layout.get("anomaly_pages", []),
        "layout_anomaly_count": layout.get("anomaly_count", 0),
        "tail_boundary_confidence": tail_score.get("score", 0.0),
    }
    report.update(decision_summary)

    degraded_reasons = []
    if span.get("coverage_quality", "weak") == "weak":
        degraded_reasons.append(f"weak span coverage ({span.get('coverage_ratio', 0):.0%})")
    if spine.get("_meta", {}).get("quality", "weak") == "weak":
        degraded_reasons.append("weak body spine")
    if layout.get("status", "unknown") == "fail":
        degraded_reasons.append(f"layout audit failed ({layout.get('anomaly_count', 0)} anomalies)")

    report["degraded_reasons"] = degraded_reasons

    def _score_distribution(scores: list[float]) -> dict:
        return {
            "high": sum(1 for s in scores if s >= 0.75),
            "medium": sum(1 for s in scores if 0.4 <= s < 0.75),
            "low": sum(1 for s in scores if s < 0.4),
        }

    fig_scores = []
    for mf in figure_inventory.get("matched_figures", []):
        cs = mf.get("caption_score", {})
        if "score" in cs:
            fig_scores.append(cs["score"])
    for rl in figure_inventory.get("rejected_legends", []):
        cs = rl.get("caption_score", {})
        if "score" in cs:
            fig_scores.append(cs["score"])

    table_scores = []
    for t in tables:
        ms = t.get("match_score", {})
        if "score" in ms:
            table_scores.append(ms["score"])

    report["figure_match_confidence_distribution"] = _score_distribution(fig_scores)
    report["table_match_confidence_distribution"] = _score_distribution(table_scores)

    low_confidence_figures = [s for s in fig_scores if s < 0.4]
    if low_confidence_figures:
        degraded_reasons.append(f"low figure caption confidence ({len(low_confidence_figures)} figures)")
    low_confidence_tables = [s for s in table_scores if s < 0.4]
    if low_confidence_tables:
        degraded_reasons.append(f"low table match confidence ({len(low_confidence_tables)} tables)")

    return report


def build_span_coverage_health(blocks: list[dict]) -> dict:
    """Compute span metadata coverage health from structured blocks."""
    from paperforge.worker.ocr_document import _compute_span_coverage

    return _compute_span_coverage(blocks)


def build_spine_health(body_spine: dict) -> dict:
    quality = body_spine.get("_meta", {}).get("quality", "weak")
    return {
        "body_spine_quality": quality,
        "body_anchor_pages": body_spine.get("_meta", {}).get("anchor_pages", []),
        "body_spine_sample_count": body_spine.get("_meta", {}).get("sample_count", 0),
    }


def build_layout_audit_health(layout_audit: dict) -> dict:
    return {
        "layout_audit_status": layout_audit.get("status", "unknown"),
        "layout_anomaly_pages": layout_audit.get("anomaly_pages", []),
        "layout_anomaly_count": layout_audit.get("anomaly_count", 0),
    }


def write_ocr_health(health_root: Path, report: dict[str, Any]) -> None:
    from paperforge.core.io import write_json

    health_root.mkdir(parents=True, exist_ok=True)
    write_json(health_root / "ocr_health.json", report)
