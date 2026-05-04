---
phase: 25-surface-convergence-doctor-repair
plan: "03"
subsystem: base-views, repair
tags: ["lifecycle", "base-views", "repair", "build-index", "canonical-index"]

# Dependency graph
requires:
  - phase: 24-derived-lifecycle-health-maturity
    provides: lifecycle/maturity/next_step field computation in canonical index
provides:
  - Base views with lifecycle/maturity/next_step columns instead of raw status fields
  - Base views sorted by lifecycle ascending
  - Base view filters using lifecycle states instead of raw status combinations
  - Repair calls build_index() after fixing source artifacts
  - Documented recovery path for migration failure (MIG-04)
affects:
  - Phase 26: Traceable AI Context Packs (consumes lifecycle semantics)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Base views filter strings use double-quote YAML wrapper for lifecycle values with single quotes
    - Repair uses lazy import inside conditional block to avoid circular deps

key-files:
  created: []
  modified:
    - paperforge/worker/base_views.py
    - paperforge/worker/repair.py
    - tests/test_base_views.py
    - tests/test_base_preservation.py
    - tests/test_repair.py

key-decisions:
  - "Use English column display names (Lifecycle, Maturity, Next Step) in Base view properties"
  - "Double-quote YAML wrapping for filters containing single-quoted lifecycle values"
  - "Lazy import build_index inside fix conditional block to avoid circular dependency"
  - "待 OCR view omits maturity_level column since papers haven't been processed yet"

patterns-established:
  - "Filter strings use lifecycle = lifecycle-specific values consistently across all 8 views"
  - "Sort by lifecycle ascending on every view for consistent readiness ordering"

requirements-completed:
  - SURF-01
  - SURF-02
  - SURF-04
  - MIG-04

# Metrics
duration: 13min
completed: 2026-05-04
---

# Phase 25: Surface Convergence, Doctor & Repair — Plan 03 Summary

**Base views lifecycle column migration and repair source-first rebuild with build_index() call**

## Performance

- **Duration:** 13 min
- **Started:** 2026-05-04T11:21:05Z
- **Completed:** 2026-05-04T11:34:25Z
- **Tasks:** 2 (3 commits)
- **Files modified:** 5

## Accomplishments

- All 8 Base views updated: removed `has_pdf`, `do_ocr`, `analyze`, `ocr_status` columns; added `lifecycle`, `maturity_level`, `next_step`
- Base view filters rewritten to use lifecycle states instead of raw status combinations
- Sort by lifecycle ascending added to every view
- `PROPERTIES_YAML` and `_build_base_yaml()` updated with lifecycle properties
- Filter YAML output uses double-quote wrapping to support single-quoted lifecycle values
- `run_repair()` calls `build_index(vault, verbose)` after fixing source artifacts (`fix=True` or `fix_paths=True`)
- User-facing recovery path messages printed: `--rebuild-index` flag with `.bak` fallback
- 50 tests pass across all three affected test suites (base_views, repair, preservation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Base view columns and filters to use lifecycle** — `bd62266` (feat)
2. **Task 1: (auto-fix) Double-quote YAML wrapping for lifecycle filter values** — `36dccf1` (fix)
3. **Task 2: Wire repair to call build_index() after fixing source artifacts** — `00cd475` (feat)

## Files Created/Modified

- `paperforge/worker/base_views.py` — Updated `build_base_views()` columns/filters/sort, `_render_views_section()` sort rendering, `PROPERTIES_YAML`, `merge_base_views()` inline sort rendering, `_build_base_yaml()` properties and sort
- `paperforge/worker/repair.py` — Added `build_index()` call after fix operations, `rebuilt` result key, user recovery path messages
- `tests/test_base_views.py` — New lifecycle column/filter/sort/properties tests; updated old field-based filter expectations to lifecycle
- `tests/test_base_preservation.py` — Updated filter preservation test for lifecycle-based filter strings
- `tests/test_repair.py` — New rebuild tests: build_index called after fix, not called on dry-run, rebuilt in result, error fallback

## Decisions Made

- **English column display names** in Base properties: Lifecycle, Maturity, Next Step (the agent's discretion, technical view)
- **Double-quote YAML wrapping** for filters containing single-quoted lifecycle values (`lifecycle = 'fulltext_ready'`) — prevents YAML parse errors
- **Lazy import** of `build_index` inside the fix conditional block follows the established pattern for circular dependency avoidance
- **"待 OCR" view** omits `maturity_level` column since maturity assessment requires processed fulltext (OCR not yet complete)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] YAML filter quoting broken by lifecycle values with single quotes**
- **Found during:** Task 1 (post-commit verification)
- **Issue:** New filter values contain single-quoted strings (`lifecycle = 'fulltext_ready'`) which broke the existing single-quote YAML wrapper (`filter: 'lifecycle = 'fulltext_ready''` is invalid YAML)
- **Fix:** Changed filter YAML wrapper from single-quotes to double-quotes in all three rendering locations: `_render_views_section()`, `merge_base_views()` inline block, `_build_base_yaml()`
- **Files modified:** `paperforge/worker/base_views.py`, `tests/test_base_preservation.py`
- **Verification:** Rendered output shows `filter: "lifecycle = 'fulltext_ready'"` — valid YAML
- **Committed in:** `36dccf1` (separate fix commit after task commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary for correct YAML output — without the fix, generated .base files would have broken YAML syntax.

## Issues Encountered

- Pre-existing test failures in `test_e2e_pipeline.py`, `test_ocr_state_machine.py`, and `test_prepare_rollback.py` (`TSTONE001` library record not found) — unrelated to this plan's changes
- Single-quote YAML wrapping issue discovered during output verification — fixed via deviation Rule 2

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Base views fully migrated to lifecycle semantics. Next: Phase 26 (Traceable AI Context Packs) or remaining Phase 25 plans (status/doctor, plugin dashboard).
- Plan 25-03 is the third of three plans for Phase 25 — phase is ready for verification.
- All existing Base merge and preservation tests continue to pass (user customization via PAPERFORGE_VIEW_PREFIX preserved).

## Self-Check: PASSED

All 5 modified files confirmed on disk. All 3 commits confirmed in git log. SUMMARY.md present.

---

*Phase: 25-surface-convergence-doctor-repair*
*Completed: 2026-05-04*
