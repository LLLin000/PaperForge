from __future__ import annotations


def test_table_corpus_collects_captions_assets_and_page_context() -> None:
    from paperforge.worker.ocr_table_domain import TableCorpus

    blocks = [
        {"block_id": "cap1", "page": 5, "role": "table_caption", "text": "Table 1. Example", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset1", "page": 5, "role": "table_html", "raw_label": "table", "text": "<table><tr><td>x</td></tr></table>", "bbox": [100, 160, 700, 500]},
        {"block_id": "note1", "page": 5, "role": "footnote", "raw_label": "vision_footnote", "text": "* p < 0.05", "bbox": [100, 520, 300, 550]},
    ]

    corpus = TableCorpus.from_blocks(blocks)

    assert [b["block_id"] for b in corpus.raw_captions] == ["cap1"]
    assert [b["block_id"] for b in corpus.raw_assets] == ["asset1"]
    assert 5 in corpus.page_footnote_prior
    assert 5 in corpus.page_max_y


def test_table_candidate_index_materializes_caption_records_and_assets_by_page() -> None:
    from paperforge.worker.ocr_table_domain import TableCandidateIndex, TableCorpus

    blocks = [
        {"block_id": "cap2", "page": 6, "role": "table_caption_candidate", "text": "Table 2. (continued)", "bbox": [100, 100, 700, 130]},
        {"block_id": "cap1", "page": 5, "role": "table_caption", "text": "Table 1. Example", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset1", "page": 5, "role": "table_html", "raw_label": "table", "text": "<table></table>", "bbox": [100, 160, 700, 500]},
    ]

    index = TableCandidateIndex.from_corpus(TableCorpus.from_blocks(blocks))

    assert [r["caption_block_id"] for r in index.caption_records] == ["cap1", "cap2"]
    assert 5 in index.assets_by_page
    assert index.caption_records[1]["is_continuation"] is True


def test_assemble_table_inventory_preserves_public_shape_for_empty_state() -> None:
    from paperforge.worker.ocr_pairing_state import OwnershipLedger, PipelineState
    from paperforge.worker.ocr_table_domain import TableCandidateIndex, TableCorpus, assemble_table_inventory

    blocks = [{"block_id": "cap1", "page": 1, "role": "table_caption", "text": "Table 1. Example", "bbox": [0, 0, 10, 10]}]
    corpus = TableCorpus.from_blocks(blocks)
    index = TableCandidateIndex.from_corpus(corpus)
    state = PipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    inventory = assemble_table_inventory(state, index)

    assert inventory == {
        "official_table_count": 0, "held_tables": [],
        "tables": [{
            "asset_bbox": [], "asset_block_id": None, "assistive_text": "",
            "bridge_block_ids": [], "candidate_assets": [],
            "caption_block_id": "cap1", "caption_text": "Table 1. Example",
            "consumed_block_ids": [], "continuation_of": None,
            "formal_table_number": 1, "has_asset": False,
            "is_continuation": False, "match_score": {"decision": "unmatched", "evidence": [], "matched_asset_id": "", "score": 0.0},
            "match_status": "pending", "note_band_bbox": [], "note_bboxes": [],
            "note_block_ids": [], "note_confidence": 0.0, "note_match_reason": "",
            "note_texts": [], "page": 1, "render_bbox": None, "render_rotation_deg": 0,
            "segments": [], "table_number": 1, "truth_source": "image",
        }],
        "unmatched_assets": [], "unmatched_captions": [blocks[0]],
    }


# ── Task 4: vnext matching passes ──


def test_build_table_inventory_vnext_matches_same_page_best_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {"block_id": "cap1", "page": 3, "role": "table_caption", "text": "Table 1. Example", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset_good", "page": 3, "role": "table_html", "raw_label": "table", "text": "<table></table>", "bbox": [100, 160, 700, 500]},
        {"block_id": "asset_bad", "page": 3, "role": "media_asset", "raw_label": "image", "text": "", "bbox": [800, 160, 1100, 300]},
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert inventory["tables"][0]["asset_block_id"] == "asset_good"
    assert inventory["tables"][0]["match_status"] in {"matched", "matched_low_confidence"}


def test_build_table_inventory_vnext_holds_validation_first_weak_caption_without_same_page_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "cap1", "page": 4, "role": "body_text",
            "text": "Table 2", "bbox": [100, 100, 260, 130],
            "zone": "display_zone", "style_family": "table_caption_like",
            "marker_signature": {"type": "table_number"},
        }
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert inventory["tables"] == []
    assert inventory["held_tables"][0]["hold_reason"] == "insufficient_caption_evidence"


def test_build_table_inventory_vnext_materializes_split_caption_continuation() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {"block_id": "cap1", "page": 5, "role": "table_caption", "text": "Table 3.", "bbox": [100, 100, 220, 130]},
        {"block_id": "cap2", "page": 5, "role": "body_text", "text": "Continuation text", "bbox": [100, 132, 700, 170]},
        {"block_id": "asset1", "page": 5, "role": "table_html", "raw_label": "table", "text": "<table></table>", "bbox": [100, 180, 700, 500]},
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert "cap2" in inventory["tables"][0]["consumed_block_ids"]
    assert inventory["tables"][0]["caption_text"].startswith("Table 3.")


def test_build_table_inventory_vnext_previous_page_continuation_gets_geometry_elevation() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {"block_id": "asset_prev", "page": 7, "role": "table_html", "raw_label": "table", "text": "<table></table>", "bbox": [100, 1200, 900, 1480]},
        {"block_id": "cap1", "page": 8, "role": "table_caption", "text": "Table 4. (continued)", "bbox": [100, 110, 700, 150]},
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert inventory["tables"][0]["asset_block_id"] == "asset_prev"
    assert "continuation_geometry_elevation" in inventory["tables"][0]["match_score"]["evidence"]


# ── Task 5: Notes, accounting, diff tooling ──


def test_build_table_inventory_vnext_collects_note_band_and_bridge_blocks() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {"block_id": "cap1", "page": 5, "role": "table_caption", "text": "Table 1. Example", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset1", "page": 5, "role": "table_html", "raw_label": "table", "text": "<table></table>", "bbox": [100, 160, 700, 520]},
        {"block_id": "note1", "page": 5, "role": "footnote", "text": "* p < 0.05", "bbox": [100, 530, 220, 555]},
        {"block_id": "bridge1", "page": 5, "bridge_eligible": True, "layout_region": "display_zone", "text": "", "bbox": [100, 150, 700, 155]},
    ]

    tables = build_table_inventory_vnext(structured_blocks)["tables"]

    assert len(tables) == 1
    assert tables[0]["note_block_ids"] == ["note1"]
    assert tables[0]["bridge_block_ids"] == ["bridge1"]
    assert "note1" in tables[0]["consumed_block_ids"]


def test_build_table_inventory_vnext_respects_page_footnote_prior() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {"block_id": "cap1", "page": 5, "role": "table_caption", "text": "Table 1. Example", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset1", "page": 5, "role": "table_html", "raw_label": "table", "text": "<table></table>", "bbox": [100, 160, 700, 1150]},
        {"block_id": "note1", "page": 5, "role": "footnote", "text": "* footer-area note", "bbox": [100, 1180, 300, 1210]},
    ]

    table = build_table_inventory_vnext(structured_blocks)["tables"][0]
    assert table["note_match_reason"] in {"note_band_geometry_match", "outside_vertical_range"}

def test_build_table_inventory_vnext_sets_render_rotation_fields_for_rotated_table_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {"block_id": "cap1", "page": 8, "role": "table_caption", "text": "Table 2. Caption", "bbox": [100, 134, 967, 1442]},
        {
            "block_id": "asset1", "page": 8, "role": "table_html", "raw_label": "table",
            "text": "<table></table>", "bbox": [100, 100, 880, 1400],
            "span_metadata": [{"dir": [0.0, -1.0], "wmode": 0}],
        },
    ]
    inventory = build_table_inventory_vnext(structured_blocks)
    tables = inventory["tables"]

    assert len(tables) >= 1
    assert tables[0]["render_rotation_deg"] in {0, 270}


def test_compare_table_inventory_legacy_vs_vnext_smoke_fixture() -> None:
    from pathlib import Path
    from scripts.dev.compare_table_inventory_legacy_vs_vnext import compare_table_inventory_legacy_vs_vnext

    result = compare_table_inventory_legacy_vs_vnext(Path("tests/fixtures/ocr_vnext_real_papers/2HEUD5P9"))

    assert "legacy" in result
    assert "vnext" in result
    assert "diff" in result
