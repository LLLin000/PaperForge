# Derived Rebuild Span Backfill Skip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow derived rebuild to skip PDF span backfill only when existing raw enrichment is still valid under an explicit version/fingerprint/coverage contract.

**Architecture:** Keep the policy local to rebuild orchestration. Add explicit span-validity helpers around `run_derived_rebuild_for_keys()`, reuse the existing `compute_pdf_fingerprint()` seam, define coverage over eligible text-like raw blocks, persist explicit `span_*` status fields in `meta.json`, and prove the contract with focused rebuild tests.

**Tech Stack:** Python 3.10+, existing PaperForge worker modules, PyMuPDF (`fitz`) only through existing fingerprint/backfill helpers, pytest.

---

## File Structure

- Modify: `paperforge/worker/ocr_rebuild.py`
  Purpose: evaluate span-backfill skip validity, decide skip/rerun, and persist `span_*` status fields.
- Modify: `paperforge/worker/ocr_artifacts.py` or `paperforge/worker/ocr_rebuild.py`
  Purpose: reuse the existing `compute_pdf_fingerprint()` seam where rebuild can access it directly.
- Modify: `tests/test_ocr_rebuild.py`
  Purpose: lock down skip/rerun behavior, coverage denominator, PDF-missing handling, and metadata write ordering.
- Modify: `PROJECT-MANAGEMENT.md`
  Purpose: record the policy fix and test coverage.

## Task 1: Add Rebuild Tests for the Span-Skip Contract

**Files:**
- Modify: `tests/test_ocr_rebuild.py`
- Test: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Write the failing eligible-coverage test**

Add a unit-style rebuild helper test that proves coverage ignores non-text raw blocks:

```python
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
```

- [ ] **Step 2: Run the eligible-coverage test to verify it fails correctly**

Run: `pytest tests/test_ocr_rebuild.py::test_span_backfill_coverage_uses_only_eligible_text_like_blocks -v`

Expected: FAIL because `_compute_span_backfill_coverage` does not exist yet.

- [ ] **Step 3: Write the failing skip-when-valid rebuild test**

Add a focused orchestration test that monkeypatches the expensive seams and proves valid stored enrichment skips backfill:

```python
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
    (paper_root / "raw" / "source_metadata.json").write_text('{"title":"Example Title"}', encoding="utf-8")
    (paper_root / "meta.json").write_text(
        '{"source_pdf":"sample.pdf","span_backfill_version":"2026-06-22.1","span_visual_container_version":"2026-06-22.1","span_pdf_fingerprint":"fp-1","span_backfill_coverage":1.0}',
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
    monkeypatch.setattr("paperforge.worker.ocr_objects.extract_and_write_objects", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_render.render_fulltext_markdown", lambda *args, **kwargs: "")
    monkeypatch.setattr("paperforge.worker.ocr_render.write_render_outputs", lambda *args, **kwargs: None)
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
```

- [ ] **Step 4: Run the skip-when-valid test to verify it fails correctly**

Run: `pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_skips_span_backfill_when_valid -v`

Expected: FAIL because rebuild currently always reruns span backfill.

- [ ] **Step 5: Write the PDF-missing status test**

Add a focused rebuild test:

```python
def test_run_derived_rebuild_records_unavailable_pdf_missing_without_rerun(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "meta.json").write_text('{"span_backfill_version":"2026-06-22.1"}', encoding="utf-8")
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
    monkeypatch.setattr("paperforge.worker.ocr_objects.extract_and_write_objects", lambda *args, **kwargs: None)
    monkeypatch.setattr("paperforge.worker.ocr_render.render_fulltext_markdown", lambda *args, **kwargs: "")
    monkeypatch.setattr("paperforge.worker.ocr_render.write_render_outputs", lambda *args, **kwargs: None)
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
```

- [ ] **Step 6: Run the PDF-missing status test to verify it fails correctly**

Run: `pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_records_unavailable_pdf_missing_without_rerun -v`

Expected: FAIL because the explicit unavailable status path does not exist yet.

- [ ] **Step 7: Write the unknown-fingerprint invalidation test**

Add this test:

```python
def test_run_derived_rebuild_does_not_skip_when_current_fingerprint_is_unknown(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-06-22.1",
        "span_visual_container_version": "2026-06-22.1",
        "span_pdf_fingerprint": "unknown",
        "span_backfill_coverage": 1.0,
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="unknown", coverage=1.0) is False
```

- [ ] **Step 8: Run the unknown-fingerprint test to verify it fails correctly**

Run: `pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_does_not_skip_when_current_fingerprint_is_unknown -v`

Expected: FAIL because the validity helper does not exist yet.

- [ ] **Step 9: Write the mismatch and write-order tests**

Add these helper-level invalidation tests:

```python
def test_span_backfill_invalid_when_version_mismatch() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "old",
        "span_visual_container_version": "2026-06-22.1",
        "span_pdf_fingerprint": "fp-1",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-1", coverage=1.0) is False


def test_span_backfill_invalid_when_visual_container_version_mismatch() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-06-22.1",
        "span_visual_container_version": "old",
        "span_pdf_fingerprint": "fp-1",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-1", coverage=1.0) is False


def test_span_backfill_invalid_when_fingerprint_mismatch() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-06-22.1",
        "span_visual_container_version": "2026-06-22.1",
        "span_pdf_fingerprint": "fp-old",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-new", coverage=1.0) is False


def test_span_backfill_invalid_when_coverage_below_threshold() -> None:
    from paperforge.worker.ocr_rebuild import _span_backfill_is_valid

    meta = {
        "span_backfill_version": "2026-06-22.1",
        "span_visual_container_version": "2026-06-22.1",
        "span_pdf_fingerprint": "fp-1",
    }

    assert _span_backfill_is_valid(meta, current_pdf_fingerprint="fp-1", coverage=0.2) is False
```

Add this write-order orchestration test:

```python
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
```

- [ ] **Step 10: Run the mismatch and write-order tests to verify they fail correctly**

Run:

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_version_mismatch -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_visual_container_version_mismatch -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_fingerprint_mismatch -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_coverage_below_threshold -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_does_not_update_validity_fields_when_raw_write_fails -v`

Expected: FAIL because the validity helper and write-order contract do not exist yet.

- [ ] **Step 11: Run the focused rebuild test file baseline**

Run: `pytest tests/test_ocr_rebuild.py -v`

Expected: the new skip-contract tests fail; existing rebuild tests continue to pass, except for pre-existing environment-dependent absolute-path tests if they are not runnable outside the author's machine.

## Task 2: Implement the Span-Skip Validity Helpers in Rebuild

**Files:**
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Add module-level constants for version and threshold**

Add these near the top of `paperforge/worker/ocr_rebuild.py`:

```python
CURRENT_SPAN_BACKFILL_VERSION = "2026-06-22.1"
CURRENT_SPAN_VISUAL_CONTAINER_VERSION = "2026-06-22.1"
MIN_SPAN_BACKFILL_COVERAGE = 0.90
```

- [ ] **Step 2: Add the eligible-text-like raw-block helper**

Implement:

```python
def _is_text_like_raw_block(block: dict) -> bool:
    raw_label = str(block.get("raw_label") or "")
    text = str(block.get("text") or "").strip()
    bbox = block.get("bbox") or []
    return raw_label in {"text", "paragraph_title", "abstract", "reference_content", "figure_title"} and bool(text) and len(bbox) >= 4
```

- [ ] **Step 3: Add the coverage helper**

Implement:

```python
def _compute_span_backfill_coverage(raw_blocks: list[dict]) -> tuple[int, int, float]:
    eligible = [block for block in raw_blocks if _is_text_like_raw_block(block)]
    eligible_count = len(eligible)
    if eligible_count == 0:
        return 0, 0, 1.0
    covered_count = sum(1 for block in eligible if block.get("span_metadata"))
    return covered_count, eligible_count, covered_count / eligible_count
```

- [ ] **Step 4: Add the validity helper**

Implement:

```python
def _span_backfill_is_valid(meta: dict, *, current_pdf_fingerprint: str, coverage: float) -> bool:
    if current_pdf_fingerprint == "unknown":
        return False
    return (
        meta.get("span_backfill_version") == CURRENT_SPAN_BACKFILL_VERSION
        and meta.get("span_visual_container_version") == CURRENT_SPAN_VISUAL_CONTAINER_VERSION
        and meta.get("span_pdf_fingerprint") == current_pdf_fingerprint
        and coverage >= MIN_SPAN_BACKFILL_COVERAGE
    )
```

- [ ] **Step 5: Split status-only and validity-field helpers**

Implement a status-only helper first:

```python
def _update_span_status_meta(meta: dict, *, covered_count: int, eligible_count: int, coverage: float, status: str) -> dict:
    updated = dict(meta)
    updated["span_backfill_covered_count"] = covered_count
    updated["span_backfill_eligible_count"] = eligible_count
    updated["span_backfill_coverage"] = coverage
    updated["span_backfill_status"] = status
    return updated
```

Then implement a validity-field helper for the verified paths only:

```python
def _update_span_validity_meta(meta: dict, *, fingerprint: str, covered_count: int, eligible_count: int, coverage: float, status: str) -> dict:
    updated = _update_span_status_meta(
        meta,
        covered_count=covered_count,
        eligible_count=eligible_count,
        coverage=coverage,
        status=status,
    )
    updated["span_backfill_version"] = CURRENT_SPAN_BACKFILL_VERSION
    updated["span_visual_container_version"] = CURRENT_SPAN_VISUAL_CONTAINER_VERSION
    updated["span_pdf_fingerprint"] = fingerprint
    return updated
```

Do not use the validity-field helper for `unavailable_pdf_missing`.

- [ ] **Step 6: Change rebuild orchestration to evaluate the skip contract**

In `run_derived_rebuild_for_keys()`, replace the unconditional span-backfill block with this shape:

```python
covered_count, eligible_count, coverage = _compute_span_backfill_coverage(all_raw_blocks)

span_meta_patch: dict[str, object] = {}

if not source_pdf_path or not source_pdf_path.exists():
    span_meta_patch = _update_span_status_meta(
        ocr_meta,
        covered_count=covered_count,
        eligible_count=eligible_count,
        coverage=coverage,
        status="unavailable_pdf_missing",
    )
elif compute_pdf_fingerprint(source_pdf_path) != "unknown" and _span_backfill_is_valid(...):
    span_meta_patch = _update_span_validity_meta(..., status="skipped_valid")
else:
    backfill_span_metadata_from_pdf(all_raw_blocks, source_pdf_path)
    covered_count, eligible_count, coverage = _compute_span_backfill_coverage(all_raw_blocks)
    write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)
    span_meta_patch = _update_span_validity_meta(..., status="rerun_...")
```

The key rules are:

- PDF unavailable does not rerun backfill,
- `current_pdf_fingerprint == "unknown"` is invalid for skip,
- raw blocks must be written before `span_*` validity fields are updated.

- [ ] **Step 7: Merge `span_meta_patch` into the final meta write path**

Do not store early updates in a local `meta` variable that will later be overwritten by the existing final `meta = read_json(...)` block.

Use this pattern instead:

```python
meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
meta.update(span_meta_patch)
meta = _apply_post_rebuild_version_flags(meta)
meta["ocr_status"] = "done"
...
write_json(artifacts.meta_json, meta)
```

- [ ] **Step 8: Run the focused rebuild tests**

Run:

`pytest tests/test_ocr_rebuild.py::test_span_backfill_coverage_uses_only_eligible_text_like_blocks -v`

`pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_skips_span_backfill_when_valid -v`

`pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_records_unavailable_pdf_missing_without_rerun -v`

`pytest tests/test_ocr_rebuild.py::test_run_derived_rebuild_does_not_skip_when_current_fingerprint_is_unknown -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_version_mismatch -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_visual_container_version_mismatch -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_fingerprint_mismatch -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_invalid_when_coverage_below_threshold -v`

`pytest tests/test_ocr_rebuild.py::test_span_backfill_does_not_update_validity_fields_when_raw_write_fails -v`

Expected: PASS.

## Task 3: Record the Policy Change and Verify the Rebuild Slice

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`
- Test: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Add a project-management entry for span-backfill invalidation policy**

Append an entry like this:

```md
### 12.16 Derived rebuild span-backfill skip contract (2026-06-22)

**Problem:** Derived rebuild reran PDF span backfill on every rebuild even when raw blocks already contained valid span enrichment.

**Root cause:** Rebuild had no explicit validity contract for stored span enrichment, so it treated all rebuilds as requiring a fresh PDF scan.

**Fix:** Added explicit skip/rerun policy using span-backfill version, visual-container version, current PDF fingerprint from `compute_pdf_fingerprint()`, eligible text-like coverage, recorded `span_backfill_status` fields in `meta.json`, and protected the meta write order so validity fields are only refreshed after raw persistence succeeds.

**Result:** Rebuild can reuse valid stored raw enrichment, avoid unnecessary PDF scans, and record why skip or rerun happened.

**Test status:** Added focused rebuild tests for eligible coverage denominator, valid skip, version/fingerprint/coverage/visual-container mismatches, unknown fingerprint invalidation, PDF-missing unavailable status, and raw-write failure validity protection.
```

- [ ] **Step 2: Run the rebuild test file**

Run: `pytest tests/test_ocr_rebuild.py -v`

Expected: PASS for the newly added focused tests. If the full file fails only on the pre-existing absolute-path tests tied to `D:\L\OB\Literature-hub`, record them as pre-existing environment-dependent failures rather than treating them as regressions from this plan.

- [ ] **Step 3: Inspect the final diff before handoff**

Run: `git diff -- paperforge/worker/ocr_rebuild.py tests/test_ocr_rebuild.py PROJECT-MANAGEMENT.md docs/superpowers/specs/2026-06-22-derived-rebuild-span-backfill-skip-design.md docs/superpowers/plans/2026-06-22-derived-rebuild-span-backfill-skip-plan.md`

Expected: diff limited to the span-backfill policy slice.

## Self-Review

- Spec coverage: the plan covers the eligible denominator, fixed fingerprint source, PDF-missing unavailable path, `unknown` fingerprint invalidation, status recording, and write-order contract.
- Placeholder scan: no `TBD`, `TODO`, or vague “handle edge cases” language remains in task steps.
- Type consistency: plan consistently uses `compute_pdf_fingerprint(source_pdf_path)`, `span_backfill_status`, and the `covered/eligible/coverage` helper shape.
