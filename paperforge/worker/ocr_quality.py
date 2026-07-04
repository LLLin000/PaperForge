from __future__ import annotations

from typing import Any


def _make_indicator(
    status: str = "unknown",
    applicability: str = "unknown",
    signals: dict | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "applicability": applicability,
        "signals": signals or {},
        "evidence": evidence or [],
    }


def _normalize_rendered_text_integrity(health: dict) -> dict[str, Any]:
    gap_count = int(health.get("rendered_text_gap_count", 0))
    body_spine = health.get("body_spine_quality", "unknown")

    signals = {"gap_count": gap_count, "body_spine_quality": body_spine}
    evidence = [f"rendered_text_gap_count={gap_count}", f"body_spine_quality={body_spine}"]

    if gap_count > 10:
        return _make_indicator("red", "applicable", signals, evidence)
    if gap_count >= 4:
        return _make_indicator("yellow", "applicable", signals, evidence)
    if body_spine == "weak":
        return _make_indicator("yellow", "applicable", signals, evidence)
    return _make_indicator("green", "applicable", signals, evidence)


def _normalize_body_reference_structure(
    health: dict,
    structured_blocks: list[dict] | None = None,
) -> dict[str, Any]:
    health_profile = health.get("health_profile", "standard")
    layout_status = health.get("layout_audit_status", "pass")
    anomaly_count = int(health.get("layout_anomaly_count", 0))
    body_spine = health.get("body_spine_quality", "unknown")
    refs_found = health.get("references_found", False)
    heading_count = int(health.get("section_heading_count", 0))

    if structured_blocks is not None:
        ref_item_count = sum(1 for b in structured_blocks if b.get("role") == "reference_item")
    else:
        ref_item_count = int(health.get("reference_item_count", 0))

    signals = {
        "health_profile": health_profile,
        "layout_audit_status": layout_status,
        "layout_anomaly_count": anomaly_count,
        "body_spine_quality": body_spine,
        "references_found": refs_found,
        "section_heading_count": heading_count,
        "reference_item_count": ref_item_count,
    }
    evidence = [f"{k}={v}" for k, v in signals.items()]

    is_standard = health_profile == "standard"

    if is_standard and not refs_found and heading_count < 2:
        return _make_indicator("red", "applicable", signals, evidence)

    if layout_status == "fail" and body_spine == "weak":
        return _make_indicator("red", "applicable", signals, evidence)

    if anomaly_count > 0 or body_spine == "partial":
        return _make_indicator("yellow", "applicable", signals, evidence)

    return _make_indicator("green", "applicable", signals, evidence)


def _normalize_figure_table_integrity(
    health: dict,
    figure_inventory: dict | None = None,
    table_inventory: dict | None = None,
) -> dict[str, Any]:
    # Figure data
    if figure_inventory is not None:
        matched_count = len(figure_inventory.get("matched_figures", []))
        unmatched_asset_count = len(figure_inventory.get("unmatched_assets", []))
        unresolved_cluster_count = len(figure_inventory.get("unresolved_clusters", []))
        unmatched_legend_count = len(figure_inventory.get("unmatched_legends", []))
        held_count = len(figure_inventory.get("held_figures", []))
        completeness = figure_inventory.get("figure_legend_completeness", {})
        accounted = completeness.get("accounted_for", 0) if isinstance(completeness, dict) else 0
        total = completeness.get("total", 0) if isinstance(completeness, dict) else 0
        completeness_ratio = accounted / total if total > 0 else 1.0
    else:
        matched_count = int(health.get("matched_figure_count_v2", 0))
        unmatched_asset_count = int(health.get("media_without_caption_count", 0))
        unresolved_cluster_count = int(health.get("unresolved_cluster_count", 0))
        unmatched_legend_count = int(health.get("caption_without_media_count", 0))
        held_count = int(health.get("held_figure_count", 0))
        completeness_ratio = float(health.get("figure_legend_completeness_ratio", 1.0))

    # Legacy health fields
    caption_count = int(health.get("figure_caption_count", 0))
    reader_ratio = float(health.get("figure_reader_coverage_ratio", 1.0))

    # Table data
    if table_inventory is not None:
        tables = table_inventory.get("tables", [])
        table_asset_count = sum(1 for t in tables if t.get("has_asset"))
        table_unmatched = len(table_inventory.get("unmatched_captions", []))
    else:
        table_asset_count = int(health.get("table_asset_count", 0))
        table_unmatched = int(health.get("table_unmatched_count", 0))

    has_figure_evidence = (
        caption_count > 0
        or matched_count > 0
        or unmatched_asset_count > 0
        or unresolved_cluster_count > 0
    )
    has_table_evidence = table_asset_count > 0 or table_unmatched > 0

    signals = {
        "matched_figure_count": matched_count,
        "unmatched_asset_count": unmatched_asset_count,
        "unresolved_cluster_count": unresolved_cluster_count,
        "unmatched_legend_count": unmatched_legend_count,
        "held_figure_count": held_count,
        "figure_caption_count": caption_count,
        "figure_reader_coverage_ratio": reader_ratio,
        "figure_legend_completeness_ratio": completeness_ratio,
        "table_asset_count": table_asset_count,
        "table_unmatched_count": table_unmatched,
    }
    evidence = [f"{k}={v}" for k, v in signals.items()]

    if has_figure_evidence and matched_count == 0 and (
        unmatched_legend_count > 0
        or unmatched_asset_count > 0
        or unresolved_cluster_count > 0
        or reader_ratio < 1.0
    ):
        return _make_indicator("red", "applicable", signals, evidence)

    if not has_figure_evidence and not has_table_evidence:
        return _make_indicator("green", "not_applicable", signals, evidence)

    return _make_indicator("green", "applicable", signals, evidence)


def _normalize_metadata_frontmatter_quality(
    health: dict,
    resolved_metadata: dict | None = None,
) -> dict[str, Any]:
    if resolved_metadata is not None:
        title_val = resolved_metadata.get("title", {})
        title = title_val.get("value", "") if isinstance(title_val, dict) else str(title_val) if title_val else ""
        authors = resolved_metadata.get("authors_display", "")
        doi_val = resolved_metadata.get("doi", {})
        doi = doi_val.get("value", "") if isinstance(doi_val, dict) else str(doi_val) if doi_val else ""
    else:
        title = health.get("title", "")
        authors = health.get("authors_display", "")
        doi = health.get("doi", "")

    abstract_found = health.get("abstract_found", False)

    signals = {
        "title_present": bool(title),
        "authors_present": bool(authors),
        "doi_present": bool(doi),
        "abstract_found": abstract_found,
    }
    evidence = [f"{k}={v}" for k, v in signals.items()]

    if not title or not authors:
        return _make_indicator("yellow", "applicable", signals, evidence)

    return _make_indicator("green", "applicable", signals, evidence)


def _normalize_confidence_fallbacks(health: dict) -> dict[str, Any]:
    degraded = health.get("degraded_mode_active", False)
    span_coverage = health.get("span_coverage_quality", "good")

    signals = {
        "degraded_mode_active": degraded,
        "span_coverage_quality": span_coverage,
    }
    evidence = [f"{k}={v}" for k, v in signals.items()]

    if degraded and span_coverage in ("poor", "none"):
        return _make_indicator("yellow", "applicable", signals, evidence)

    return _make_indicator("green", "applicable", signals, evidence)


def build_quality_indicators(
    *,
    health: dict,
    figure_inventory: dict | None = None,
    table_inventory: dict | None = None,
    structured_blocks: list[dict] | None = None,
    resolved_metadata: dict | None = None,
    reader_payload: dict | None = None,
    run_integrity: dict | None = None,
) -> dict:
    developer_diagnostics = {
        "run_integrity": dict(run_integrity or {}),
        "anchor_summary": health.get("anchor_summary", {}),
        "zone_summary": health.get("zone_summary", {}),
        "decision_summary": {},
        "raw_health_keys": list(health.keys()),
    }

    return {
        "schema_version": "ocr_quality_v1",
        "quality_indicators": {
            "rendered_text_integrity": _normalize_rendered_text_integrity(health),
            "body_reference_structure": _normalize_body_reference_structure(health, structured_blocks),
            "figure_table_integrity": _normalize_figure_table_integrity(health, figure_inventory, table_inventory),
            "metadata_frontmatter_quality": _normalize_metadata_frontmatter_quality(health, resolved_metadata),
            "confidence_and_fallbacks": _normalize_confidence_fallbacks(health),
        },
        "developer_diagnostics": developer_diagnostics,
    }
