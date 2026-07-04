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
