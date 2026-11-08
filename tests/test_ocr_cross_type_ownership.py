"""Cross-type asset claims are decided by caption adjacency, not role labels."""

from __future__ import annotations

from paperforge.worker.ocr_figures import (
    _build_ownership_conflicts,
    resolve_media_asset_conflicts,
)


def _block(bid, page, bbox, role, text="", height=1600):
    return {
        "block_id": bid,
        "page": page,
        "bbox": list(bbox),
        "role": role,
        "text": text,
        "page_height": height,
    }


def _figure(asset_ids=("8",), legend="9", score=0.85):
    return {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "page": 1,
                "legend_block_id": legend,
                "asset_block_ids": list(asset_ids),
                "text": "Figure 1 Photomicrographs",
                "match_score": {"score": score},
            }
        ]
    }


def _table(asset="8", has_asset=True):
    return {
        "tables": [
            {
                "caption_block_id": "2",
                "page": 1,
                "asset_block_id": asset,
                "asset_bbox": [250, 1000, 940, 1370],
                "assistive_text": "",
                "segments": [
                    {"page": 1, "asset_block_id": asset, "asset_bbox": [250, 1000, 940, 1370], "is_continuation": False}
                ],
                "consumed_block_ids": ["2", asset],
                "bridge_block_ids": [asset],
                "has_asset": has_asset,
                "caption_text": "Table 1 Morphometric parameters",
                "match_status": "matched",
                "match_score": {"score": 0.8, "matched_asset_id": asset, "decision": "matched", "evidence": []},
            }
        ]
    }


def _page():
    return [
        _block("2", 1, [100, 170, 500, 220], "table_caption", "Table 1"),
        _block("3", 1, [100, 240, 500, 320], "table_html", "<table><tr><td>Parameter</td></tr></table>"),
        _block("8", 1, [250, 1000, 940, 1370], "figure_asset"),
        _block("9", 1, [110, 1375, 1070, 1460], "figure_caption", "Figure 1"),
    ]


def test_adjacent_figure_keeps_asset_and_table_moves_to_table_asset():
    figures, tables = _figure(), _table()
    resolutions = resolve_media_asset_conflicts(figures, tables, structured=_page())

    assert resolutions and resolutions[0]["winner"] == "figure"
    assert resolutions[0]["table_reassigned_to"] == "3"
    table = tables["tables"][0]
    assert table["asset_block_id"] == "3"
    assert table["asset_bbox"] == [100, 240, 500, 320]
    assert table["has_asset"] is True
    assert table["assistive_text"] == "<table><tr><td>Parameter</td></tr></table>"
    assert table["segments"] == [
        {"page": 1, "asset_block_id": "3", "asset_bbox": [100, 240, 500, 320], "is_continuation": False}
    ]
    assert table["match_score"]["matched_asset_id"] == "3"
    assert table["match_score"]["decision"] == "reassigned_after_conflict"
    assert table["match_score"]["previous_asset_block_id"] == "8"
    assert "3" in {str(block_id) for block_id in table["consumed_block_ids"]}
    assert "8" not in {str(block_id) for block_id in table["consumed_block_ids"]}
    assert "8" not in {str(block_id) for block_id in table["bridge_block_ids"]}
    assert table["render_bbox"] is None
    assert table["asset_switch"]["from"]["asset_block_id"] == "8"
    assert table["asset_switch"]["to"]["asset_block_id"] == "3"
    assert figures["matched_figures"][0]["asset_block_ids"] == ["8"]
    assert _build_ownership_conflicts(figures, tables) == []


def test_table_loses_asset_when_no_table_asset_is_available():
    page = [block for block in _page() if block["block_id"] != "3"]
    figures, tables = _figure(), _table()
    resolutions = resolve_media_asset_conflicts(figures, tables, structured=page)

    assert resolutions and resolutions[0]["table_reassigned_to"] is None
    table = tables["tables"][0]
    assert table["has_asset"] is False
    assert table["asset_block_id"] == ""
    assert table["asset_bbox"] == []
    assert table["segments"] == []
    assert table["render_bbox"] is None
    assert table["match_status"] == "ambiguous"
    assert table["match_score"]["decision"] == "withdrawn_after_conflict"
    assert "8" not in {str(block_id) for block_id in table["consumed_block_ids"]}
    assert figures["matched_figures"][0]["asset_block_ids"] == ["8"]
    withdrawn = [
        conflict
        for conflict in _build_ownership_conflicts(figures, tables)
        if conflict["conflict_type"] == "ownership_withdrawn"
    ]
    assert withdrawn and withdrawn[0]["block_id"] == "8"


def test_ambiguous_adjacency_keeps_the_conflict_unresolved():
    page = _page()
    for block in page:
        if block["block_id"] == "9":
            block["bbox"] = [110, 400, 1070, 480]  # now far from the asset
    figures, tables = _figure(), _table()
    resolutions = resolve_media_asset_conflicts(figures, tables, structured=page)

    assert resolutions == []
    assert len(_build_ownership_conflicts(figures, tables)) == 1


def test_without_blocks_the_old_weak_weak_behaviour_is_kept():
    figures, tables = _figure(), _table()
    assert resolve_media_asset_conflicts(figures, tables) == []
    assert tables["tables"][0]["asset_block_id"] == "8"


def test_strong_asymmetry_is_unchanged():
    figures, tables = _figure(score=0.4), _table()  # figure weak, table explicit+strong
    resolutions = resolve_media_asset_conflicts(figures, tables)
    assert resolutions and resolutions[0]["winner"] == "table"
    assert figures["matched_figures"] == []
