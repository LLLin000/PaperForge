from __future__ import annotations


def test_role_index_separates_body_caption_table_metadata_reference() -> None:
    from paperforge.worker.ocr_index import build_role_indexes

    structured_blocks = [
        {"paper_id": "KEY001", "page": 1, "block_id": "b1", "role": "body_paragraph", "text": "Methods body"},
        {"paper_id": "KEY001", "page": 1, "block_id": "b2", "role": "figure_caption", "text": "Figure 1. Result"},
        {"paper_id": "KEY001", "page": 1, "block_id": "b3", "role": "table_caption", "text": "Table 1. Data"},
        {"paper_id": "KEY001", "page": 1, "block_id": "b4", "role": "reference_item", "text": "Smith et al. (2024)."},
    ]
    resolved_metadata = {
        "title": {"value": "Paper Title"},
        "doi": {"value": "10.1000/xyz"},
    }

    indexes = build_role_indexes(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
    )

    assert "body" in indexes
    assert "captions" in indexes
    assert "tables" in indexes
    assert "metadata" in indexes
    assert "references" in indexes
