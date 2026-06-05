# Legacy OCR Backfill And Sync Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backfill legacy OCR paper directories that only contain `meta.json`, `json/result.json`, and `fulltext.md` into the new structured OCR artifact layout without rerunning raw OCR when `result.json` is still usable, and integrate that backfill into sync as a mostly invisible derived rebuild flow.

**Architecture:** Treat legacy OCR migration as a deterministic rebuild problem, not an OCR rerun problem. Add a classifier that labels each paper as `can_backfill`, `backfill_with_warning`, or `needs_rerun_raw`, then route the first two classes through the same derived rebuild pipeline used for modern OCR artifacts. Sync should detect these legacy papers and schedule backfill as deferred derived work; only papers lacking usable raw truth should surface as redo candidates.

**Tech Stack:** Python, pytest, current OCR rebuild pipeline, current sync runtime integration, filesystem scanning over `System/PaperForge/ocr/<zotero_key>/`

---

## File Structure

This plan should establish or modify these focused units:

- `paperforge/worker/ocr_legacy.py`
  - New module for legacy OCR directory detection, backfill eligibility classification, and migration summary building.
- `paperforge/worker/ocr_rebuild.py`
  - Extend to accept legacy inputs where `blocks.raw.jsonl` and other new artifacts are missing but `json/result.json` exists.
- `paperforge/worker/ocr.py`
  - Add a narrow helper to regenerate Phase 1-5 artifacts from legacy `result.json` without raw OCR rerun.
- `paperforge/services/sync_service.py`
  - Integrate legacy OCR backfill detection into the existing derived-runtime flow.
- `paperforge/worker/ocr_versions.py`
  - Extend version-state classification so legacy directories without `raw_version` / `derived_version` are first-class detectable states.
- `paperforge/commands/ocr.py`
  - Surface legacy backfill counts in doctor/diagnostics if useful.
- `tests/test_ocr_legacy.py`
  - New unit tests for legacy directory classification and migration decisions.
- `tests/test_ocr_rebuild.py`
  - Extend rebuild tests for legacy `result.json` backfill.
- `tests/test_sync_service_ocr_versions.py`
  - Extend sync runtime tests for deferred legacy backfill scheduling.
- `tests/test_ocr_redo_runtime.py`
  - New or extended tests to ensure only `needs_rerun_raw` papers escalate to redo.

Rationale:

- The real corpus currently has many legacy OCR directories, and the new search/evidence layer cannot work until those papers are backfilled.
- This should be solved once in the OCR runtime, not paper-by-paper by manual redo.
- Legacy backfill naturally belongs inside the same derived rebuild family as renderer/health/index refreshes.

## Classification Model

Every legacy OCR paper should be classified into one of three states:

1. `can_backfill`
   - `json/result.json` exists
   - `meta.json` exists or enough identity can be inferred
   - raw payload is parseable
   - backfill should proceed automatically

2. `backfill_with_warning`
   - `json/result.json` exists and is parseable
   - some compatibility fields are missing or suspicious
   - backfill should still proceed
   - resulting paper gets warning markers in health/runtime state

3. `needs_rerun_raw`
   - `json/result.json` missing
   - or unreadable
   - or obviously structurally unusable
   - this paper should not auto-backfill and should surface through redo/raw-upgrade flows

## Task 1: Lock Legacy OCR Classification Contract In Tests

**Files:**
- Create: `tests/test_ocr_legacy.py`
- Modify: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Write the failing legacy classification tests**

```python
from __future__ import annotations

from pathlib import Path


def test_legacy_paper_with_result_json_is_can_backfill(tmp_path: Path) -> None:
    from paperforge.worker.ocr_legacy import classify_legacy_ocr_dir

    paper_dir = tmp_path / "ocr" / "KEY001"
    (paper_dir / "json").mkdir(parents=True)
    (paper_dir / "json" / "result.json").write_text("[]", encoding="utf-8")
    (paper_dir / "meta.json").write_text('{"zotero_key":"KEY001","ocr_status":"done"}', encoding="utf-8")

    result = classify_legacy_ocr_dir(paper_dir)

    assert result["state"] in {"can_backfill", "backfill_with_warning"}


def test_legacy_paper_without_result_json_needs_rerun_raw(tmp_path: Path) -> None:
    from paperforge.worker.ocr_legacy import classify_legacy_ocr_dir

    paper_dir = tmp_path / "ocr" / "KEY002"
    paper_dir.mkdir(parents=True)
    (paper_dir / "meta.json").write_text('{"zotero_key":"KEY002","ocr_status":"done"}', encoding="utf-8")

    result = classify_legacy_ocr_dir(paper_dir)

    assert result["state"] == "needs_rerun_raw"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_legacy.py -q`
Expected: FAIL because `ocr_legacy.py` does not exist yet.

- [ ] **Step 3: Add a failing rebuild test for legacy-only directories**

Extend `tests/test_ocr_rebuild.py` with a case where:

- only `meta.json`
- `json/result.json`
- `fulltext.md`

exist, but no Phase 1-5 artifacts exist yet.

Expected result:

- derived rebuild succeeds
- `role-index.json` and other structured artifacts are created

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr_rebuild.py -k legacy -q`
Expected: FAIL because the rebuild pipeline currently expects newer artifacts.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ocr_legacy.py tests/test_ocr_rebuild.py
git commit -m "test: lock legacy OCR backfill contract"
```

## Task 2: Implement Legacy OCR Directory Classification

**Files:**
- Create: `paperforge/worker/ocr_legacy.py`
- Modify: `paperforge/worker/ocr_versions.py`
- Test: `tests/test_ocr_legacy.py`

- [ ] **Step 1: Implement `classify_legacy_ocr_dir()`**

Return at least:

- `zotero_key`
- `state`
- `reasons`
- `has_meta`
- `has_result_json`
- `has_compat_fulltext`
- `has_new_artifacts`

- [ ] **Step 2: Add a corpus scan helper**

Implement a helper like:

```python
def scan_legacy_ocr_dirs(ocr_root: Path) -> list[dict]:
    ...
```

This should be cheap and deterministic.

- [ ] **Step 3: Extend version-state logic for legacy papers**

If a paper has `result.json` but lacks `raw_version` / `derived_version`, classify it as legacy-backfillable rather than just generic stale.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_legacy.py tests/test_ocr_versions.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_legacy.py paperforge/worker/ocr_versions.py tests/test_ocr_legacy.py tests/test_ocr_versions.py
git commit -m "feat: classify legacy OCR directories for backfill"
```

## Task 3: Add Backfill-From-Result Rebuild Path

**Files:**
- Modify: `paperforge/worker/ocr_rebuild.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Add a helper that rebuilds from legacy `result.json`**

Implement a narrow helper, for example:

```python
def backfill_legacy_ocr_dir(vault: Path, key: str) -> dict:
    ...
```

This should:

- read `json/result.json`
- rebuild raw blocks
- rebuild structured blocks
- rebuild metadata/inventories/objects/render/health/index
- write version fields into `meta.json`

- [ ] **Step 2: Reuse existing builders**

Do not fork a separate logic path.
Call the same block/metadata/figure/table/render/health/index builders already used by the modern OCR pipeline.

- [ ] **Step 3: Mark legacy backfill outcomes**

For example in `meta.json` or a runtime field:

- `legacy_backfilled: true`
- `legacy_backfill_at`
- `legacy_backfill_warning_count`

Only if the data model needs it. Keep this additive.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_rebuild.py -k legacy -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_rebuild.py paperforge/worker/ocr.py tests/test_ocr_rebuild.py
git commit -m "feat: backfill legacy OCR directories from result.json"
```

## Task 4: Integrate Legacy Backfill Into Sync Runtime

**Files:**
- Modify: `paperforge/services/sync_service.py`
- Modify: `paperforge/commands/sync.py`
- Modify: `tests/test_sync_service_ocr_versions.py`

- [ ] **Step 1: Add failing sync tests for legacy backfill scheduling**

Cases to cover:

- `can_backfill` legacy papers are counted and deferred like derived rebuilds
- `backfill_with_warning` papers are also scheduled
- `needs_rerun_raw` papers are not auto-backfilled and are surfaced as raw-upgrade/redo candidates

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sync_service_ocr_versions.py -q`
Expected: FAIL until sync understands legacy backfill state.

- [ ] **Step 3: Integrate legacy scan into OCR runtime summary**

Sync runtime summary should add at least:

- `legacy_backfill_count`
- `legacy_backfill_keys`
- `legacy_rerun_raw_count`
- `legacy_rerun_raw_keys`

- [ ] **Step 4: Keep sync non-blocking**

Legacy backfill should follow the same rule as derived rebuild:

- detect during sync
- schedule or defer
- do not make sync completion depend on full backfill completion

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_sync_service_ocr_versions.py tests/cli/test_json_contracts.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/services/sync_service.py paperforge/commands/sync.py tests/test_sync_service_ocr_versions.py tests/cli/test_json_contracts.py
git commit -m "feat: schedule legacy OCR backfill during sync runtime"
```

## Task 5: Surface Legacy Backfill State In Diagnostics

**Files:**
- Modify: `paperforge/commands/ocr.py`
- Modify: `paperforge/worker/status.py`
- Modify: `tests/test_ocr_doctor.py`
- Modify: `tests/test_status.py`

- [ ] **Step 1: Add failing status/doctor assertions**

Expect doctor/status to mention:

- legacy backfillable paper count
- papers that require raw rerun

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_doctor.py tests/test_status.py -q`
Expected: FAIL until legacy state is surfaced.

- [ ] **Step 3: Add additive runtime summaries**

Do not redesign UX yet.
Just expose:

- `legacy_backfill_count`
- `legacy_rerun_raw_count`
- a few representative keys

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_doctor.py tests/test_status.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/commands/ocr.py paperforge/worker/status.py tests/test_ocr_doctor.py tests/test_status.py
git commit -m "feat: surface legacy OCR backfill state in diagnostics"
```

## Task 6: Add One Real-Corpus Smoke Procedure

**Files:**
- Update plan notes only or add a lightweight script if needed

- [ ] **Step 1: Define a corpus smoke procedure against `D:\L\OB\Literature-hub`**

Minimum checks:

- scan count of legacy papers
- sample 5 `PaddleOCR-VL-1.6` papers
- sample 5 `PaddleOCR-VL-1.5` papers
- run backfill on a representative paper such as `7C8829BD`
- confirm `role-index.json` lands
- confirm `paper-context` then includes `ocr_evidence`

- [ ] **Step 2: If useful, add a small helper script**

Only if it reduces repeated manual effort.

- [ ] **Step 3: Record expected outcome**

This should become the validation bridge before Phase 5.2 command integration.

## Task 7: Final Verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused legacy backfill suite**

Run: `python -m pytest tests/test_ocr_legacy.py tests/test_ocr_rebuild.py tests/test_sync_service_ocr_versions.py tests/test_ocr_doctor.py tests/test_status.py -q`
Expected: PASS

- [ ] **Step 2: Run broader OCR/runtime regressions**

Run: `python -m pytest tests/test_ocr_versions.py tests/test_ocr_render_v2.py tests/test_ocr_health.py tests/test_ocr.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_state_machine.py tests/test_sync.py tests/test_context.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 3: Run at least one real-corpus smoke backfill**

Expected:

- modern artifacts appear under a legacy paper directory
- `role-index.json` exists
- `paper-context` shows `ocr_evidence`

- [ ] **Step 4: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize legacy OCR backfill and sync integration"
```

## Risks To Watch During Execution

1. Do not force raw rerun when `result.json` is still usable.
2. Keep legacy backfill on the derived side of the system, not the raw OCR side.
3. Avoid special-casing legacy papers too much; the goal is to converge them onto the same artifact pipeline.
4. Keep sync non-blocking even when many legacy papers need backfill.
5. Do not move to command-layer OCR evidence retrieval until real corpus backfill is producing actual role indexes.

