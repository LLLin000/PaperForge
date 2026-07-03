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
    from paperforge.worker.ocr_table_domain import (
        TableCandidateIndex,
        TableCorpus,
        assemble_table_inventory,
    )

    blocks = [
        {
            "block_id": "cap1",
            "page": 1,
            "role": "table_caption",
            "text": "Table 1. Example",
            "bbox": [0, 0, 10, 10],
        }
    ]
    corpus = TableCorpus.from_blocks(blocks)
    index = TableCandidateIndex.from_corpus(corpus)
    state = PipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    inventory = assemble_table_inventory(state, index)

    assert inventory == {
        "tables": [],
        "held_tables": [],
        "unmatched_captions": [blocks[0]],
        "unmatched_assets": [],
        "official_table_count": 0,
    }
