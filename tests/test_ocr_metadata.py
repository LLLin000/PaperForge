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
