def test_page_qualified_duplicate_legend_ids():
    from paperforge.worker.ocr_figures import build_figure_inventory_vnext

    blocks = [
        {"block_id": 4, "page": 9, "role": "figure_caption", "text": "Figure 4. Page9 caption.", "bbox": [0, 0, 100, 50]},
        {"block_id": 4, "page": 15, "role": "figure_caption", "text": "Figure 4. Page15 caption.", "bbox": [0, 0, 100, 50]},
        {"block_id": "a15", "page": 15, "role": "figure_asset", "raw_label": "image", "bbox": [0, 60, 100, 200]},
    ]
    inv = build_figure_inventory_vnext(blocks, 1200)
    matched = inv.get("matched_figures", [])
    # page-qualified: only page15 legend should match page15 asset
    assert all(m.get("page") != 9 or m.get("legend_block_id") != 4 for m in matched)
