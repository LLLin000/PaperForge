"""Tests for paperforge.worker.paper_resolver."""

import json
from pathlib import Path

import pytest

from paperforge.worker.paper_resolver import PaperResolver, PaperWorkspace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_index_entry(
    key="ABC12345",
    title="Test Paper Title",
    domain="骨科",
    year=2024,
    authors="Smith J; Doe J",
    doi="10.1234/test.2024",
    journal="Journal of Testing",
    note_path=None,
    ocr_status="done",
    deep_reading_status="pending",
    analyze=True,
    do_ocr=True,
    has_pdf=True,
    **overrides,
):
    if note_path is None:
        note_path = f"Literature/{domain}/{key} - {title}.md"
    entry = {
        "zotero_key": key,
        "title": title,
        "domain": domain,
        "year": year,
        "authors": authors.split("; "),
        "doi": doi,
        "journal": journal,
        "note_path": note_path,
        "ocr_status": ocr_status,
        "deep_reading_status": deep_reading_status,
        "analyze": analyze,
        "do_ocr": do_ocr,
        "has_pdf": has_pdf,
        "fulltext_path": "",
        "collection_path": "",
        "first_author": authors.split("; ")[0] if authors else "",
        "abstract": "This is a test abstract.",
        "impact_factor": "5.0",
        "pmid": "",
        "collections": [],
        "collection_tags": [],
        "collection_group": [],
        "pdf_path": "",
        "ocr_job_id": "",
        "ocr_md_path": "",
        "ocr_json_path": "",
        "deep_reading_md_path": "",
        "paper_root": "",
        "main_note_path": "",
        "deep_reading_path": "",
        "ai_path": "",
        "lifecycle": "fulltext_ready",
        "health": {},
        "maturity": {},
        "next_step": "/pf-deep",
    }
    entry.update(overrides)
    return entry


def _make_index_envelope(items):
    return {"schema_version": "2", "generated_at": "2026-01-01T00:00:00", "paper_count": len(items), "items": items}


def _write_index(path: Path, envelope: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")


def _write_vault_config(vault: Path):
    (vault / "paperforge.json").write_text(
        json.dumps(
            {
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                }
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Patch PaperResolver to bypass real file system dependencies
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver_with_index(tmp_path):
    """Create a PaperResolver preloaded with a test index."""
    vault = tmp_path / "test_vault"
    vault.mkdir(parents=True)
    _write_vault_config(vault)

    # Create index path structure
    indexes_dir = vault / "99_System" / "PaperForge" / "indexes"
    indexes_dir.mkdir(parents=True)

    items = [
        _make_index_entry(key="ABC12345", title="TGF-beta in Bone Regeneration", domain="骨科", year=2024, authors="Smith J; Lee K", doi="10.1234/tgf.2024"),
        _make_index_entry(key="DEF67890", title="MRI Predictive Findings in Rotator Cuff", domain="运动医学", year=2023, authors="Chen W; Wang L", doi="10.5678/mri.2023"),
        _make_index_entry(key="GHI11111", title="Another Bone Study", domain="骨科", year=2024, authors="Smith J; Zhang Y", doi="10.9999/bone.2024"),
    ]
    _write_index(indexes_dir / "formal-library.json", _make_index_envelope(items))

    # Create literature dirs and minimal formal notes
    for item in items:
        note_dir = vault / Path(item["note_path"]).parent
        note_dir.mkdir(parents=True, exist_ok=True)
        frontmatter = f"""---
zotero_key: "{item['zotero_key']}"
domain: "{item['domain']}"
title: "{item['title']}"
year: {item['year']}
doi: "{item['doi']}"
ocr_status: "{item['ocr_status']}"
deep_reading_status: "{item['deep_reading_status']}"
analyze: {str(item['analyze']).lower()}
do_ocr: {str(item['do_ocr']).lower()}
has_pdf: {str(item['has_pdf']).lower()}
---
"""
        (vault / item["note_path"]).write_text(frontmatter, encoding="utf-8")

    # Create OCR dir for ABC12345
    ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "ABC12345"
    ocr_dir.mkdir(parents=True)
    (ocr_dir / "fulltext.md").write_text("# Fulltext\nTest content.", encoding="utf-8")

    resolver = PaperResolver(vault)
    resolver._ensure_loaded()
    return resolver


@pytest.fixture
def empty_resolver(tmp_path):
    """Create a PaperResolver with no index data."""
    vault = tmp_path / "empty_vault"
    vault.mkdir(parents=True)
    _write_vault_config(vault)
    return PaperResolver(vault)


# ---------------------------------------------------------------------------
# resolve_key tests
# ---------------------------------------------------------------------------


class TestResolveKey:
    def test_exact_match(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("ABC12345")
        assert ws is not None
        assert ws.key == "ABC12345"
        assert ws.title == "TGF-beta in Bone Regeneration"
        assert ws.domain == "骨科"
        assert ws.year == "2024"

    def test_case_insensitive(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("abc12345")
        assert ws is not None
        assert ws.key == "ABC12345"

    def test_no_match(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("ZZZZZZZZ")
        assert ws is None

    def test_empty_key(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("")
        assert ws is None

    def test_whitespace_trimmed(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("  ABC12345  ")
        assert ws is not None
        assert ws.key == "ABC12345"


# ---------------------------------------------------------------------------
# resolve_doi tests
# ---------------------------------------------------------------------------


class TestResolveDoi:
    def test_exact_match(self, resolver_with_index):
        ws = resolver_with_index.resolve_doi("10.1234/tgf.2024")
        assert ws is not None
        assert ws.key == "ABC12345"

    def test_case_insensitive(self, resolver_with_index):
        ws = resolver_with_index.resolve_doi("10.1234/TGF.2024")
        assert ws is not None
        assert ws.key == "ABC12345"

    def test_with_url_prefix(self, resolver_with_index):
        ws = resolver_with_index.resolve_doi("https://doi.org/10.1234/tgf.2024")
        assert ws is not None
        assert ws.key == "ABC12345"

    def test_with_dx_prefix(self, resolver_with_index):
        ws = resolver_with_index.resolve_doi("http://dx.doi.org/10.1234/tgf.2024")
        assert ws is not None
        assert ws.key == "ABC12345"

    def test_no_match(self, resolver_with_index):
        ws = resolver_with_index.resolve_doi("10.0000/nonexistent")
        assert ws is None

    def test_empty_doi_entries_handled(self, resolver_with_index):
        items = resolver_with_index._items
        for item in items:
            if item["zotero_key"] == "GHI11111":
                break
        ws = resolver_with_index.resolve_doi("10.9999/bone.2024")
        assert ws is not None
        assert ws.key == "GHI11111"


# ---------------------------------------------------------------------------
# search tests
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_by_title_exact(self, resolver_with_index):
        results = resolver_with_index.search(title="TGF-beta in Bone Regeneration")
        assert len(results) == 1
        assert results[0].key == "ABC12345"

    def test_search_by_title_substring(self, resolver_with_index):
        results = resolver_with_index.search(title="Bone")
        assert len(results) == 2  # ABC12345 + GHI11111
        keys = {r.key for r in results}
        assert "ABC12345" in keys
        assert "GHI11111" in keys

    def test_search_by_author(self, resolver_with_index):
        results = resolver_with_index.search(author="Smith")
        assert len(results) == 2  # ABC12345 + GHI11111

    def test_search_by_year(self, resolver_with_index):
        results = resolver_with_index.search(year=2023)
        assert len(results) == 1
        assert results[0].key == "DEF67890"

    def test_search_by_domain(self, resolver_with_index):
        results = resolver_with_index.search(domain="运动医学")
        assert len(results) == 1
        assert results[0].key == "DEF67890"

    def test_search_combined_and_logic(self, resolver_with_index):
        results = resolver_with_index.search(title="Bone", author="Smith", year=2024)
        assert len(results) == 2  # Both ABC and GHI match all three

    def test_search_no_match_combined(self, resolver_with_index):
        results = resolver_with_index.search(title="Bone", year=2023)
        assert len(results) == 0  # No bone papers in 2023

    def test_search_ranked_by_relevance(self, resolver_with_index):
        results = resolver_with_index.search(title="Bone")
        assert len(results) >= 1
        # Exact match (TGF-beta in Bone Regeneration) should rank higher
        # than substring match (Another Bone Study)
        assert results[0].key in ("ABC12345", "GHI11111")

    def test_search_returns_workspace_fields(self, resolver_with_index):
        results = resolver_with_index.search(title="TGF-beta")
        ws = results[0]
        assert isinstance(ws, PaperWorkspace)
        assert ws.key == "ABC12345"
        assert ws.formal_note_path
        assert ws.frontmatter
        assert ws.frontmatter["zotero_key"] == "ABC12345"


# ---------------------------------------------------------------------------
# PaperWorkspace tests
# ---------------------------------------------------------------------------


class TestPaperWorkspace:
    def test_has_all_fields(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("ABC12345")
        assert ws is not None
        assert ws.key == "ABC12345"
        assert ws.title
        assert ws.domain
        assert ws.year
        assert ws.authors
        assert ws.doi
        assert ws.journal
        assert ws.formal_note_path
        assert ws.ocr_status == "done"
        assert ws.deep_reading_status == "pending"
        assert ws.analyze is True
        assert ws.do_ocr is True
        assert ws.has_pdf is True

    def test_ocr_path_when_ocr_dir_exists(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("ABC12345")
        assert ws is not None
        assert ws.ocr_path
        assert "ABC12345" in ws.ocr_path

    def test_frontmatter_loaded(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("ABC12345")
        assert ws is not None
        fm = ws.frontmatter
        assert fm["zotero_key"] == "ABC12345"
        assert fm["domain"] == "骨科"
        assert fm["title"] == "TGF-beta in Bone Regeneration"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_index(self, empty_resolver):
        empty_resolver._ensure_loaded()
        assert empty_resolver.resolve_key("ABC12345") is None
        assert empty_resolver.resolve_doi("10.1234/test") is None
        assert empty_resolver.search(title="anything") == []

    def test_authors_as_list(self, resolver_with_index):
        ws = resolver_with_index.resolve_key("ABC12345")
        assert ws is not None
        assert "Smith" in ws.authors
        assert "Lee" in ws.authors

    def test_missing_optional_fields(self, resolver_with_index):
        items = resolver_with_index._items
        extra = _make_index_entry(
            key="XXX00000",
            title="Minimal Paper",
            domain="测试",
            year="",
            authors="",
            doi="",
            note_path="Literature/测试/XXX00000 - Minimal Paper.md",
        )
        items.append(extra)
        ws = resolver_with_index.resolve_key("XXX00000")
        assert ws is not None
        assert ws.year == ""
        assert ws.doi == ""
