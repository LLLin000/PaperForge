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


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursive dict merge with list replace."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _resolve_field(data: dict, path: str) -> Any:
    """Resolve dotted field path against a nested dict."""
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _apply_op(value, op: str, target) -> bool:
    """Apply comparison operator."""
    if op == "gt":
        return isinstance(value, (int, float)) and value > target
    elif op == "lt":
        return isinstance(value, (int, float)) and value < target
    elif op == "eq":
        return value == target
    return False


def _check_hard_red(policy: dict, quality_report: dict) -> list[str]:
    """Check hard-red rules against the full quality report.

    Returns:
        list of triggered hard-red rule names.
    """
    triggered: list[str] = []
    for rule in policy.get("hard_red", []):
        if "condition" in rule:
            cond = rule["condition"]
            val_a = _resolve_field(quality_report, cond["field_a"])
            val_b = _resolve_field(quality_report, cond["field_b"])
            match_a = _apply_op(val_a, cond["op_a"], cond["value_a"])
            match_b = _apply_op(val_b, cond["op_b"], cond["value_b"])
            if match_a and match_b:
                triggered.append(rule["rule"])
        else:
            val = _resolve_field(quality_report, rule["field"])
            if _apply_op(val, rule["op"], rule["value"]):
                triggered.append(rule["rule"])
    return triggered


def load_readiness_policy(
    policy: dict | None = None,
    *,
    policy_path: str | Path | None = None,
) -> dict:
    """Load and merge readiness policy.

    Args:
        policy: in-memory policy dict (mutually exclusive with policy_path)
        policy_path: path to explicit YAML file (mutually exclusive with policy)

    Returns:
        merged policy dict

    Resolution order:
        1. Default: paperforge/policies/ocr_readiness_v1.yaml (via importlib.resources)
        2. If policy_path is provided: deep-merge that file over default. Skip user override.
        3. Else if ~/.paperforge/policies/ocr_readiness_v1.yaml exists: deep-merge user override.
        4. If in-memory policy is provided: deep-merge over whatever was loaded.

    Merge rules:
        - dicts: recursive deep-merge
        - lists: replace (not append)
        - scalars: override
    """
    if policy is not None and policy_path is not None:
        raise ValueError("policy and policy_path are mutually exclusive")

    from pathlib import Path

    import yaml
    from importlib.resources import files as pkg_files

    # 1. Load default
    default_path = pkg_files("paperforge") / "policies/ocr_readiness_v1.yaml"
    with open(default_path, "r", encoding="utf-8") as fh:
        merged = yaml.safe_load(fh) or {}

    # 2. Load explicit policy_path or user override
    if policy_path is not None:
        with open(policy_path, "r", encoding="utf-8") as fh:
            override = yaml.safe_load(fh) or {}
        merged = _deep_merge(merged, override)
    else:
        user_path = Path.home() / ".paperforge" / "policies" / "ocr_readiness_v1.yaml"
        if user_path.exists():
            with open(user_path, "r", encoding="utf-8") as fh:
                override = yaml.safe_load(fh) or {}
            merged = _deep_merge(merged, override)

    # 3. In-memory policy overrides everything
    if policy is not None:
        merged = _deep_merge(merged, policy)

    return merged


STATUS_RANK = {"red": 0, "unknown": 1, "yellow": 2, "green": 3}
STATUS_SCORE = {"green": 1.0, "yellow": 0.6, "red": 0.2, "unknown": 0.5}


def _evaluate_gate(indicators: dict, indicator_name: str, min_status: str) -> dict:
    """Evaluate a single gate against an indicator.

    unknown status fails required gates (rank 1 < yellow 2).
    """
    ind = indicators.get(indicator_name, {})
    actual_status = ind.get("status", "unknown")
    passes = STATUS_RANK.get(actual_status, 1) >= STATUS_RANK.get(min_status, 2)
    return {
        "indicator": indicator_name,
        "actual_status": actual_status,
        "min_status": min_status,
        "passes": passes,
    }


def compute_use_cases(policy: dict, indicators: dict) -> dict:
    """Compute recommended use cases from policy and indicators."""
    result: dict[str, Any] = {}
    for uc_name, uc_config in policy.get("use_cases", {}).items():
        # Check not_applicable shortcut
        if uc_config.get("if_no_figure_table_evidence") == "not_applicable":
            fig_ind = indicators.get("figure_table_integrity", {})
            if fig_ind.get("applicability") == "not_applicable":
                result[uc_name] = {"recommended": "not_applicable", "gate_results": []}
                continue

        gates = uc_config.get("gates", {})
        gate_results: list[dict] = []
        all_required_pass = True

        for gate in gates.get("required", []):
            gr = _evaluate_gate(indicators, gate["indicator"], gate["min_status"])
            gr["required"] = True
            gate_results.append(gr)
            if not gr["passes"]:
                all_required_pass = False

        for gate in gates.get("soft", []):
            gr = _evaluate_gate(indicators, gate["indicator"], gate["min_status"])
            gr["required"] = False
            gate_results.append(gr)

        result[uc_name] = {
            "recommended": "yes" if all_required_pass else "no",
            "gate_results": gate_results,
        }

    return result


def evaluate_readiness(
    quality_report_base: dict,
    policy: dict | None = None,
    *,
    policy_path: str | Path | None = None,
) -> dict:
    """Apply readiness policy to quality report.

    Args:
        quality_report_base: output of build_quality_indicators()
        policy: in-memory policy dict (mutually exclusive with policy_path)
        policy_path: path to YAML policy file

    Returns:
        dict with user_readiness + recommended_use
    """
    from pathlib import Path

    merged_policy = load_readiness_policy(policy, policy_path=policy_path)
    indicators = quality_report_base.get("quality_indicators", {})

    # Hard-red check (resolves fields against full quality report)
    triggered = _check_hard_red(merged_policy, quality_report_base)

    # Weighted score
    weights = merged_policy.get("weights", {})
    total_weight = 0.0
    weighted_sum = 0.0
    dim_statuses: dict[str, str] = {}
    for dim, weight in weights.items():
        ind = indicators.get(dim, {})
        if ind.get("applicability") == "not_applicable":
            continue  # exclude from weighted score, renormalize
        status = ind.get("status", "unknown")
        dim_statuses[dim] = status
        score = STATUS_SCORE.get(status, 0.5)
        weighted_sum += weight * score
        total_weight += weight

    score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Status determination
    hard_red = len(triggered) > 0
    if hard_red:
        status = "red"
        score = min(score, 0.3)
    elif score >= 0.75:
        status = "green"
    elif score >= 0.40:
        status = "yellow"
    else:
        status = "red"

    return {
        "user_readiness": {
            "status": status,
            "score": round(score, 4),
            "policy_version": merged_policy.get("schema_version", ""),
            "basis": "policy_estimate",
            "hard_red_triggers": triggered,
        },
        "recommended_use": compute_use_cases(merged_policy, indicators),
    }
