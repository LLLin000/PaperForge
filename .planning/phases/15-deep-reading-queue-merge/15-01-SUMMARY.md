---
phase: 15-deep-reading-queue-merge
plan: 01
subsystem: worker
tags: deep-reading, queue, refactoring, code-health
requires:
  - phase: 14-shared-utilities-extraction
    provides: _utils.py leaf module with shared utility functions
provides:
  - scan_library_records() as canonical data acquisition function
  - _resolve_formal_note_path() moved to _utils.py
  - deep_reading.py refactored to use scan_library_records()
  - ld_deep.py scan_deep_reading_queue() as thin wrapper
affects:
  - 17-code-cleanup (unused import removal)
  - 19-consolidation-tests (unit tests for _utils.py)

tech-stack:
  added: []
  patterns:
    - Canonical data acquisition: scan_library_records() as single source of library-record scanning
    - Thin wrapper pattern: scan_deep_reading_queue() calls canonical function + caller-specific filter/sort
    - Pure data separation: scan_library_records() has no side effects, no categorization

key-files:
  created:
    - paperforge/worker/_utils.py (Phase 14 content + scan_library_records + _resolve_formal_note_path)
  modified:
    - paperforge/worker/deep_reading.py (refactored to use scan_library_records; re-export comment)
    - paperforge/skills/literature-qa/scripts/ld_deep.py (thin wrapper using scan_library_records)

key-decisions:
  - "scan_library_records() returns ALL analyze=true records (not filtered by deep_reading_status) -- caller filters"
  - "scan_library_records() does NOT sort -- caller sorts as needed"
  - "ld_deep.py uses module-level direct import from _utils.py (safe -- _utils.py is a leaf module)"
  - "deep_reading.py retains status sync + categorization + report generation (D-05)"

patterns-established:
  - "Canonical data acquisition function in _utils.py with pure data semantics"
  - "Thin-wrapper delegation with reusable filter/sort logic in consumer modules"

requirements-completed:
  - CH-03

duration: 4min
completed: 2026-04-27
---

# Phase 15 Plan 01: Canonical scan_library_records() Summary

**Eliminated divergent queue-scanning logic between worker/deep_reading.py and skills/ld_deep.py by creating a single canonical `scan_library_records()` in _utils.py, with both callers converted to thin wrappers.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-27T15:54:34Z
- **Completed:** 2026-04-27T15:58:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `scan_library_records(vault) -> list[dict]` in _utils.py -- pure data acquisition with all D-03 fields (zotero_key, domain, title, analyze, do_ocr, deep_reading_status, ocr_status, note_path)
- `_resolve_formal_note_path()` moved from deep_reading.py to _utils.py with function-level `paperforge_paths` import
- `run_deep_reading()` in deep_reading.py refactored: replaced inline scan loop with `scan_library_records()` call, retained status sync, categorization, and report logic unchanged
- `scan_deep_reading_queue()` in ld_deep.py reduced to a 14-line thin wrapper calling `scan_library_records()` with filter + sort
- ~49 lines of duplicate scanning logic removed from ld_deep.py
- 203/203 tests pass (2 pre-existing skips)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scan_library_records() and _resolve_formal_note_path() to _utils.py** - `e24ef4c` (feat)
2. **Task 2: Refactor deep_reading.py and ld_deep.py to call scan_library_records()** - `d472c30` (feat)

**Plan metadata:** (to be committed)

## Files Created/Modified

- `paperforge/worker/_utils.py` - Added `scan_library_records()` and `_resolve_formal_note_path()` in new `# --- Deep-Reading Queue ---` section (Phase 14 content also included in this commit)
- `paperforge/worker/deep_reading.py` - Added imports, replaced `_resolve_formal_note_path` definition with re-export comment, replaced inline scan loop with `scan_library_records()` call
- `paperforge/skills/literature-qa/scripts/ld_deep.py` - Added module-level import from _utils, replaced `scan_deep_reading_queue()` body with thin wrapper

## Decisions Made

- **Canonical function signature**: `scan_library_records(vault: Path) -> list[dict]` -- returns ALL analyze=true records regardless of deep_reading_status, with no side effects, no categorization, no sorting (per D-02, D-03, D-04)
- **ld_deep.py import strategy**: Module-level direct `from paperforge.worker._utils import scan_library_records` (per D-08) -- safe because _utils.py is a leaf module
- **OCR status lookup**: Simplified to direct `meta.json` read via `read_json()` (same as ld_deep.py's _read_json approach) -- validates well with all sandbox tests passing
- **Status sync retained**: `run_deep_reading()` still checks `has_deep_reading_content()` against actual note content and syncs frontmatter before building queue (per D-05)
- **Regex patterns preserved**: Used identical frontmatter regex patterns from ld_deep.py (`r'^analyze:\s*(true|false)$'`, etc.) for output consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both tasks completed on first attempt with full test pass.

## User Setup Required

None - no external service configuration required. Pure code refactoring.

## Next Phase Readiness

- Deep-reading queue scanning unified under canonical `scan_library_records()` in _utils.py
- Both callers (deep_reading.py, ld_deep.py) delegate to shared function
- Ready for Phase 16 (TTY enhancement) or Phase 17 (dead code removal / unused import cleanup)
- `validate_ocr_meta()` and `load_export_rows()` imports in deep_reading.py are now unused -- deferred to Phase 17
- `_paperforge_paths()` and `_read_json()` in ld_deep.py may be unused by other callers -- deferred to Phase 17

## Self-Check: PASSED

All files and commits verified:
- `paperforge/worker/_utils.py` -- FOUND, exports scan_library_records and _resolve_formal_note_path
- `paperforge/worker/deep_reading.py` -- FOUND, imports cleanly
- `paperforge/skills/literature-qa/scripts/ld_deep.py` -- FOUND, imports via importlib
- Commit e24ef4c -- FOUND (Task 1)
- Commit d472c30 -- FOUND (Task 2)
- Import verification -- PASSED

---

*Phase: 15-deep-reading-queue-merge*
*Completed: 2026-04-27*
