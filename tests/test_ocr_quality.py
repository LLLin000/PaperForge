from __future__ import annotations


def test_a1_all_indicators_have_correct_shape() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {"body_spine_quality": "strong"}
    result = build_quality_indicators(health=health)

    indicators = result["quality_indicators"]
    assert set(indicators.keys()) == {
        "rendered_text_integrity",
        "body_reference_structure",
        "figure_table_integrity",
        "metadata_frontmatter_quality",
        "confidence_and_fallbacks",
    }

    for name, ind in indicators.items():
        assert isinstance(ind, dict), f"{name} is not a dict"
        assert "status" in ind, f"{name} missing status"
        assert "applicability" in ind, f"{name} missing applicability"
        assert "signals" in ind, f"{name} missing signals"
        assert "evidence" in ind, f"{name} missing evidence"
        assert ind["status"] in ("green", "yellow", "red", "unknown"), f"{name} bad status"
        assert ind["applicability"] in ("applicable", "not_applicable", "unknown"), f"{name} bad applicability"

    assert result["schema_version"] == "ocr_quality_v1"
    assert "developer_diagnostics" in result


def test_a2_rendered_text_integrity_red_gap_over_10() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {
        "rendered_text_gap_count": 15,
        "body_spine_quality": "strong",
    }
    result = build_quality_indicators(health=health)
    ind = result["quality_indicators"]["rendered_text_integrity"]
    assert ind["status"] == "red"
    assert ind["applicability"] == "applicable"
    assert ind["signals"]["gap_count"] == 15


def test_a3_rendered_text_integrity_yellow_gap_4_to_10() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {
        "rendered_text_gap_count": 7,
        "body_spine_quality": "strong",
    }
    result = build_quality_indicators(health=health)
    ind = result["quality_indicators"]["rendered_text_integrity"]
    assert ind["status"] == "yellow"
    assert ind["signals"]["gap_count"] == 7


def test_a4_figure_table_integrity_green_not_applicable() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {
        "body_spine_quality": "strong",
        "figure_caption_count": 0,
        "matched_figure_count_v2": 0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }
    result = build_quality_indicators(health=health)
    ind = result["quality_indicators"]["figure_table_integrity"]
    assert ind["status"] == "green"
    assert ind["applicability"] == "not_applicable"


def test_a5_figure_table_integrity_red_captions_zero_matched_with_unmatched() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {
        "body_spine_quality": "strong",
        "figure_caption_count": 3,
        "matched_figure_count_v2": 0,
        "media_without_caption_count": 2,
        "caption_without_media_count": 0,
        "unresolved_cluster_count": 0,
        "figure_reader_coverage_ratio": 1.0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }
    result = build_quality_indicators(health=health)
    ind = result["quality_indicators"]["figure_table_integrity"]
    assert ind["status"] == "red"
    assert ind["applicability"] == "applicable"
    assert ind["signals"]["unmatched_asset_count"] == 2


def test_a6_metadata_frontmatter_quality_yellow_title_missing() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {
        "body_spine_quality": "strong",
        "abstract_found": True,
    }
    result = build_quality_indicators(health=health)
    ind = result["quality_indicators"]["metadata_frontmatter_quality"]
    assert ind["status"] == "yellow"
    assert ind["signals"]["title_present"] is False
    assert ind["signals"]["authors_present"] is False


def test_a7_body_reference_structure_uses_health_profile() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    # health_profile key is exactly "health_profile" (no underscore prefix)
    health = {
        "health_profile": "standard",
        "layout_audit_status": "pass",
        "layout_anomaly_count": 0,
        "body_spine_quality": "strong",
        "references_found": True,
        "section_heading_count": 3,
        "reference_item_count": 5,
    }
    result = build_quality_indicators(health=health)
    ind = result["quality_indicators"]["body_reference_structure"]
    assert ind["signals"]["health_profile"] == "standard"
    assert ind["status"] == "green"

    # Verify that _health_profile is NOT read (no such key in our health)
    # Green means all checks passed, meaning "health_profile" was read correctly
    # and no silent fallback to "_health_profile" occurred
    assert "_health_profile" not in health


def test_a8_figure_table_integrity_prefers_inventory_over_health() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    # Health with v2 fields all at zero
    health = {
        "body_spine_quality": "strong",
        "figure_caption_count": 0,
        "matched_figure_count_v2": 0,
        "media_without_caption_count": 0,
        "unresolved_cluster_count": 0,
        "figure_reader_coverage_ratio": 1.0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }

    # Inventory with actual data
    figure_inventory = {
        "matched_figures": [{"id": "fig1"}, {"id": "fig2"}, {"id": "fig3"}],
        "unmatched_assets": [],
        "unresolved_clusters": [],
        "unmatched_legends": [],
        "held_figures": [],
        "figure_legend_completeness": {"accounted_for": 3, "total": 3},
    }

    result = build_quality_indicators(health=health, figure_inventory=figure_inventory)
    ind = result["quality_indicators"]["figure_table_integrity"]
    # Should use inventory: 3 matched figures, not health's 0
    assert ind["signals"]["matched_figure_count"] == 3
    assert ind["status"] == "green"


def test_a9_run_integrity_none_is_empty() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {"body_spine_quality": "strong"}
    result = build_quality_indicators(health=health, run_integrity=None)
    assert result["developer_diagnostics"]["run_integrity"] == {}


def test_a10_run_integrity_dict_preserved() -> None:
    from paperforge.worker.ocr_quality import build_quality_indicators

    health = {"body_spine_quality": "strong"}
    ri = {"pages_processed": 5, "status": "ok"}
    result = build_quality_indicators(health=health, run_integrity=ri)
    assert result["developer_diagnostics"]["run_integrity"] == {"pages_processed": 5, "status": "ok"}


# ── B series: Readiness policy evaluator ──────────────────────────────


def test_b1_default_policy_returns_status_and_score() -> None:
    """Default policy evaluates a healthy report as green."""
    from paperforge.worker.ocr_quality import build_quality_indicators, evaluate_readiness

    health = {
        "rendered_text_gap_count": 0,
        "body_spine_quality": "strong",
        "health_profile": "standard",
        "layout_audit_status": "pass",
        "layout_anomaly_count": 0,
        "references_found": True,
        "section_heading_count": 3,
        "reference_item_count": 5,
        "figure_caption_count": 0,
        "matched_figure_count_v2": 0,
        "media_without_caption_count": 0,
        "unresolved_cluster_count": 0,
        "figure_reader_coverage_ratio": 1.0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }
    base = build_quality_indicators(health=health)
    result = evaluate_readiness(base)

    assert "user_readiness" in result
    assert "recommended_use" in result
    assert result["user_readiness"]["status"] in ("green", "yellow", "red")
    assert result["user_readiness"]["basis"] == "policy_estimate"


def test_b2_hard_red_overrides_green() -> None:
    """gap_count > 10 triggers hard-red rule, forcing status to red."""
    from paperforge.worker.ocr_quality import build_quality_indicators, evaluate_readiness

    health = {
        "rendered_text_gap_count": 15,
        "body_spine_quality": "strong",
        "health_profile": "standard",
        "layout_audit_status": "pass",
        "layout_anomaly_count": 0,
        "references_found": True,
        "section_heading_count": 3,
        "reference_item_count": 5,
        "figure_caption_count": 0,
        "matched_figure_count_v2": 0,
        "media_without_caption_count": 0,
        "unresolved_cluster_count": 0,
        "figure_reader_coverage_ratio": 1.0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }
    base = build_quality_indicators(health=health)
    result = evaluate_readiness(base)

    assert result["user_readiness"]["status"] == "red"
    assert "rendered_text_gap_excessive" in result["user_readiness"]["hard_red_triggers"]


def test_b3_reading_gate_yellow_when_yellow() -> None:
    """Reading gate passes when both required indicators are at least yellow."""
    from paperforge.worker.ocr_quality import build_quality_indicators, evaluate_readiness

    # gap_count 7 → yellow rendered_text_integrity
    # body_spine partial → yellow body_reference_structure
    health = {
        "rendered_text_gap_count": 7,
        "body_spine_quality": "partial",
        "health_profile": "standard",
        "layout_audit_status": "pass",
        "layout_anomaly_count": 1,
        "references_found": True,
        "section_heading_count": 3,
        "reference_item_count": 5,
        "figure_caption_count": 0,
        "matched_figure_count_v2": 0,
        "media_without_caption_count": 0,
        "unresolved_cluster_count": 0,
        "figure_reader_coverage_ratio": 1.0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }
    base = build_quality_indicators(health=health)
    result = evaluate_readiness(base)

    reading = result["recommended_use"].get("reading", {})
    assert reading.get("status") == "ok"


def test_b4_figure_table_reasoning_not_applicable() -> None:
    """figure_table_reasoning returns not_applicable when no figure/table evidence."""
    from paperforge.worker.ocr_quality import build_quality_indicators, evaluate_readiness

    # No figure/table evidence → not_applicable
    health = {
        "rendered_text_gap_count": 0,
        "body_spine_quality": "strong",
        "health_profile": "standard",
        "layout_audit_status": "pass",
        "layout_anomaly_count": 0,
        "references_found": True,
        "section_heading_count": 3,
        "reference_item_count": 5,
        "figure_caption_count": 0,
        "matched_figure_count_v2": 0,
        "media_without_caption_count": 0,
        "unresolved_cluster_count": 0,
        "figure_reader_coverage_ratio": 0.0,
        "table_asset_count": 0,
        "table_unmatched_count": 0,
    }
    base = build_quality_indicators(health=health)
    result = evaluate_readiness(base)

    ftr = result["recommended_use"].get("figure_table_reasoning", {})
    assert ftr.get("status") == "not_applicable"

    # The figure_table_integrity indicator should be excluded from weighted scoring
    # because its applicability is not_applicable
    fig_ind = base["quality_indicators"]["figure_table_integrity"]
    assert fig_ind["applicability"] == "not_applicable"


def test_b5_policy_loaded_from_temp_yaml() -> None:
    """Policy can be loaded from an explicit YAML path."""
    import tempfile
    from pathlib import Path

    import yaml

    from paperforge.worker.ocr_quality import evaluate_readiness

    temp_policy = {
        "schema_version": "custom_v1",
        "weights": {"rendered_text_integrity": 1.0},
        "hard_red": [],
        "use_cases": {},
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(temp_policy, f)
        tmp_path = Path(f.name)

    try:
        base = {"quality_indicators": {}, "developer_diagnostics": {}}
        result = evaluate_readiness(base, policy_path=tmp_path)
        assert result["user_readiness"]["policy_version"] == "custom_v1"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_b6_default_policy_file_exists() -> None:
    """The default policy YAML is bundled with the package."""
    from importlib.resources import files as pkg_files

    policy_path = pkg_files("paperforge") / "policies/ocr_readiness_v1.yaml"
    assert policy_path.exists()
    assert policy_path.is_file()


def test_b7_user_override_merges_correctly() -> None:
    """Deep-merge and list-replace semantics work for user overrides."""
    from paperforge.worker.ocr_quality import load_readiness_policy, evaluate_readiness

    # Override with a custom weight and a replacement hard_red list
    override = {
        "weights": {"rendered_text_integrity": 0.50},
        "hard_red": [{"rule": "custom_rule", "field": "x", "op": "eq", "value": 1}],
    }

    policy = load_readiness_policy(policy=override)

    # Weight should be overridden
    assert policy["weights"]["rendered_text_integrity"] == 0.50
    # Other weights should still exist (dict deep-merge)
    assert "body_reference_structure" in policy["weights"]

    # hard_red list should be replaced, not appended
    assert len(policy["hard_red"]) == 1
    assert policy["hard_red"][0]["rule"] == "custom_rule"

    # Use cases should be preserved
    assert "reading" in policy["use_cases"]

    # Integration: override via evaluate_readiness
    health = {
        "rendered_text_gap_count": 15,
        "body_spine_quality": "strong",
    }
    from paperforge.worker.ocr_quality import build_quality_indicators

    base = build_quality_indicators(health=health)
    result = evaluate_readiness(base, policy=override)
    # With only one dimension weighted 1.0 and no hard_red matching,
    # the score should be high
    assert result["user_readiness"]["policy_version"] == "ocr_readiness_policy_v1"

# ── C series: Contract polish tests ──────────────────────────────


def test_c1_confidence_fallbacks_yellow_when_degraded() -> None:
    """confidence_and_fallbacks returns yellow when degraded_mode_active=True."""
    from paperforge.worker.ocr_quality import _normalize_confidence_fallbacks

    health = {"degraded_mode_active": True, "span_coverage_quality": "good"}
    ind = _normalize_confidence_fallbacks(health)
    assert ind["status"] == "yellow"
    assert ind["evidence"] == ["degraded_mode_active=True", "span_coverage_quality=good", "Degraded mode active"]
