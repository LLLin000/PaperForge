from __future__ import annotations

from paperforge.worker.ocr_figures import build_figure_inventory_legacy, build_figure_inventory_vnext
from scripts.dev.compare_figure_inventory_legacy_vs_vnext import compare_inventories


def test_compare_inventories_reports_counts_for_same_page_case():
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    legacy = build_figure_inventory_legacy(blocks, 1200)
    vnext = build_figure_inventory_vnext(blocks, 1200)
    diff = compare_inventories(legacy, vnext)

    assert diff["vnext_matched_count"] >= 1
    assert "vnext_consumed_block_ids" in diff

def test_compare_inventories_now_includes_gate_fields():
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    legacy = build_figure_inventory_legacy(blocks, 1200)
    vnext = build_figure_inventory_vnext(blocks, 1200)
    diff = compare_inventories(legacy, vnext)

    assert "legacy_completeness" in diff
    assert "vnext_completeness" in diff
    assert "legacy_figure_ids" in diff
    assert "vnext_figure_ids" in diff
    assert "vnext_pass_names" in diff
    assert "legacy_settlement_types" in diff
    assert "vnext_settlement_types" in diff
    assert "consumed_ids_only_in_legacy" in diff
    assert "consumed_ids_only_in_vnext" in diff
