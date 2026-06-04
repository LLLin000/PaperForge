from __future__ import annotations


def test_build_structured_blocks_preserves_noise_and_confidence() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "header",
            "raw_order": 0,
            "bbox": [1, 2, 3, 4],
            "text": "Header",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows = build_structured_blocks(raw_blocks)

    assert rows[0]["role"] in {"noise", "page_header"}
    assert "role_confidence" in rows[0]
    assert "evidence" in rows[0]


def test_build_raw_blocks_preserves_every_block() -> None:
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_page

    result = {
        "prunedResult": {
            "width": 1200,
            "height": 1600,
            "parsing_res_list": [
                {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [1, 2, 3, 4], "block_content": "A"},
                {"block_id": 2, "block_label": "header", "block_order": 1, "block_bbox": [5, 6, 7, 8], "block_content": "B"},
            ],
        }
    }

    rows = build_raw_blocks_for_page("KEY001", 1, result)

    assert len(rows) == 2
    assert rows[0]["paper_id"] == "KEY001"
    assert rows[1]["raw_label"] == "header"
