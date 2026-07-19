---
phase: 24-derived-lifecycle-health-maturity
plan: 01
subsystem: worker
tags: [lifecycle, health, maturity, derivation, pure-functions, tdd]

requires:
  - phase: 23-canonical-asset-index-safe-rebuilds
    provides: canonical index entry dict shape from _build_entry()
provides:
  - compute_lifecycle(entry) -> str — six progressive lifecycle states
  - compute_health(entry) -> dict — four-dimension health with fix instructions
  - compute_maturity(entry) -> dict — level 1-6 with check breakdown
  - compute_next_step(entry) -> str — priority-ordered next-action recommendation
affects:
  - 24-02-PLAN (asset_index integration)
  - status.py (can read lifecycle/health from index)
  - doctor.py (health findings power diagnostics)

tech-stack:
  added: []
  patterns: [pure-function-derivation, class-per-function-tests, tdd-red-green-refactor]

key-files:
  created:
    - paperforge/worker/asset_state.py
    - tests/test_asset_state.py
  modified: []

key-decisions:
  - "compute_maturity delegates to compute_lifecycle internally — no duplicate logic"
  - "All four functions use .get() with safe defaults — no KeyError on missing fields from legacy or partial entries"
  - "has_pdf=False short-circuits lifecycle to 'indexed' regardless of ocr/deep_reading status"
  - "Asset health always uses 'Missing workspace paths: {list}' format (no separate 'Workspace not initialized' message)"

patterns-established:
  - "Pure function pattern for derivation logic: no filesystem access, no imports from paperforge.config or paperforge.worker._utils"
  - "TDD class-per-function: 4 test classes, 26 test methods total"

requirements-completed:
  - STATE-01
  - STATE-02
  - STATE-03
  - STATE-04
  - AIC-01

duration: 10 min
completed: 2026-05-04
---

# Phase 24 Plan 01: Asset State Derivation Summary

**Four pure derivation functions (lifecycle, health, maturity, next-step) consuming canonical index entry dicts with full test coverage via TDD**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-04T10:26:43Z
- **Completed:** 2026-05-04T10:36:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `paperforge/worker/asset_state.py` with four pure derivation functions: `compute_lifecycle` (6 states), `compute_health` (4 dimensions), `compute_maturity` (level 1-6), `compute_next_step` (6 action types)
- 26 tests covering all lifecycle states, health dimensions, maturity levels, and next-step recommendations
- `compute_maturity` delegates to `compute_lifecycle` internally — zero duplicate derivation logic
- All functions use `.get()` with safe defaults — safe for legacy or partial index entries
- Zero filesystem or config imports — pure functions suitable for plugin reuse

## Task Commits

Each TDD phase was committed atomically:

1. **Task 1: RED — Write failing tests** - `7daffab` (test)
2. **Task 2: GREEN — Implement four functions** - `3228126` (feat)
3. **Task 3: REFACTOR — Polish and document** - `1528550` (refactor)

## Files Created/Modified

- `paperforge/worker/asset_state.py` - Four pure derivation functions consuming canonical index entry dicts (242 lines)
- `tests/test_asset_state.py` - 26 tests across 4 test classes (336 lines)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] lifecycle returned deep_read_done when has_pdf=False with OCR/deep_reading done**
- **Found during:** Task 2 (GREEN phase test run)
- **Issue:** The progressive check order checked `ocr_status="done"` before `has_pdf`. When `has_pdf=False` but `ocr_status="done"` and `deep_reading_status="done"`, the function returned `deep_read_done` instead of `indexed`.
- **Fix:** Moved `not has_pdf` check to the top as a short-circuit returning `"indexed"` immediately. Reorganized remaining checks under the `ocr_status == "done"` branch.
- **Files modified:** paperforge/worker/asset_state.py
- **Verification:** test_no_pdf_returns_indexed passes
- **Committed in:** `3228126` (Task 2 commit)

**2. [Rule 1 - Bug] Asset health for empty entry used different message format than test expected**
- **Found during:** Task 2 (GREEN phase test run)
- **Issue:** When all 4 workspace paths were empty, the implementation returned `"Workspace not initialized: run paperforge sync"` but the test expected `"Missing workspace paths"` in the message. The special-case message diverged from the consistent list-based format.
- **Fix:** Removed the special "all 4 missing" case. Now all missing-path cases use the consistent `"Missing workspace paths: {list}. Run paperforge sync to regenerate"` format.
- **Files modified:** paperforge/worker/asset_state.py
- **Verification:** test_empty_entry_all_unhealthy passes
- **Committed in:** `3228126` (Task 2 commit)

**3. [Rule 2 - Missing Critical] Ruff SIM108: if-else block should use ternary for note_health**
- **Found during:** Task 3 (REFACTOR ruff check)
- **Issue:** Ruff flagged the note_health if-else block as replaceable with a ternary expression (SIM108).
- **Fix:** Converted to ternary: `note_health = "Formal note missing..." if not note_path else "healthy"`
- **Files modified:** paperforge/worker/asset_state.py
- **Verification:** ruff: All checks passed, 26/26 tests pass
- **Committed in:** `1528550` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing code quality fix)
**Impact on plan:** All auto-fixes necessary for correctness and code quality. No scope creep.

## Issues Encountered

- TDD test-implementation inconsistency: the plan's behavior description listed a special "Workspace not initialized" message for all-empty workspace paths, but the test expected the consistent list-based format. Resolved by matching the test (TDD spec wins).

## Next Phase Readiness

- `asset_state.py` is ready for integration in Plan 24-02 (asset_index.py integration)
- All four functions are importable and tested — ready for `_build_entry()` to call them
- No external dependencies — integration is a matter of adding import + function calls in `asset_index.py`

---
*Phase: 24-derived-lifecycle-health-maturity*
*Completed: 2026-05-04*
