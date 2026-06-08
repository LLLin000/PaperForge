"""Contract tests for OCR derived-rebuild orchestration (Phase 4)."""

from __future__ import annotations


def test_rebuild_selector_only_targets_derived_stale_papers() -> None:
    """select_papers_for_derived_rebuild must only return papers
    where derived_stale=True, regardless of raw_upgradable status."""
    # This will fail with ModuleNotFoundError until paperforge/worker/ocr_rebuild.py exists
    from paperforge.worker.ocr_rebuild import select_papers_for_derived_rebuild

    papers = [
        {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
        {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
    ]

    selected = select_papers_for_derived_rebuild(papers)

    assert selected == ["A"]


def test_derived_rebuild_excludes_raw_upgradable_papers() -> None:
    from paperforge.worker.ocr_rebuild import select_papers_for_derived_rebuild

    papers = [
        {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
        {"zotero_key": "B", "derived_stale": True, "raw_upgradable": True},
    ]

    selected = select_papers_for_derived_rebuild(papers)

    assert selected == ["A"]


def test_resolve_source_pdf_fallback_stale_path() -> None:
    from paperforge.worker.ocr_rebuild import _resolve_source_pdf_for_rebuild
    from pathlib import Path

    vault = Path(r"D:\L\OB\Literature-hub")
    meta = {"source_pdf": ""}  # empty path
    result = _resolve_source_pdf_for_rebuild(vault, "SAN9AYVR", meta)
    assert result is not None and result.exists(), f"Fallback failed: {result}"


def test_resolve_source_pdf_stale_missing() -> None:
    from paperforge.worker.ocr_rebuild import _resolve_source_pdf_for_rebuild
    from pathlib import Path

    vault = Path(r"D:\L\OB\Literature-hub")
    meta = {"source_pdf": r"D:\nonexistent\path.pdf"}
    result = _resolve_source_pdf_for_rebuild(vault, "SAN9AYVR", meta)
    assert result is not None and result.exists(), f"Fallback failed for stale key: {result}"


def test_enrich_source_metadata_from_paper_note(monkeypatch, tmp_path) -> None:
    from paperforge.worker import _utils
    from paperforge.worker.ocr_rebuild import _enrich_meta_from_paper_note
    from paperforge.core.io import read_json

    vault = tmp_path / "vault"
    lit_dir = vault / "literature"
    note_dir = lit_dir / "Biology"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "TSCKAVIS.md"
    note_path.write_text(
        """---
zotero_key: TSCKAVIS
title: Metabolic regulation of skeletal cell fate and function in development and disease
authors:
  - Steve Stegen
  - Geert Carmeliet
year: 2022
journal: Nature Reviews Endocrinology
doi: 10.1038/s41574-021-00588-4
---
""",
        encoding="utf-8",
    )

    meta_path = vault / "ocr" / "TSCKAVIS" / "source_metadata.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(_utils, "pipeline_paths", lambda _vault: {"literature": lit_dir, "ocr": vault / "ocr"})

    _enrich_meta_from_paper_note(vault, "TSCKAVIS", meta_path)

    meta = read_json(meta_path)
    assert meta["title"].startswith("Metabolic regulation")
    assert meta["authors"] == ["Steve Stegen", "Geert Carmeliet"]
    assert meta["year"] == 2022
    assert meta["journal"] == "Nature Reviews Endocrinology"
    assert meta["doi"] == "10.1038/s41574-021-00588-4"


def test_enrich_meta_falls_back_to_first_author(monkeypatch, tmp_path) -> None:
    from paperforge.worker import _utils
    from paperforge.worker.ocr_rebuild import _enrich_meta_from_paper_note
    from paperforge.core.io import read_json

    vault = tmp_path / "vault"
    lit_dir = vault / "literature"
    note_dir = lit_dir / "Biology"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "KEY001.md"
    note_path.write_text(
        """---
zotero_key: KEY001
title: A paper with only first author
first_author: W. H. Marks
year: 2023
journal: Journal of Examples
doi: 10.1000/example
---
""",
        encoding="utf-8",
    )

    meta_path = vault / "ocr" / "KEY001" / "source_metadata.json"
    meta_path.parent.mkdir(parents=True)
    meta_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(_utils, "pipeline_paths", lambda _vault: {"literature": lit_dir, "ocr": vault / "ocr"})

    _enrich_meta_from_paper_note(vault, "KEY001", meta_path)

    meta = read_json(meta_path)
    assert meta["authors"] == ["W. H. Marks"]
    assert meta.get("authors_incomplete") is True
    assert meta.get("authors_source") == "paper_note.first_author_fallback"
