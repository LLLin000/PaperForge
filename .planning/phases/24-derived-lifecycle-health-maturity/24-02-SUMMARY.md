---
phase: 24-derived-lifecycle-health-maturity
plan: 02
subsystem: worker
tags: [asset-state, lifecycle, health, maturity, next-step, index]

# Dependency graph
requires:
  - phase: 24-01
    provides: "compute_lifecycle, compute_health, compute_maturity, compute_next_step in asset_state.py"
provides:
  - "Every canonical index entry now carries embedded lifecycle, health, maturity, and next_step fields derived from source artifacts"
  - "Both build_index() and refresh_index_entry() code paths produce entries with the four new fields"
affects: [25-surface-convergence, 26-ai-context-packs, plugin-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import pattern: asset_state functions imported inside _build_entry() to avoid circular dependencies with sync.py"
    - "Pure derivation: all four fields computed from the entry dict itself, no filesystem access, no side effects"

key-files:
  created: []
  modified:
    - "paperforge/worker/asset_index.py - Added import and 4 field assignments to _build_entry()"
    - "tests/test_asset_index_integration.py - Added TestDerivedStateFields class (6 tests)"

key-decisions:
  - "Derived fields inserted after entry dict construction but before formal note write — ensures note frontmatter does not include machine-only fields"
  - "Lazy import inside _build_entry() follows the existing pattern established for sync.py/ocr.py imports — no new circular dependency risk"
  - "Call order: lifecycle first, then health, then maturity (calls lifecycle internally), then next_step — ensures maturity has correct lifecycle value"

patterns-established:
  - "Pattern: Derived machine-only fields appended to entry dict after all source-artifact fields, before formal note write — keeps machine state out of user-visible notes"

requirements-completed: [STATE-01, STATE-02, STATE-03, STATE-04, AIC-01]

# Metrics
duration: 25min
completed: 2026-05-04
---

# Phase 24 Plan 02: asset_state Integration into asset_index Summary

**All four compute functions from asset_state.py wired into _build_entry() — every canonical index entry now carries embedded lifecycle, health, maturity, and next_step fields derived from source artifacts**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-04T02:40:21Z
- **Completed:** 2026-05-04T03:04:55Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Imported `compute_lifecycle`, `compute_health`, `compute_maturity`, `compute_next_step` from `asset_state` into `_build_entry()`
- Added 4 field assignments after entry dict construction, before formal note write — fields flow automatically through both `build_index()` and `refresh_index_entry()`
- 6 new integration tests verify field presence, type correctness, and value validity across both full-build and incremental-refresh paths
- All 55 asset-specific tests pass (23 asset_index + 26 asset_state + 6 new integration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add derived state fields to _build_entry()** - `8fd963f` (feat)
2. **Task 2: Add integration tests for derived state fields** - `043df53` (test)
3. **Task 3: Verify full test suite and serialization** - No code changes (verification-only)

## Files Created/Modified
- `paperforge/worker/asset_index.py` - Added lazy import of 4 asset_state functions; added 4 field assignments (lifecycle, health, maturity, next_step) after entry dict construction
- `tests/test_asset_index_integration.py` - Added `TestDerivedStateFields` class with 6 test methods covering field presence, type validation, and value correctness

## Decisions Made
- Lazy import inside `_build_entry()` follows existing pattern (sync.py, ocr.py imports) — avoids circular dependency risk
- Derived fields inserted after entry dict closing `}` but before `# Write / update the formal note` — keeps machine-only fields out of user-visible Obsidian note frontmatter
- Call order: lifecycle → health → maturity → next_step. Maturity calls `compute_lifecycle()` internally, so lifecycle must be set first

## Deviations from Plan

None — plan executed exactly as written.

The 3 pre-existing test failures (`test_doctor_on_empty_vault`, `test_corrupt_meta_json_does_not_crash`, `test_request_timeout_triggers_retry_not_fatal`) are confirmed unrelated to these changes (verified by git stash revert).

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Phase 25 (surface convergence): Ready — canonical index entries now carry all four derived state fields needed by status dashboards and plugin surfaces
- Phase 26 (AI context packs): Ready — lifecycle and maturity fields available for context-pack quality gates
- No blockers

---
*Phase: 24-derived-lifecycle-health-maturity*
*Completed: 2026-05-04*
