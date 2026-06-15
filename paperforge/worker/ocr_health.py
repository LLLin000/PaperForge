from __future__ import annotations

from pathlib import Path
from typing import Any


def _doc_attr(doc_structure: Any, name: str, default=None):
    if doc_structure is None:
        return default
    if isinstance(doc_structure, dict):
        return doc_structure.get(name, default)
    return getattr(doc_structure, name, default)


def _decision_status(value: Any) -> str:
    if isinstance(value, dict):
        status = value.get("status")
        if isinstance(status, str) and status:
            return status
    if isinstance(value, str) and value:
        return value
    return "OBSERVATION_ONLY"


def _build_anchor_summary(doc_structure: Any) -> dict[str, str]:
    if isinstance(doc_structure, dict) and "anchor_summary" in doc_structure:
        return dict(doc_structure.get("anchor_summary") or {})
    return {
        "body_family_anchor": _decision_status(_doc_attr(doc_structure, "body_family_anchor", {})),
        "reference_family_anchor": _decision_status(_doc_attr(doc_structure, "reference_family_anchor", {})),
    }


def _build_zone_summary(doc_structure: Any) -> dict[str, str]:
    if isinstance(doc_structure, dict) and "zone_summary" in doc_structure:
        return dict(doc_structure.get("zone_summary") or {})
    region_bus = _doc_attr(doc_structure, "region_bus", {}) or {}
    return {zone_name: _decision_status(zone) for zone_name, zone in region_bus.items()}


def _build_held_counts(doc_structure: Any, *, held_figure_count: int, held_table_count: int) -> dict[str, int]:
    if isinstance(doc_structure, dict) and "held_counts" in doc_structure:
        held = dict(doc_structure.get("held_counts") or {})
        held.setdefault("matches", held_figure_count + held_table_count)
        return held
    return {
        "families": 0,
        "matches": held_figure_count + held_table_count,
    }


def build_ocr_health(
    *,
    page_count: int,
    raw_blocks_count: int,
    structured_blocks: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    doc_structure: Any = None,
    reader_payload: dict | None = None,
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
    grouped_figure_match_count = sum(
        1 for mf in figure_inventory.get("matched_figures", []) if len(mf.get("matched_assets", [])) > 1
    )
    single_asset_figure_match_count = sum(
        1 for mf in figure_inventory.get("matched_figures", []) if len(mf.get("matched_assets", [])) == 1
    )
    held_figure_count = len(figure_inventory.get("held_figures", []))
    unmatched_legends = len(figure_inventory.get("unmatched_legends", []))
    unmatched_figure_assets = len(figure_inventory.get("unmatched_assets", []))
    tables = table_inventory.get("tables", [])
    held_table_count = len(table_inventory.get("held_tables", []))
    table_asset_count = sum(1 for t in tables if t.get("has_asset"))
    empty_tables = sum(1 for t in tables if not t.get("has_asset"))
    formal_table_count = len([t for t in tables if not t.get("is_continuation")])
    entries_with_asset = sum(1 for t in tables if t.get("has_asset"))
    table_segment_count = entries_with_asset + len(table_inventory.get("unmatched_assets", []))
    ambiguous_table_match_count = sum(1 for t in tables if t.get("match_status") == "ambiguous")
    low_confidence_table_match_count = sum(1 for t in tables if t.get("match_status") == "matched_low_confidence")

    low_confidence_insert_candidate_count = sum(
        1
        for b in structured_blocks
        if b.get("role") == "structured_insert_candidate" and float(b.get("insert_score", {}).get("score", 0.0)) < 0.7
    )
    candidate_forced_count = sum(
        1
        for b in structured_blocks
        if b.get("role") == "structured_insert" and float(b.get("insert_score", {}).get("score", 1.0)) < 0.7
    )

    media_without_caption = unmatched_figure_assets
    caption_without_media = unmatched_legends + len(table_inventory.get("unmatched_captions", []))

    frontmatter_quality = 1.0 if abstract_found and references_found else 0.5

    # Figure legend completeness: every numbered formal legend must have an outcome
    completeness = figure_inventory.get("figure_legend_completeness", {})
    formal_legend_total = int(completeness.get("total", 0))
    formal_legend_accounted = int(completeness.get("accounted_for", 0))
    formal_legend_gaps = int(completeness.get("gap_count", 0))

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
    if formal_legend_gaps > 0:
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
    layout = _run_layout_audit(
        structured_blocks,
        body_spine=spine,
        page_layouts=_doc_attr(doc_structure, "page_layouts", None),
    )

    tail_score = {}
    tail_score = _doc_attr(doc_structure, "tail_boundary_score", {}) or {}

    # Collect decision log summaries
    from paperforge.worker.ocr_decisions import collect_decisions, summarize_decisions

    decision_summary = summarize_decisions(collect_decisions(structured_blocks))

    ambiguous_figure_match_count = len(figure_inventory.get("ambiguous_figures", []))
    unresolved_cluster_count = len(figure_inventory.get("unresolved_clusters", []))
    low_score_matched_figures = sum(
        1
        for mf in figure_inventory.get("matched_figures", [])
        if float(mf.get("caption_score", {}).get("score", 1.0)) < 0.4
    )
    low_score_matched_tables = sum(
        1 for t in tables if t.get("has_asset") and float(t.get("match_score", {}).get("score", 1.0)) < 0.4
    )
    low_tail_boundary_confidence = tail_score.get("score", 1.0) < 0.4
    hard_rule_decision_count = (
        int(decision_summary.get("structured_insert_decision_count", 0))
        + int(decision_summary.get("tail_promotion_count", 0))
        + int(decision_summary.get("candidate_resolution_count", 0))
        + candidate_forced_count
    )

    anchor_summary = _build_anchor_summary(doc_structure)
    zone_summary = _build_zone_summary(doc_structure)
    held_counts = _build_held_counts(
        doc_structure,
        held_figure_count=held_figure_count,
        held_table_count=held_table_count,
    )

    report = {
        "page_count": page_count,
        "blocks_count": raw_blocks_count,
        "section_heading_count": section_heading_count,
        "abstract_found": abstract_found,
        "references_found": references_found,
        "figure_caption_count": figure_caption_count,
        "figure_asset_count": figure_asset_count,
        "grouped_figure_match_count": grouped_figure_match_count,
        "single_asset_figure_match_count": single_asset_figure_match_count,
        "held_figure_count": held_figure_count,
        "table_caption_count": table_caption_count,
        "table_asset_count": table_asset_count,
        "held_table_count": held_table_count,
        "formal_table_count": formal_table_count,
        "table_segment_count": table_segment_count,
        "ambiguous_table_match_count": ambiguous_table_match_count,
        "low_confidence_table_match_count": low_confidence_table_match_count,
        "low_confidence_insert_candidate_count": low_confidence_insert_candidate_count,
        "candidate_forced_count": candidate_forced_count,
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
        "low_score_but_matched_count": low_score_matched_figures + low_score_matched_tables,
        "ambiguous_match_count": ambiguous_figure_match_count + ambiguous_table_match_count,
        "ambiguous_figure_match_count": ambiguous_figure_match_count,
        "unresolved_cluster_count": unresolved_cluster_count,
        "held_match_count": held_figure_count + held_table_count,
        "low_tail_boundary_confidence": low_tail_boundary_confidence,
        "hard_rule_decision_count": hard_rule_decision_count,
        "anchor_summary": anchor_summary,
        "zone_summary": zone_summary,
        "held_counts": held_counts,
        "figure_legend_completeness_total": formal_legend_total,
        "figure_legend_completeness_accounted": formal_legend_accounted,
        "figure_legend_completeness_gap_count": formal_legend_gaps,
        "figure_legend_completeness_ratio": (
            formal_legend_accounted / formal_legend_total if formal_legend_total > 0 else 1.0
        ),
    }

    if reader_payload is not None:
        rc = reader_payload.get("reader_coverage", {})
        report["figure_reader_coverage_total"] = rc.get("total", 0)
        report["figure_reader_coverage_accounted"] = rc.get("accounted", 0)
        report["figure_reader_coverage_gap_count"] = rc.get("gap_count", 0)
        report["figure_reader_coverage_ratio"] = rc.get("ratio", 1.0)
        reader_figures = reader_payload.get("reader_figures", [])
        reader_count = sum(
            1
            for figure in reader_figures
            if figure.get("reader_status") != "DEPRECATED" and figure.get("visual_groups")
        )
        report["figure_reader_count"] = reader_count

    report.update(decision_summary)

    role_gate_summary = _doc_attr(doc_structure, "role_gate_summary", None) or {}
    if role_gate_summary:
        report["role_gate_summary"] = role_gate_summary

    degraded_reasons = []
    if span.get("coverage_quality", "weak") == "weak":
        degraded_reasons.append(f"weak span coverage ({span.get('coverage_ratio', 0):.0%})")
    if spine.get("_meta", {}).get("quality", "weak") == "weak":
        degraded_reasons.append("weak body spine")
    if layout.get("error_count", 0) > 0:
        degraded_reasons.append(f"layout audit errors ({layout.get('error_count', 0)} errors)")

    if role_gate_summary.get("status") == "degraded":
        degraded_reasons.append("OCR structural role gate degraded")

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

    layout_confidences = []
    page_layouts = _doc_attr(doc_structure, "page_layouts", None)
    if page_layouts:
        layout_confidences = [float(p.confidence) for p in page_layouts.values()]
    report["layout_confidence_distribution"] = _score_distribution(layout_confidences)

    low_confidence_figures = [s for s in fig_scores if s < 0.4]
    if low_confidence_figures:
        degraded_reasons.append(f"low figure caption confidence ({len(low_confidence_figures)} figures)")
    low_confidence_tables = [s for s in table_scores if s < 0.4]
    if low_confidence_tables:
        degraded_reasons.append(f"low table match confidence ({len(low_confidence_tables)} tables)")
    if formal_legend_gaps > 0:
        degraded_reasons.append(
            f"figure legend completeness gap ({formal_legend_gaps} numbered legends unaccounted for)"
        )
    if reader_payload is not None and reader_payload.get("reader_coverage", {}).get("gap_count", 0) > 0:
        degraded_reasons.append("reader_figure_coverage_gap")

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
