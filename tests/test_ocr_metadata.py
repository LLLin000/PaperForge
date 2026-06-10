from __future__ import annotations

from pathlib import Path


def test_resolved_metadata_prefers_zotero_but_preserves_ocr_candidates() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source_metadata = {
        "zotero_key": "KEY001",
        "title": "Canonical Zotero Title",
        "authors": ["Alice", "Bob"],
        "year": 2024,
        "journal": "Journal A",
        "doi": "10.1000/xyz",
        "source": "zotero_bbt",
    }
    frontmatter_candidates = {
        "title": "Canonical Zotero Title",
        "authors_text": "Alice, Bob, Carol",
        "doi_candidates": ["10.1000/xyz"],
    }

    resolved = resolve_metadata(source_metadata, frontmatter_candidates)

    assert resolved["title"]["value"] == "Canonical Zotero Title"
    assert resolved["title"]["source"] == "zotero"
    assert resolved["authors"]["value"] == ["Alice", "Bob"]
    assert "raw_frontmatter" in resolved


def test_resolved_metadata_has_confidence_scores() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    resolved = resolve_metadata(
        {
            "zotero_key": "KEY002",
            "title": "Z Title",
            "authors": ["A"],
            "year": 2023,
            "doi": "10.1001/abc",
        },
        {},
    )

    assert isinstance(resolved["title"]["confidence"], float)
    assert resolved["title"]["confidence"] > 0.5


def test_resolved_metadata_preserves_alternatives() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    resolved = resolve_metadata(
        {
            "zotero_key": "KEY003",
            "title": "Primary Title",
            "authors": ["Author A"],
            "year": 2022,
            "doi": "10.1002/def",
        },
        {
            "title": "Alternative OCR Title",
            "authors_text": "Author B",
        },
    )

    assert "alternatives" in resolved["title"]
    assert len(resolved["title"]["alternatives"]) >= 1
    assert any(
        alt["source"] == "ocr_frontmatter"
        for alt in resolved["title"]["alternatives"]
    )


def test_legacy_frontmatter_recovers_title_from_first_page(tmp_path: Path) -> None:
    from paperforge.worker.ocr_metadata import extract_frontmatter_candidates
    import json

    blocks_path = tmp_path / "blocks.structured.jsonl"
    blocks_path.write_text(
        json.dumps({"role": "paper_title", "text": "Test Paper Title"}) + "\n"
        + json.dumps({"role": "authors", "text": "Author A, Author B"}) + "\n"
        + json.dumps({"role": "doi", "text": "10.1000/xyz"}) + "\n",
        encoding="utf-8",
    )

    candidates = extract_frontmatter_candidates(blocks_path)
    assert candidates["title"] == "Test Paper Title"
    assert candidates["authors_text"] == "Author A, Author B"
    assert "10.1000/xyz" in candidates.get("doi_candidates", [])


def test_match_author_block_positive() -> None:
    from paperforge.worker.ocr_metadata import _match_author_block_to_source_authors

    result = _match_author_block_to_source_authors(
        "Alice Smith, Bob Jones, Charlie Brown",
        ["Alice Smith", "Bob Jones", "Charlie Brown"],
    )
    assert result["matched"] is True
    assert result["similarity"] > 0.5


def test_match_author_block_negative() -> None:
    from paperforge.worker.ocr_metadata import _match_author_block_to_source_authors

    result = _match_author_block_to_source_authors(
        "In Section 5, the focus is on ES based bioelectronics",
        ["Alice Smith", "Bob Jones"],
    )
    assert result["matched"] is False
    assert result["similarity"] < 0.3


def test_resolve_metadata_author_alignment_mismatch() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source = {"authors": ["Alice Smith", "Bob Jones"]}
    candidates = {"authors_text": "In Section 5, bioelectronics"}
    resolved = resolve_metadata(source, candidates)
    assert resolved["authors"]["source"] == "zotero"
    assert resolved["authors"]["alignment"]["matched"] is False
    assert resolved["authors"]["value"] == ["Alice Smith", "Bob Jones"]


def test_resolve_metadata_author_alignment_match() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source = {"authors": ["Alice Smith", "Bob Jones"]}
    candidates = {"authors_text": "Alice Smith, Bob Jones"}
    resolved = resolve_metadata(source, candidates)
    assert resolved["authors"]["source"] == "zotero"
    assert resolved["authors"]["alignment"]["matched"] is True


def test_resolve_metadata_author_no_zotero_fallback() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source = {}
    candidates = {"authors_text": "Alice Smith, Bob Jones"}
    resolved = resolve_metadata(source, candidates)
    assert resolved["authors"]["source"] == "ocr_frontmatter"
    assert resolved["authors"]["value"] == ["Alice Smith", "Bob Jones"]


def test_title_anchored_from_source_metadata() -> None:
    from paperforge.worker.ocr_metadata import (
        _align_frontmatter_to_source_metadata,
    )

    source_meta = {
        "title": "Correct Research Title That Is Long Enough",
        "authors": ["Alice Smith", "Bob Jones"],
    }
    page1_blocks = [
        {
            "block_id": "p1_b1",
            "block_label": "doc_title",
            "block_content": "Correct Research Title That Is Long Enough",
            "block_bbox": [100, 50, 900, 100],
            "page": 1,
        }
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page1_blocks)
    assert aligned["title"]["source"] == "zotero"
    assert aligned["title"]["value"] == "Correct Research Title That Is Long Enough"
    assert aligned["title"].get("ocr_aligned") is True


def test_author_anchored_from_source_metadata() -> None:
    from paperforge.worker.ocr_metadata import (
        _align_frontmatter_to_source_metadata,
    )

    source_meta = {
        "title": "Some Title",
        "authors": ["Alice Smith", "Bob Jones"],
    }
    page1_blocks = [
        {
            "block_id": "p1_b2",
            "block_label": "text",
            "block_content": "Alice Smith, Bob Jones",
            "block_bbox": [100, 200, 800, 230],
            "page": 1,
        }
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page1_blocks)
    assert aligned["authors"]["source"] == "zotero"
    assert aligned["authors"]["value"] == ["Alice Smith", "Bob Jones"]
    assert aligned["authors"].get("ocr_aligned") is True


def test_mismatched_ocr_title_does_not_pollute_metadata() -> None:
    from paperforge.worker.ocr_metadata import (
        _align_frontmatter_to_source_metadata,
    )

    source_meta = {
        "title": "Correct Zotero Title That Is Real",
        "authors": ["Alice Smith"],
    }
    page1_blocks = [
        {
            "block_id": "p1_b1",
            "block_label": "doc_title",
            "block_content": "Totally Wrong OCR Title That Should Not Be Used",
            "block_bbox": [100, 50, 900, 100],
            "page": 1,
        }
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page1_blocks)
    assert aligned["title"]["value"] == "Correct Zotero Title That Is Real"
    assert aligned["title"]["source"] == "zotero"
    assert aligned["title"].get("ocr_aligned", False) is False


def test_normalize_author_name_strips_superscripts() -> None:
    from paperforge.worker.ocr_metadata import _normalize_author_name

    assert _normalize_author_name("Smith $^{1}") == "Smith"
    assert _normalize_author_name("Ebrahim Esfandiari $^{1}$") == "Ebrahim Esfandiari"


def test_preproof_page_one_does_not_block_page_two_title_localization() -> None:
    from paperforge.worker.ocr_metadata import _align_frontmatter_to_source_metadata

    source_meta = {"title": "Canonical Title", "authors": ["A. Yoo"]}
    page_blocks = [
        {"block_id": "p1_b1", "block_label": "text", "block_content": "Journal Pre-proof", "page": 1},
        {"block_id": "p2_b1", "block_label": "doc_title", "block_content": "Canonical Title", "page": 2},
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page_blocks)

    assert aligned["title"]["source"] == "zotero"
    assert aligned["title"]["value"] == "Canonical Title"
    assert aligned["title"].get("ocr_aligned") is True
    assert aligned["title"].get("ocr_block_id") == "p2_b1"


def test_body_block_outside_frontmatter_window_not_anchored() -> None:
    from paperforge.worker.ocr_metadata import _align_frontmatter_to_source_metadata

    source_meta = {"title": "Cell Biology and Molecular Mechanisms"}
    page_blocks = [
        {"block_id": "p1_b1", "block_content": "Journal Pre-proof", "page": 1},
        {"block_id": "p12_b20", "block_content": "Cell Biology and Molecular Mechanisms are fundamental to understanding", "page": 12},
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page_blocks)

    assert aligned["title"]["value"] == "Cell Biology and Molecular Mechanisms"
    assert aligned["title"]["source"] == "zotero"
    assert aligned["title"].get("ocr_aligned") is not True


def test_source_authors_remain_canonical_with_first_author_ocr() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source = {
        "authors": ["A. Yoo"],
        "first_author": "A. Yoo",
    }
    ocr_blocks = [
        {"block_id": "p1_b1", "role": "authors", "text": "Ami Yoo, Bob Smith, Carol Jones"},
    ]

    resolved = resolve_metadata(source, structured_blocks=ocr_blocks)

    assert resolved["authors"]["value"] == ["A. Yoo"]
    assert resolved["authors"]["source"] == "zotero"


def test_author_localized_within_frontmatter_window() -> None:
    from paperforge.worker.ocr_metadata import _align_frontmatter_to_source_metadata

    source_meta = {"title": "Some Paper", "authors": ["Alice Smith", "Bob Jones"]}
    page_blocks = [
        {"block_id": "p1_b1", "block_content": "Journal Pre-proof", "page": 1},
        {"block_id": "p2_b3", "block_content": "Alice Smith, Bob Jones", "page": 2},
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page_blocks)

    assert aligned["authors"]["source"] == "zotero"
    assert aligned["authors"]["value"] == ["Alice Smith", "Bob Jones"]
    assert aligned["authors"].get("ocr_aligned") is True
    assert aligned["authors"].get("ocr_block_id") == "p2_b3"


def test_author_like_text_outside_window_not_anchored() -> None:
    from paperforge.worker.ocr_metadata import _align_frontmatter_to_source_metadata

    source_meta = {"title": "Some Paper", "authors": ["Alice Smith", "Bob Jones"]}
    page_blocks = [
        {"block_id": "p1_b1", "block_content": "Journal Pre-proof", "page": 1},
        {"block_id": "p15_b42", "block_content": "Alice Smith, Bob Jones, and colleagues have shown that", "page": 15},
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page_blocks)

    assert aligned["authors"]["source"] == "zotero"
    assert aligned["authors"]["value"] == ["Alice Smith", "Bob Jones"]
    assert aligned["authors"].get("ocr_aligned") is not True


def test_live_and_rebuild_metadata_inputs_keep_first_author_fallback_parity() -> None:
    from paperforge.worker.ocr_metadata import resolve_metadata

    source_meta = {
        "first_author": "A. Yoo",
    }
    frontmatter_candidates = {
        "authors_text": None,
    }
    raw_blocks = [
        {"block_id": "p2_b1", "block_content": "Ami Yoo, Bob Smith, Carol Jones", "page": 2},
    ]
    structured_blocks = [
        {"block_id": "p2_b1", "role": "authors", "text": "Ami Yoo, Bob Smith, Carol Jones", "page": 2},
    ]

    live_like = resolve_metadata(
        source_meta,
        frontmatter_candidates,
        page_blocks=raw_blocks,
        structured_blocks=structured_blocks,
    )
    rebuild_like = resolve_metadata(
        source_meta,
        frontmatter_candidates,
        page_blocks=raw_blocks,
        structured_blocks=structured_blocks,
    )

    assert live_like["authors"] == rebuild_like["authors"]
    assert live_like["authors"]["source"] == "ocr_blocks_verified_by_first_author"


def test_build_source_backed_frontmatter_anchors_reports_alignment() -> None:
    from paperforge.worker.ocr_metadata import build_source_backed_frontmatter_anchors

    source_meta = {
        "title": "Canonical Title",
        "authors": ["Alice Smith", "Bob Jones"],
        "doi": "10.1000/test-doi",
    }
    page_blocks = [
        {"block_id": "p1_b1", "block_label": "doc_title", "block_content": "Canonical Title", "page": 1},
        {"block_id": "p1_b2", "block_label": "text", "block_content": "Alice Smith, Bob Jones", "page": 1},
        {"block_id": "p1_b3", "block_label": "text", "block_content": "https://doi.org/10.1000/test-doi", "page": 1},
    ]

    anchors = build_source_backed_frontmatter_anchors(source_meta, page_blocks)

    assert anchors["title_source_anchor"]["status"] == "ACCEPT"
    assert anchors["authors_source_anchor"]["status"] == "ACCEPT"
    assert anchors["doi_source_anchor"]["status"] == "ACCEPT"
