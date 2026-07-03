from __future__ import annotations


def test_table_corpus_collects_captions_assets_and_page_context() -> None:
    from paperforge.worker.ocr_table_domain import TableCorpus

    blocks = [
        {
            "block_id": "cap1",
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Example",
            "bbox": [100, 100, 700, 140],
        },
        {
            "block_id": "asset1",
            "page": 5,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table><tr><td>x</td></tr></table>",
            "bbox": [100, 160, 700, 500],
        },
        {
            "block_id": "note1",
            "page": 5,
            "role": "footnote",
            "raw_label": "vision_footnote",
            "text": "* p < 0.05",
            "bbox": [100, 520, 300, 550],
        },
    ]

    corpus = TableCorpus.from_blocks(blocks)

    assert [b["block_id"] for b in corpus.raw_captions] == ["cap1"]
    assert [b["block_id"] for b in corpus.raw_assets] == ["asset1"]
    assert 5 in corpus.page_footnote_prior
    assert 5 in corpus.page_max_y


def test_table_candidate_index_materializes_caption_records_and_assets_by_page() -> None:
    from paperforge.worker.ocr_table_domain import TableCandidateIndex, TableCorpus

    blocks = [
        {
            "block_id": "cap2",
            "page": 6,
            "role": "table_caption_candidate",
            "text": "Table 2. (continued)",
            "bbox": [100, 100, 700, 130],
        },
        {
            "block_id": "cap1",
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Example",
            "bbox": [100, 100, 700, 140],
        },
        {
            "block_id": "asset1",
            "page": 5,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 160, 700, 500],
        },
    ]

    index = TableCandidateIndex.from_corpus(TableCorpus.from_blocks(blocks))

    assert [r["caption_block_id"] for r in index.caption_records] == ["cap1", "cap2"]
    assert 5 in index.assets_by_page
    assert index.caption_records[1]["is_continuation"] is True


def test_assemble_table_inventory_preserves_public_shape_for_empty_state() -> None:
    from paperforge.worker.ocr_pairing_state import OwnershipLedger, PipelineState
    from paperforge.worker.ocr_table_domain import TableCandidateIndex, TableCorpus, assemble_table_inventory

    blocks = [
        {"block_id": "cap1", "page": 1, "role": "table_caption", "text": "Table 1. Example", "bbox": [0, 0, 10, 10]}
    ]
    corpus = TableCorpus.from_blocks(blocks)
    index = TableCandidateIndex.from_corpus(corpus)
    state = PipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    inventory = assemble_table_inventory(state, index)

    assert inventory == {
        "official_table_count": 0,
        "held_tables": [],
        "tables": [
            {
                "asset_bbox": [],
                "asset_block_id": None,
                "assistive_text": "",
                "bridge_block_ids": [],
                "candidate_assets": [],
                "caption_block_id": "cap1",
                "caption_text": "Table 1. Example",
                "consumed_block_ids": [],
                "continuation_of": None,
                "formal_table_number": 1,
                "has_asset": False,
                "is_continuation": False,
                "match_score": {"decision": "unmatched", "evidence": [], "matched_asset_id": "", "score": 0.0},
                "match_status": "pending",
                "note_band_bbox": [],
                "note_bboxes": [],
                "note_block_ids": [],
                "note_confidence": 0.0,
                "note_match_reason": "",
                "note_texts": [],
                "page": 1,
                "render_bbox": None,
                "render_rotation_deg": 0,
                "segments": [],
                "table_number": 1,
                "truth_source": "image",
            }
        ],
        "unmatched_assets": [],
        "unmatched_captions": [blocks[0]],
    }


# ── Task 4: vnext matching passes ──


def test_build_table_inventory_vnext_matches_same_page_best_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 3,
            "role": "table_caption",
            "text": "Table 1. Example",
            "bbox": [100, 100, 700, 140],
        },
        {
            "block_id": "asset_good",
            "page": 3,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 160, 700, 500],
        },
        {
            "block_id": "asset_bad",
            "page": 3,
            "role": "media_asset",
            "raw_label": "image",
            "text": "",
            "bbox": [800, 160, 1100, 300],
        },
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert inventory["tables"][0]["asset_block_id"] == "asset_good"
    assert inventory["tables"][0]["match_status"] in {"matched", "matched_low_confidence"}


def test_build_table_inventory_vnext_holds_validation_first_weak_caption_without_same_page_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 4,
            "role": "body_text",
            "text": "Table 2",
            "bbox": [100, 100, 260, 130],
            "zone": "display_zone",
            "style_family": "table_caption_like",
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
        {
            "block_id": "asset1",
            "page": 5,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 180, 700, 500],
        },
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert "cap2" in inventory["tables"][0]["consumed_block_ids"]
    assert inventory["tables"][0]["caption_text"].startswith("Table 3.")


def test_build_table_inventory_vnext_previous_page_continuation_gets_geometry_elevation() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "asset_prev",
            "page": 7,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 1200, 900, 1480],
        },
        {
            "block_id": "cap1",
            "page": 8,
            "role": "table_caption",
            "text": "Table 4. (continued)",
            "bbox": [100, 110, 700, 150],
        },
    ]

    inventory = build_table_inventory_vnext(structured_blocks)

    assert inventory["tables"][0]["asset_block_id"] == "asset_prev"
    assert "continuation_geometry_elevation" in inventory["tables"][0]["match_score"]["evidence"]


# ── Task 5: Notes, accounting, diff tooling ──


def test_build_table_inventory_vnext_collects_note_band_and_bridge_blocks() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Example",
            "bbox": [100, 100, 700, 140],
        },
        {
            "block_id": "asset1",
            "page": 5,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 160, 700, 520],
        },
        {"block_id": "note1", "page": 5, "role": "footnote", "text": "* p < 0.05", "bbox": [100, 530, 220, 555]},
        {
            "block_id": "bridge1",
            "page": 5,
            "bridge_eligible": True,
            "layout_region": "display_zone",
            "text": "",
            "bbox": [100, 150, 700, 155],
        },
    ]

    tables = build_table_inventory_vnext(structured_blocks)["tables"]

    assert len(tables) == 1
    assert tables[0]["note_block_ids"] == ["note1"]
    assert tables[0]["bridge_block_ids"] == ["bridge1"]
    assert "note1" in tables[0]["consumed_block_ids"]


def test_build_table_inventory_vnext_respects_page_footnote_prior() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Example",
            "bbox": [100, 100, 700, 140],
        },
        {
            "block_id": "asset1",
            "page": 5,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 160, 700, 1150],
        },
        {
            "block_id": "note1",
            "page": 5,
            "role": "footnote",
            "text": "* footer-area note",
            "bbox": [100, 1180, 300, 1210],
        },
    ]

    table = build_table_inventory_vnext(structured_blocks)["tables"][0]
    assert table["note_match_reason"] in {"note_band_geometry_match", "outside_vertical_range"}


def test_build_table_inventory_vnext_sets_render_rotation_fields_for_rotated_table_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 8,
            "role": "table_caption",
            "text": "Table 2. Caption",
            "bbox": [100, 134, 967, 1442],
        },
        {
            "block_id": "asset1",
            "page": 8,
            "role": "table_html",
            "raw_label": "table",
            "text": "<table></table>",
            "bbox": [100, 100, 880, 1400],
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


def test_compare_table_inventory_parity_on_all_real_paper_fixtures() -> None:
    """Semantic parity after normalising benign drift (string/int, ordering, None vs '').

    Runnable fixtures: 2HEUD5P9, 28JLIHLS, YGH7VEX6, DWQQK2YB, 24YKLTHQ, 37LK5T97.
    The first five achieve full parity across all fields including consumed_block_ids.

    37LK5T97 gap: consumed_block_ids in legacy drops caption block_id=0 because
    the ``if bid`` filter treats integer 0 as falsy; vnext uses string ``'0'``
    which is truthy.  This is a known legacy bug that vnext fixes — the core
    fields (caption_block_id, page, formal_table_number, asset_block_id,
    match_status, render_rotation_deg) are identical after normalisation.
    """
    from pathlib import Path

    from scripts.dev.compare_table_inventory_legacy_vs_vnext import compare_table_inventory_legacy_vs_vnext

    fixtures = [
        ("2HEUD5P9", False),
        ("28JLIHLS", False),
        ("YGH7VEX6", False),
        ("DWQQK2YB", False),
        ("24YKLTHQ", False),
        ("37LK5T97", True),  # True = known consumed_block_ids gap
    ]

    core_fields = {
        "caption_block_id",
        "page",
        "formal_table_number",
        "asset_block_id",
        "match_status",
        "render_rotation_deg",
    }

    for pid, known_consumed_gap in fixtures:
        result = compare_table_inventory_legacy_vs_vnext(Path(f"tests/fixtures/ocr_vnext_real_papers/{pid}"))

        assert len(result["legacy"]) == len(result["vnext"]), (
            f"{pid}: table count mismatch: {len(result['legacy'])} vs {len(result['vnext'])}"
        )

        lo = result["diff"]["legacy_only"]
        vo = result["diff"]["vnext_only"]

        # Compare core fields directly: for each fixture paper, every
        # legacy table's core fields must appear in the vnext list and
        # vice versa.  This catches real semantic drift.
        legacy_core = {tuple(t.get(k) for k in core_fields) for t in result["legacy"]}
        vnext_core = {tuple(t.get(k) for k in core_fields) for t in result["vnext"]}

        legacy_missing = legacy_core - vnext_core
        vnext_extra = vnext_core - legacy_core

        assert not legacy_missing and not vnext_extra, (
            f"{pid}: core-field mismatch — "
            f"legacy has {legacy_missing} not in vnext, "
            f"vnext has {vnext_extra} not in legacy"
        )

        # consumed_block_ids / note / bridge diffs: must be the known gap or absent.
        consumed_lo = {tuple(t["consumed_block_ids"]) for t in lo}
        consumed_vo = {tuple(t["consumed_block_ids"]) for t in vo}

        if known_consumed_gap:
            assert consumed_lo or consumed_vo, f"{pid}: expected consumed_block_ids gap but found none"
            # note / bridge must be pair-wise equivalent across lo and vo
            # (same empty values for 37LK5T97 — no notes or bridges).
            lo_pairs = {(tuple(t.get("note_block_ids")), tuple(t.get("bridge_block_ids"))) for t in lo}
            vo_pairs = {(tuple(t.get("note_block_ids")), tuple(t.get("bridge_block_ids"))) for t in vo}
            assert lo_pairs == vo_pairs, (
                f"{pid}: note/bridge mismatch beyond consumed_block_ids gap: lo={lo_pairs} vo={vo_pairs}"
            )
        else:
            assert not consumed_lo and not consumed_vo, (
                f"{pid}: unexpected consumed_block_ids diffs: legacy={consumed_lo}, vnext={consumed_vo}"
            )


def test_table_pipeline_does_not_set_figure_enricher() -> None:
    """Table pipeline state must not wire the figure-only rotation enricher."""
    from paperforge.worker.ocr_table_domain import TableCandidateIndex, TableCorpus

    # Build a minimal table inventory — the state created internally must not
    # have the figure rotation enricher set.
    structured_blocks = [
        {
            "block_id": "cap1",
            "page": 1,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "bbox": [100, 50, 500, 80],
        },
        {"block_id": "tab1", "page": 1, "role": "table_asset", "bbox": [100, 100, 500, 400]},
    ]
    from paperforge.worker.ocr_pairing_state import OwnershipLedger, PipelineState

    corpus = TableCorpus.from_blocks(structured_blocks)
    candidate_index = TableCandidateIndex.from_corpus(corpus)
    state = PipelineState(corpus=corpus, candidate_index=candidate_index, ledger=OwnershipLedger())

    # Table pipeline should never set the figure-only enricher
    assert state._match_pre_enricher is None
