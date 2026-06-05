# OCR Structured Pipeline Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Phase 4 runtime integration so PaperForge can detect raw-version and derived-version drift, trigger non-blocking derived rebuilds during sync, surface raw-upgrade opportunities through redo-facing state, and keep OCR runtime state coherent across CLI, sync, status, and dashboard.

**Architecture:** Keep user-facing semantics simple: `paperforge ocr` runs OCR, `paperforge ocr redo` reruns full-paper OCR for notes marked `ocr_redo: true`, and sync remains fast. Phase 4 adds version-aware state detection and orchestration around the artifacts produced in Phases 1-3. Derived drift should be mostly user-invisible and repairable through rebuild scheduling; raw drift should be visible but user-controlled through redo selection. This phase also absorbs the current execution risk that `ocr_render.py` and `ocr_objects.py` are uncommitted and therefore need a preflight audit before automatic rebuild logic begins to fan out their outputs.

**Tech Stack:** Python, pytest, current PaperForge sync service and worker sync path, PFResult JSON contracts, plugin dashboard command surfaces, file-based runtime snapshots

---

## File Structure

Phase 4 should establish these focused units:

- `paperforge/worker/ocr_versions.py`
  - New module for raw/derived drift classification and paper-level version state summaries.
- `paperforge/worker/ocr_rebuild.py`
  - New module for derived-layer rebuild orchestration and scheduling decisions.
- `paperforge/worker/ocr_runtime.py`
  - New module for compact OCR runtime state snapshots shared by sync, status, and dashboard.
- `paperforge/worker/ocr.py`
  - Keep OCR entrypoint and redo semantics intact.
  - Modify only to expose version state and hook derived rebuild entrypoints.
- `paperforge/services/sync_service.py`
  - Primary integration point for non-blocking derived drift detection and rebuild triggering.
- `paperforge/commands/sync.py`
  - Extend returned PFResult payload with derived rebuild summary if needed.
- `paperforge/commands/ocr.py`
  - Extend OCR command JSON/status summary with version-state information.
- `paperforge/worker/status.py`
  - Surface raw-upgradable and derived-stale state in doctor/status.
- `paperforge/plugin/src/views/dashboard.ts`
  - Optional plugin-side display integration for stale/upgradable OCR state, but keep it additive.
- `tests/test_ocr_versions.py`
  - New unit tests for version comparison and state classification.
- `tests/test_ocr_rebuild.py`
  - New unit tests for derived rebuild selection and execution policy.
- `tests/test_sync_service_ocr_versions.py`
  - New tests for sync-triggered detection and non-blocking rebuild behavior.
- `tests/test_ocr_redo_runtime.py`
  - New tests for raw-upgrade state and redo interaction.
- `tests/test_status.py`
  - Extend runtime state / doctor coverage.
- `tests/cli/test_json_contracts.py`
  - Extend command JSON envelope expectations if payloads grow.

Rationale:

- Version state should live in focused runtime modules instead of leaking into `ocr.py` or `sync.py` ad hoc.
- Sync orchestration belongs in `SyncService`, not back in frozen `worker/sync.py`.
- This phase must explicitly handle the current risk that some renderer/object changes are still uncommitted before we automate rebuild fanout.

### Task 1: Add A Preflight Audit For Dirty OCR Runtime Files

**Files:**
- Create: `tests/test_ocr_runtime_preflight.py`
- Modify: `paperforge/services/sync_service.py`
- Modify: `paperforge/commands/sync.py`

- [ ] **Step 1: Write the failing preflight tests**

```python
from __future__ import annotations


def test_sync_preflight_flags_dirty_ocr_runtime_modules(tmp_path):
    from paperforge.services.sync_service import detect_ocr_runtime_preflight_issues

    issues = detect_ocr_runtime_preflight_issues(
        dirty_files=[
            "paperforge/worker/ocr_render.py",
            "paperforge/worker/ocr_objects.py",
        ]
    )

    assert issues
    assert any("ocr_render.py" in issue for issue in issues)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr_runtime_preflight.py -q`
Expected: FAIL because the preflight helper does not exist yet.

- [ ] **Step 3: Implement a narrow preflight detector**

Create a small helper in `SyncService` or a focused module that:

- checks for dirty OCR runtime files before auto-triggering derived rebuilds
- returns warnings, not hard process failure

Minimum watched files:

- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_objects.py`
- any future runtime rebuild modules added in this phase

- [ ] **Step 4: Surface preflight warnings in sync result**

Add these warnings to sync PFResult output without failing sync.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_runtime_preflight.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/services/sync_service.py paperforge/commands/sync.py tests/test_ocr_runtime_preflight.py
git commit -m "feat: add OCR runtime preflight warnings for auto-rebuild"
```

### Task 2: Lock Version-State Classification Contract In Tests

**Files:**
- Create: `tests/test_ocr_versions.py`
- Modify: `tests/test_ocr.py`
- Reference: `docs/superpowers/specs/2026-06-04-ocr-structured-pipeline-design.md`

- [ ] **Step 1: Write the failing version-state tests**

```python
from __future__ import annotations


def test_version_state_distinguishes_raw_vs_derived_drift() -> None:
    from paperforge.worker.ocr_versions import classify_version_state

    state = classify_version_state(
        meta={
            "raw_version": {"ocr_model": "PaddleOCR-VL-1.5", "pdf_fingerprint": "sha256:a"},
            "derived_version": {"renderer_version": "1.0.0-compat"},
        },
        expected_raw={
            "ocr_model": "PaddleOCR-VL-1.6",
            "pdf_fingerprint": "sha256:a",
        },
        expected_derived={
            "renderer_version": "2.0.0",
        },
    )

    assert state["raw_upgradable"] is True
    assert state["derived_stale"] is True
```

- [ ] **Step 2: Add a failing end-to-end version-state assertion**

Extend `tests/test_ocr.py` or a new runtime-focused OCR test to assert that version-state data can be built from current `meta.json`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_versions.py -q`
Expected: FAIL because version-state helpers do not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_versions.py tests/test_ocr.py
git commit -m "test: lock OCR phase4 version state contract"
```

### Task 3: Implement Raw/Derived Version State Classification

**Files:**
- Create: `paperforge/worker/ocr_versions.py`
- Modify: `paperforge/worker/ocr_artifacts.py`
- Modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_versions.py`

- [ ] **Step 1: Implement expected-version builders**

Add helpers for:

- expected raw version payload from current config/model
- expected derived version payload from current code constants

Keep these centralized so sync, OCR, and status compare against the same source.

- [ ] **Step 2: Implement `classify_version_state()`**

Return at least:

- `raw_upgradable`
- `derived_stale`
- `raw_reasons`
- `derived_reasons`
- `has_version_state`

- [ ] **Step 3: Mirror compact version state into `meta.json`**

Keep `raw_version` and `derived_version` as source-of-truth fields, but add compact runtime mirrors such as:

- `raw_upgradable`
- `derived_stale`
- `version_state_updated_at`

Do not remove the full version payloads.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_versions.py tests/test_ocr.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_versions.py paperforge/worker/ocr_artifacts.py paperforge/worker/ocr.py tests/test_ocr_versions.py tests/test_ocr.py
git commit -m "feat: classify OCR raw and derived version state"
```

### Task 4: Lock Derived Rebuild Orchestration Contract In Tests

**Files:**
- Create: `tests/test_ocr_rebuild.py`
- Modify: `tests/test_ocr_redo.py`

- [ ] **Step 1: Write the failing rebuild orchestration tests**

```python
from __future__ import annotations


def test_rebuild_selector_only_targets_derived_stale_papers() -> None:
    from paperforge.worker.ocr_rebuild import select_papers_for_derived_rebuild

    papers = [
        {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
        {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
    ]

    selected = select_papers_for_derived_rebuild(papers)

    assert selected == ["A"]
```

- [ ] **Step 2: Add a redo guard test**

Assert that `ocr redo` does not become the code path for derived-only rebuilds.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_rebuild.py tests/test_ocr_redo.py -k "derived_rebuild or redo_guard" -q`
Expected: FAIL because rebuild orchestration does not exist yet.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_rebuild.py tests/test_ocr_redo.py
git commit -m "test: lock OCR phase4 rebuild orchestration contract"
```

### Task 5: Implement Derived Rebuild Helpers Without Changing Redo Semantics

**Files:**
- Create: `paperforge/worker/ocr_rebuild.py`
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/commands/ocr.py`
- Test: `tests/test_ocr_rebuild.py`

- [ ] **Step 1: Implement narrow derived rebuild entrypoints**

Add helpers like:

- `select_papers_for_derived_rebuild()`
- `run_derived_rebuild_for_keys()`

They should rebuild:

- resolved metadata
- inventories
- object markdown
- render outputs
- health

Without rerunning raw OCR.

- [ ] **Step 2: Keep these entrypoints internal**

Do not introduce a new public user-facing redo command.
This is runtime orchestration support for sync and maintenance flows.

- [ ] **Step 3: Preserve redo semantics**

`paperforge ocr redo` must continue to mean:

- full-paper rerun
- clear old raw + derived OCR artifacts
- rerun current OCR model

It must not be reused for derived-only rebuild.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_rebuild.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_rebuild.py paperforge/worker/ocr.py paperforge/commands/ocr.py tests/test_ocr_rebuild.py tests/test_ocr_redo.py
git commit -m "feat: add derived OCR rebuild helpers without changing redo semantics"
```

### Task 6: Integrate Derived Drift Detection Into SyncService

**Files:**
- Create: `tests/test_sync_service_ocr_versions.py`
- Modify: `paperforge/services/sync_service.py`
- Modify: `paperforge/commands/sync.py`

- [ ] **Step 1: Write the failing sync integration tests**

```python
from __future__ import annotations


def test_sync_detects_derived_drift_without_failing_sync(tmp_path) -> None:
    from paperforge.services.sync_service import summarize_ocr_version_actions

    summary = summarize_ocr_version_actions(
        papers=[
            {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
            {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
        ]
    )

    assert summary["derived_rebuild_count"] == 1
    assert summary["raw_upgrade_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sync_service_ocr_versions.py -q`
Expected: FAIL because sync version-action summary does not exist yet.

- [ ] **Step 3: Implement non-blocking version scan inside sync**

In `SyncService.run()`:

- scan OCR paper directories after selection/index phases
- classify version state per paper
- collect derived-stale and raw-upgradable counts
- trigger derived rebuilds non-blockingly or as best-effort follow-up

Do not let sync return non-zero solely because derived rebuild scheduling found stale papers.

- [ ] **Step 4: Expose structured summary in PFResult**

Include a sync result section like:

- `ocr_runtime.derived_rebuild_count`
- `ocr_runtime.raw_upgrade_count`
- `ocr_runtime.preflight_warnings`

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_sync_service_ocr_versions.py tests/cli/test_json_contracts.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/services/sync_service.py paperforge/commands/sync.py tests/test_sync_service_ocr_versions.py tests/cli/test_json_contracts.py
git commit -m "feat: integrate OCR version state into sync runtime"
```

### Task 7: Surface Raw-Upgradable And Derived-Stale State Through Status/Doctor/OCR JSON

**Files:**
- Modify: `paperforge/worker/status.py`
- Modify: `paperforge/commands/ocr.py`
- Modify: `tests/test_status.py`
- Modify: `tests/test_ocr_doctor.py`

- [ ] **Step 1: Add failing runtime-state visibility tests**

Extend tests so:

- `paperforge status --json` exposes version-state aggregates
- `paperforge ocr --json` includes raw-upgradable / derived-stale summaries
- doctor text mentions raw-upgradable and derived-stale counts when present

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_status.py tests/test_ocr_doctor.py -q`
Expected: FAIL until version state is surfaced.

- [ ] **Step 3: Implement runtime-state summaries**

Keep this narrow:

- aggregate counts
- a few representative keys
- guidance strings for user action

Avoid detailed plugin UX logic in the Python output layer.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_status.py tests/test_ocr_doctor.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/status.py paperforge/commands/ocr.py tests/test_status.py tests/test_ocr_doctor.py
git commit -m "feat: surface OCR version runtime state in status and doctor"
```

### Task 8: Add Minimal Dashboard/Plugin Runtime Awareness

**Files:**
- Modify: `paperforge/plugin/src/views/dashboard.ts`
- Modify: `paperforge/plugin/src/constants.ts`
- Modify: plugin-side tests only if they already exist for dashboard JSON handling

- [ ] **Step 1: Add a narrow dashboard contract test or spot-check target**

If no plugin unit test exists, define a manual verification target in the plan:

- dashboard does not break when sync/status JSON includes new OCR runtime summary
- collection/global modes can still render OCR pipeline counts

- [ ] **Step 2: Make dashboard tolerant of new OCR runtime fields**

Add UI only if low-risk:

- count of raw-upgradable papers
- count of derived-stale papers

Do not block this phase on large UI redesign.

- [ ] **Step 3: Run relevant plugin tests or manual build verification**

Run: `cd paperforge/plugin && npx vitest run`
Expected: PASS if plugin test coverage exists

- [ ] **Step 4: Commit**

```bash
git add paperforge/plugin/src/views/dashboard.ts paperforge/plugin/src/constants.ts
git commit -m "feat: tolerate OCR runtime version state in dashboard"
```

### Task 9: Final Verification For Phase 4

**Files:**
- Verify only

- [ ] **Step 1: Run Phase 4 focused suite**

Run: `python -m pytest tests/test_ocr_runtime_preflight.py tests/test_ocr_versions.py tests/test_ocr_rebuild.py tests/test_sync_service_ocr_versions.py tests/test_status.py tests/test_ocr_doctor.py tests/cli/test_json_contracts.py -q`
Expected: PASS

- [ ] **Step 2: Run prior OCR pipeline regression suites**

Run: `python -m pytest tests/test_ocr_render_v2.py tests/test_ocr_health.py tests/test_ocr.py tests/test_ocr_rendering.py tests/test_ocr_integration_fixtures.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_state_machine.py tests/test_sync.py tests/test_context.py tests/test_selection_sync_pdf.py tests/e2e/test_ocr_e2e.py tests/test_ocr_redo.py -q`
Expected: PASS

- [ ] **Step 3: Run sync service regression suite**

Run: `python -m pytest tests/e2e/test_sync_pipeline.py tests/e2e/test_status_doctor_repair.py tests/journey/test_daily_workflow.py tests/journey/test_onboarding.py -q`
Expected: PASS or document any existing unrelated failures

- [ ] **Step 4: Inspect diff scope**

Run: `git diff -- paperforge/worker paperforge/services paperforge/commands paperforge/plugin docs/superpowers tests`
Expected: changes are limited to version-state runtime integration, rebuild orchestration, and additive dashboard tolerance; no Phase 5 search/evidence work yet.

- [ ] **Step 5: Commit verification-only fixes if needed**

```bash
git add -A
git commit -m "test: finalize OCR structured pipeline phase4 runtime integration"
```

## Risks To Watch During Execution

1. The current dirty `ocr_render.py` / `ocr_objects.py` state must be audited before auto-rebuild logic depends on them.
2. Do not let sync become slow or blocking because of derived rebuild work.
3. Keep redo semantics strictly full-rerun; derived rebuild must remain a separate internal path.
4. Avoid reintroducing path truth-source drift by bypassing `paperforge_paths()` / `pipeline_paths()`.
5. Do not auto-rerun raw OCR on version drift; raw upgrade remains user-driven through redo selection state.
6. The current renderer/object placement logic is still conservative; derived rebuild fanout must not assume perfect semantic placement.

