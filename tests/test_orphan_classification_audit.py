from __future__ import annotations

from scripts.dev.orphan_classification_audit import CLASSES, classify_assets


def test_classifies_each_unmatched_asset_category() -> None:
    inventory = {
        "page_dimensions_by_page": {str(page): [1000, 1000] for page in range(1, 6)},
        "matched_figures": [
            {"figure_id": "figure_001", "page": 1, "bbox": [100, 100, 500, 500],
             "matched_assets": []},
            {"figure_id": "figure_002", "page": 2, "bbox": [700, 700, 900, 900],
             "matched_assets": [{"page": 2, "bbox": [100, 100, 400, 400]}]},
        ],
        "unmatched_assets": [
            {"block_id": "panel", "page": 1, "bbox": [150, 150, 250, 250]},
            {"block_id": "duplicate", "page": 2, "bbox": [100, 100, 400, 400]},
            {"block_id": "decoration", "page": 3, "bbox": [300, 300, 350, 350]},
            {"block_id": "true", "page": 4, "bbox": [300, 300, 500, 500]},
            {"block_id": "unknown", "page": 5, "bbox": [300, 300, 420, 420]},
        ],
    }

    result = classify_assets(inventory, [])

    assert {item["classification"] for item in result} == set(CLASSES)
    assert {item["block_id"]: item["classification"] for item in result} == {
        "panel": "panel_sub_asset",
        "duplicate": "duplicate_asset",
        "decoration": "decoration",
        "true": "true_unmatched_figure",
        "unknown": "undetermined",
    }


def test_delivery_totals_distinguish_stale_files_and_missing_embeds(tmp_path) -> None:
    import json
    from scripts.dev.orphan_classification_audit import audit_corpus

    paper = tmp_path / "PAPER1"
    (paper / "structure").mkdir(parents=True)
    (paper / "render" / "figures").mkdir(parents=True)
    (paper / "structure" / "figure_inventory.json").write_text(
        json.dumps({"matched_figures": [
            {"figure_id": "figure_001", "page": 1, "matched_assets": [{"block_id": "a", "page": 1}]},
            {"figure_id": "figure_002", "page": 2},
        ]}), encoding="utf-8"
    )
    (paper / "render" / "figures" / "figure_001.md").write_text("figure", encoding="utf-8")
    (paper / "render" / "figures" / "figure_003.md").write_text("stale", encoding="utf-8")
    (paper / "fulltext.md").write_text("", encoding="utf-8")

    result = audit_corpus(tmp_path)

    assert result["totals"]["inventory_ids_without_embed"] == 2
    assert result["totals"]["asset_bearing_without_embed"] == 1
    assert result["totals"]["asset_bearing_delivery_violations"] == 1
    assert result["totals"]["canonical_md_never_embedded"] == 2
    assert result["totals"]["stale_canonical_md"] == 1
    assert result["asset_bearing_undelivered"][0]["reconciliation_type"] == "missing_embed_for_asset_object"
