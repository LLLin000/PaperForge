"""Contract tests for OCR derived-rebuild orchestration (Phase 4)."""

from __future__ import annotations

from pathlib import Path
from paperforge.worker.ocr_render import RenderOutput



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
    from pathlib import Path

    from paperforge.worker.ocr_rebuild import _resolve_source_pdf_for_rebuild

    vault = Path(r"D:\L\OB\Literature-hub")
    meta = {"source_pdf": ""}  # empty path
    result = _resolve_source_pdf_for_rebuild(vault, "SAN9AYVR", meta)
    assert result is not None and result.exists(), f"Fallback failed: {result}"


def test_resolve_source_pdf_stale_missing() -> None:
    from pathlib import Path

    from paperforge.worker.ocr_rebuild import _resolve_source_pdf_for_rebuild

    vault = Path(r"D:\L\OB\Literature-hub")
    meta = {"source_pdf": r"D:\nonexistent\path.pdf"}
    result = _resolve_source_pdf_for_rebuild(vault, "SAN9AYVR", meta)
    assert result is not None and result.exists(), f"Fallback failed for stale key: {result}"


def test_enrich_source_metadata_from_paper_note(monkeypatch, tmp_path) -> None:
    from paperforge.core.io import read_json
    from paperforge.worker import _utils
    from paperforge.worker.ocr_rebuild import _enrich_meta_from_paper_note

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


def test_run_derived_rebuild_writes_structured_blocks_once(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)

    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps(
            {
                "paper_id": key,
                "page": 1,
                "block_id": "p1_b1",
                "raw_label": "text",
                "raw_order": 0,
                "text": "Example text",
                "bbox": [10, 10, 100, 40],
                "page_width": 600,
                "page_height": 800,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (paper_root / "raw" / "source_metadata.json").write_text(
        json.dumps({"title": "Example Title"}),
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text(json.dumps({"source_pdf": ""}), encoding="utf-8")

    writes = {"count": 0}

    def _counting_write(*args, **kwargs):
        writes["count"] += 1

    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", _counting_write)
    monkeypatch.setattr(
        "paperforge.worker.ocr_metadata.extract_frontmatter_candidates_from_blocks",
        lambda structured: {"title": "Example Title", "authors_text": None, "doi_candidates": []},
    )

    result = run_derived_rebuild_for_keys(tmp_path, [key])


    assert result["rebuild_count"] == 1
    assert writes["count"] == 1


# --- Span-backfill skip contract tests ---


def test_span_backfill_coverage_uses_only_eligible_text_like_blocks() -> None:
    from paperforge.worker.ocr_rebuild import _compute_span_backfill_coverage

    raw_blocks = [
        {"raw_label": "text", "text": "A", "bbox": [0, 0, 10, 10], "span_metadata": [{"size": 10}]},
        {"raw_label": "text", "text": "B", "bbox": [0, 0, 10, 10]},
        {"raw_label": "image", "text": "", "bbox": [0, 0, 10, 10]},
    ]

    covered, eligible, coverage = _compute_span_backfill_coverage(raw_blocks)

    assert covered == 1
    assert eligible == 2
    assert coverage == 0.5


def test_run_derived_rebuild_skips_span_backfill_when_valid(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)

    raw_path = paper_root / "canonical" / "blocks.raw.jsonl"
    raw_path.write_text(
        "\n".join(
            [
                '{"paper_id":"TESTKEY1","page":1,"block_id":"p1_b1","raw_label":"text","raw_order":0,"text":"A","bbox":[0,0,10,10],"page_width":600,"page_height":800,"span_metadata":[{"size":10}]}'
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text(
        '{"source_pdf":"sample.pdf","span_backfill_version":"2026-07-01.1","span_visual_container_version":"2026-06-26.6","span_pdf_fingerprint":"fp-1","span_backfill_coverage":1.0}',
        encoding="utf-8",
    )
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()

    called = {"backfill": 0}
    monkeypatch.setattr("paperforge.worker.ocr_rebuild._resolve_source_pdf_for_rebuild", lambda *args, **kwargs: pdf_path)
    monkeypatch.setattr("paperforge.worker.ocr_artifacts.compute_pdf_fingerprint", lambda path: "fp-1")
    monkeypatch.setattr(
        "paperforge.worker.ocr_pdf_spans.backfill_span_metadata_from_pdf",
        lambda *args, **kwargs: called.__setitem__("backfill", called["backfill"] + 1),
    )

    monkeypatch.setattr("paperforge.worker.ocr_blocks.build_structured_blocks", lambda *args, **kwargs: ([{"page": 1, "block_id": "p1_b1", "role": "body_paragraph", "text": "A"}], {}))
    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_profiles.write_role_span_profiles", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_metadata.extract_frontmatter_candidates", lambda path: {"title": "Example Title", "authors_text": None, "doi_candidates": []})
    monkeypatch.setattr("paperforge.worker.ocr_metadata.resolve_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_metadata.write_resolved_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_figures.build_figure_inventory", lambda *args, **kwargs: {"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []})
    monkeypatch.setattr("paperforge.worker.ocr_figures.write_back_figure_roles", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_figures.write_figure_inventory", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_figure_reader.synthesize_reader_figures", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_tables.build_table_inventory", lambda *args, **kwargs: {"tables": [], "unmatched_assets": []})
    monkeypatch.setattr("paperforge.worker.ocr_tables.write_back_table_roles", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_tables.write_table_inventory", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_render.render_fulltext_markdown", lambda *args, **kwargs: RenderOutput(markdown="", heading_events=[], emitted_block_events=[]))
    monkeypatch.setattr("paperforge.worker.ocr_render.write_render_outputs", lambda *args, meta=None, **kwargs: dict(meta) if meta else {})
    monkeypatch.setattr("paperforge.worker.ocr_health.build_ocr_health", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_health.build_ocr_raw_integrity_health", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_health.write_ocr_health", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_decisions.collect_decisions", lambda *args, **kwargs: [])
    monkeypatch.setattr("paperforge.worker.ocr_decisions.write_decision_log", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_index.build_role_indexes", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_index.write_role_index", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr.validate_ocr_meta", lambda *args, **kwargs: ("done", ""))

    result = run_derived_rebuild_for_keys(tmp_path, [key])

    assert result["rebuild_count"] == 1
    assert called["backfill"] == 0


def test_run_derived_rebuild_records_unavailable_pdf_missing_without_rerun(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "meta.json").write_text('{"span_backfill_version":"2026-07-01.1"}', encoding="utf-8")
    (paper_root / "canonical" / "blocks.raw.jsonl").write_text('{"paper_id":"TESTKEY1","page":1,"block_id":"p1_b1","raw_label":"text","raw_order":0,"text":"A","bbox":[0,0,10,10],"page_width":600,"page_height":800,"span_metadata":[{"size":10}]}\n', encoding="utf-8")
    (paper_root / "raw" / "source_metadata.json").write_text('{"title":"Example Title"}', encoding="utf-8")

    called = {"backfill": 0}
    monkeypatch.setattr("paperforge.worker.ocr_rebuild._resolve_source_pdf_for_rebuild", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "paperforge.worker.ocr_pdf_spans.backfill_span_metadata_from_pdf",
        lambda *args, **kwargs: called.__setitem__("backfill", called["backfill"] + 1),
    )

    monkeypatch.setattr("paperforge.worker.ocr_blocks.build_structured_blocks", lambda *args, **kwargs: ([{"page": 1, "block_id": "p1_b1", "role": "body_paragraph", "text": "A"}], {}))
    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_profiles.write_role_span_profiles", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_metadata.extract_frontmatter_candidates", lambda path: {"title": "Example Title", "authors_text": None, "doi_candidates": []})
    monkeypatch.setattr("paperforge.worker.ocr_metadata.resolve_metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_metadata.write_resolved_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_figures.build_figure_inventory", lambda *args, **kwargs: {"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []})
    monkeypatch.setattr("paperforge.worker.ocr_figures.write_back_figure_roles", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_figures.write_figure_inventory", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_figure_reader.synthesize_reader_figures", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_tables.build_table_inventory", lambda *args, **kwargs: {"tables": [], "unmatched_assets": []})
    monkeypatch.setattr("paperforge.worker.ocr_tables.write_back_table_roles", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_tables.write_table_inventory", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_render.render_fulltext_markdown", lambda *args, **kwargs: RenderOutput(markdown="", heading_events=[], emitted_block_events=[]))
    monkeypatch.setattr("paperforge.worker.ocr_render.write_render_outputs", lambda *args, meta=None, **kwargs: dict(meta) if meta else {})
    monkeypatch.setattr("paperforge.worker.ocr_health.build_ocr_health", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_health.build_ocr_raw_integrity_health", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_health.write_ocr_health", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_decisions.collect_decisions", lambda *args, **kwargs: [])
    monkeypatch.setattr("paperforge.worker.ocr_decisions.write_decision_log", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_index.build_role_indexes", lambda *args, **kwargs: {})
    monkeypatch.setattr("paperforge.worker.ocr_index.write_role_index", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr.validate_ocr_meta", lambda *args, **kwargs: ("done", ""))

    result = run_derived_rebuild_for_keys(tmp_path, [key])

    assert result["rebuild_count"] == 1
    assert called["backfill"] == 0
    meta = json.loads((paper_root / "meta.json").read_text(encoding="utf-8"))
    assert meta["span_backfill_status"] == "unavailable_pdf_missing"
    assert meta["span_backfill_eligible_count"] == 1
    assert meta["span_backfill_covered_count"] == 1


def test_run_derived_rebuild_does_not_skip_when_current_fingerprint_is_unknown() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-07-01.1",
        "span_visual_container_version": "2026-06-26.6",
        "span_pdf_fingerprint": "unknown",
        "span_backfill_coverage": 1.0,
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="unknown", coverage=1.0) is False


def test_span_backfill_invalid_when_version_mismatch() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "old",
        "span_visual_container_version": "2026-06-26.6",
        "span_pdf_fingerprint": "fp-1",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-1", coverage=1.0) is False


def test_span_backfill_invalid_when_visual_container_version_mismatch() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-07-01.1",
        "span_visual_container_version": "old",
        "span_pdf_fingerprint": "fp-1",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-1", coverage=1.0) is False


def test_span_backfill_invalid_when_fingerprint_mismatch() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-07-01.1",
        "span_visual_container_version": "2026-06-26.6",
        "span_pdf_fingerprint": "fp-old",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-new", coverage=1.0) is False


def test_span_backfill_invalid_when_coverage_below_threshold() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-07-01.1",
        "span_visual_container_version": "2026-06-26.6",
        "span_pdf_fingerprint": "fp-1",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-1", coverage=0.2) is False


def test_span_backfill_does_not_update_validity_fields_when_raw_write_fails(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()

    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        '{"paper_id":"TESTKEY1","page":1,"block_id":"p1_b1","raw_label":"text","raw_order":0,"text":"A","bbox":[0,0,10,10],"page_width":600,"page_height":800}\n',
        encoding="utf-8",
    )
    (paper_root / "raw" / "source_metadata.json").write_text('{"title":"Example Title"}', encoding="utf-8")
    (paper_root / "meta.json").write_text('{"source_pdf":"sample.pdf"}', encoding="utf-8")

    monkeypatch.setattr("paperforge.worker.ocr_rebuild._resolve_source_pdf_for_rebuild", lambda *args, **kwargs: pdf_path)
    monkeypatch.setattr("paperforge.worker.ocr_artifacts.compute_pdf_fingerprint", lambda path: "fp-1")
    monkeypatch.setattr(
        "paperforge.worker.ocr_pdf_spans.backfill_span_metadata_from_pdf",
        lambda blocks, pdf: blocks[0].update({"span_metadata": [{"size": 10}]}) or blocks,
    )
    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_raw_blocks_jsonl", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("write failed")))

    try:
        run_derived_rebuild_for_keys(tmp_path, [key])
    except RuntimeError:
        pass

    meta = json.loads((paper_root / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("span_backfill_version") in (None, "")
    assert meta.get("span_backfill_status") not in {"rerun_success", "skipped_valid"}


def test_enrich_meta_falls_back_to_first_author(monkeypatch, tmp_path) -> None:
    from paperforge.core.io import read_json
    from paperforge.worker import _utils
    from paperforge.worker.ocr_rebuild import _enrich_meta_from_paper_note

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


# ── Plan A: rebuild compatibility proof (pairing framework) ──


def test_run_derived_rebuild_for_keys_still_uses_public_build_figure_inventory(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)

    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps(
            {
                "paper_id": key,
                "page": 1,
                "block_id": "p1_b1",
                "raw_label": "text",
                "raw_order": 0,
                "text": "Example text",
                "bbox": [10, 10, 100, 40],
                "page_width": 600,
                "page_height": 800,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (paper_root / "raw" / "source_metadata.json").write_text(
        json.dumps({"title": "Example Title"}),
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text(json.dumps({"source_pdf": ""}), encoding="utf-8")

    called = {"count": 0}

    def fake_build_figure_inventory(structured_blocks, page_width=1200, page_pdf_lines_by_page=None):
        called["count"] += 1
        return {
            "pipeline_mode": "vnext",
            "matched_figures": [],
            "ambiguous_figures": [],
            "unmatched_legends": [],
            "unmatched_assets": [],
            "unresolved_clusters": [],
            "held_figures": [],
            "rejected_legends": [],
            "page_ledger": {},
            "residual_ledger": {},
            "local_pairing_hypotheses": [],
            "pass_reports": [],
            "completeness": {"total_numbered_legends": 0, "accounted_for": 0, "details": []},
        }

    monkeypatch.setattr("paperforge.worker.ocr_figures.build_figure_inventory", fake_build_figure_inventory)
    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "paperforge.worker.ocr_metadata.extract_frontmatter_candidates_from_blocks",
        lambda structured: {"title": "Example Title", "authors_text": None, "doi_candidates": []},
    )

    result = run_derived_rebuild_for_keys(tmp_path, [key])

    assert result["rebuild_count"] == 1
    assert called["count"] > 0


def test_run_derived_rebuild_for_keys_still_uses_public_build_table_inventory(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)

    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps({"paper_id": key, "page": 1, "block_id": "p1_b1", "raw_label": "text", "raw_order": 0, "text": "text", "bbox": [10, 10, 100, 40], "page_width": 600, "page_height": 800}) + "\n", encoding="utf-8"
    )
    (paper_root / "raw" / "source_metadata.json").write_text(json.dumps({"title": "Example Title"}), encoding="utf-8")
    (paper_root / "meta.json").write_text(json.dumps({"source_pdf": ""}), encoding="utf-8")

    called = {"count": 0}

    def fake_build_table_inventory(structured_blocks):
        called["count"] += 1
        return {"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": [], "official_table_count": 0}

    monkeypatch.setattr("paperforge.worker.ocr_tables.build_table_inventory", fake_build_table_inventory)
    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_metadata.extract_frontmatter_candidates_from_blocks", lambda s: {"title": "Example Title", "authors_text": None, "doi_candidates": []})
    monkeypatch.setattr("paperforge.worker.ocr_figures.build_figure_inventory", lambda *a, **kw: {"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []})
    monkeypatch.setattr("paperforge.worker.ocr_figures.write_back_figure_roles", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_figures.write_figure_inventory", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_figure_reader.synthesize_reader_figures", lambda *a, **kw: {})
    monkeypatch.setattr("paperforge.worker.ocr_tables.write_back_table_roles", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_tables.write_table_inventory", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_render.render_fulltext_markdown", lambda *a, **kw: RenderOutput(markdown="", heading_events=[], emitted_block_events=[]))
    monkeypatch.setattr("paperforge.worker.ocr_render.write_render_outputs", lambda *a, meta=None, **kw: dict(meta) if meta else {})
    monkeypatch.setattr("paperforge.worker.ocr_health.build_ocr_health", lambda *a, **kw: {})
    monkeypatch.setattr("paperforge.worker.ocr_health.build_ocr_raw_integrity_health", lambda *a, **kw: {})
    monkeypatch.setattr("paperforge.worker.ocr_health.write_ocr_health", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_decisions.collect_decisions", lambda *a, **kw: [])
    monkeypatch.setattr("paperforge.worker.ocr_decisions.write_decision_log", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr_index.build_role_indexes", lambda *a, **kw: {})
    monkeypatch.setattr("paperforge.worker.ocr_index.write_role_index", lambda *a, **kw: None)
    monkeypatch.setattr("paperforge.worker.ocr.validate_ocr_meta", lambda *a, **kw: ("done", ""))

    result = run_derived_rebuild_for_keys(tmp_path, [key])

    assert result["rebuild_count"] == 1
    assert called["count"] > 0

# ── Derived-rebuild backup & provenance tests ──


def _seed_rebuild_paper(tmp_path: Path, key: str) -> Path:
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "raw" / "source_metadata.json").write_text('{"title": "Example Title"}', encoding="utf-8")
    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        '{"paper_id":"TESTKEY1","page":1,"block_id":"p1_b1","raw_label":"text","raw_order":0,"text":"A","bbox":[0,0,10,10],"page_width":600,"page_height":800,"span_metadata":[{"size":10}]}\n',
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text('{"source_pdf":"","ocr_status":"done"}', encoding="utf-8")
    return paper_root


def test_run_derived_rebuild_creates_backup_before_replace(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = _seed_rebuild_paper(tmp_path, key)
    (paper_root / "fulltext.md").write_text("annotated\n", encoding="utf-8")
    result = run_derived_rebuild_for_keys(tmp_path, [key])
    assert result["rebuild_count"] == 1
    backups = sorted((paper_root / "backups").glob("fulltext.pre-rebuild.*.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "annotated\n"


def test_run_derived_rebuild_increments_rebuild_count_and_hash(tmp_path: Path, monkeypatch) -> None:
    import json
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = _seed_rebuild_paper(tmp_path, key)
    (paper_root / "fulltext.md").write_text("annotated\n", encoding="utf-8")
    (paper_root / "meta.json").write_text('{"rebuild_count": 1}', encoding="utf-8")
    run_derived_rebuild_for_keys(tmp_path, [key])
    meta = json.loads((paper_root / "meta.json").read_text(encoding="utf-8"))
    assert meta["rebuild_count"] == 2
    assert meta["machine_fulltext_hash"].startswith("sha256:")
    assert meta["last_backup_path"].startswith("backups/fulltext.pre-rebuild.")
