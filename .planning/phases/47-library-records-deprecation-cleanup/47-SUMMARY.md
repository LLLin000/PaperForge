---
phase: 47-library-records-deprecation-cleanup
plan: 001-002
subsystem: cleanup
tags: library-records, deprecation, cleanup, refactor, documentation

requires:
  - phase: 46-index-path-resolution
    provides: config-resolved paths across 5 workspace fields
  - phase: 44-documentation-update
    provides: primary skill files cleaned (command set A)

provides:
  - Zero library-records references in Python production code (6 files)
  - Zero library-records references in user-facing documentation (10 command files)
  - Updated post-install instructions with single-command workflow
  - Fixed hardcoded Literature/ references in docstrings and labels
  - Removed dead code (parse_existing_library_record function + call site)
  - Removed stale records key from ld_deep._paperforge_paths()
  
affects: Phase 48 (Textual TUI Removal), Phase 49 (Module Hardening)

tech-stack:
  added: []
  patterns:
    - Docstrings use {variable}/ references instead of hardcoded path literals
    - Command files describe formal-note-only workflows
    - User-facing labels use generic "literature" not hardcoded "Literature/"

key-files:
  modified:
    - paperforge/worker/status.py (stale-record scan path + output label)
    - paperforge/worker/sync.py (dead code removal + docstring fixes)
    - paperforge/worker/repair.py (docstring update)
    - paperforge/worker/discussion.py (docstring with variable reference)
    - paperforge/worker/setup_wizard.py (post-install single-command workflow)
    - paperforge/skills/literature-qa/scripts/ld_deep.py (records key removal)
    - command/pf-*.md (5 files, library-records purged)
    - paperforge/command_files/pf-*.md (5 files, library-records purged)
    - tests/test_ld_deep_config.py (updated for removed records key)

key-decisions:
  - "Scanned <control> dir instead of <control>/library-records/ for stale records (latter no longer exists)"
  - "Used deprecation notice text instead of silent removal of --selection/--index documentation (users migrating from v1.8 need guidance)"
  - "Updated tests rather than skipping them — removed records key assertion"

patterns-established:
  - "Command file edits applied identically to both command/ and paperforge/command_files/ copies"
  - "Post-install text describes single paperforge sync workflow with deprecation footnote"

requirements-completed: [LEGACY-01, LEGACY-02, LEGACY-03, LEGACY-04, LEGACY-05, LEGACY-06, LEGACY-07]

duration: 18min
completed: 2026-05-07
---

# Phase 47: Library-Records Deprecation Cleanup Summary

**Zero residual library-records references across 6 Python source files, 10 command file copies, and 1 post-install instruction block — all production code and user-facing documentation now describes formal-note-only workflows**

## Performance

- **Duration:** 18 min
- **Started:** 2026-05-07T18:00:00Z (approx)
- **Completed:** 2026-05-07T18:18:00Z (approx)
- **Tasks:** 4 (5 commits)
- **Files modified:** 16

## Accomplishments

- Removed dead `parse_existing_library_record()` function and dead `record_path` construction from `sync.py` (LEGACY-02)
- Purged `"records"` key from `ld_deep.py` `_paperforge_paths()` return dict (LEGACY-03)
- Fixed stale-record detection in `status.py` to scan `<control>` directory instead of nonexistent `library-records/` (LEGACY-01)
- Updated output label from `library_records` to `formal_notes` in `status.py` (LEGACY-01)
- Fixed `repair.py` docstring from "Scan library-records" to "Scan formal literature notes" (LEGACY-04)
- Replaced hardcoded `"Literature/"` docstring references with `{literature_dir}/` variable patterns in `discussion.py` and `sync.py` (LEGACY-07)
- Updated `setup_wizard.py` post-install text to single-command workflow (LEGACY-05)
- Purged all library-records references from 10 command file copies across `command/` and `paperforge/command_files/` (LEGACY-06)
- Updated `test_ld_deep_config.py` to reflect removed `records` key from `_paperforge_paths()`

## Task Commits

| # | Plan | Task | Commit | Description |
|---|------|------|--------|-------------|
| 1 | 47-001 | Task 1 | `8f02fa7` | Purge stale-records from status.py, repair.py, ld_deep.py, discussion.py |
| 2 | 47-001 | Task 2 | `bacf8ad` | Remove dead parse_existing_library_record, fix Literature/ docstrings |
| 3 | 47-002 | Task 1 | `b9849cb` | Update setup_wizard.py post-install to single-command workflow |
| 4 | 47-002 | Task 2 | `1548de2` | Purge library-records from all 10 command file copies |
| 5 | (test fix) | | `6402ca5` | Update ld_deep tests for removed records key |

## Files Modified

- `paperforge/worker/status.py` — Stale-record detection scans control dir; output label uses `formal_notes`
- `paperforge/worker/sync.py` — Dead function/call removed; docstrings use `<literature_dir>/`
- `paperforge/worker/repair.py` — Docstring updated to "Scan formal literature notes"
- `paperforge/worker/discussion.py` — Docstring uses `{literature_dir}/` variable reference
- `paperforge/worker/setup_wizard.py` — Post-install step 3 describes single `paperforge sync`
- `paperforge/skills/literature-qa/scripts/ld_deep.py` — `records` key removed from return dict
- `command/pf-sync.md` — Restructured for single-command workflow; library-records output removed
- `command/pf-ocr.md` — Library-records replaced with formal-note references
- `command/pf-status.md` — Library-records path/count removed from output
- `command/pf-paper.md` — Library-record prerequisite replaced with formal notes
- `command/pf-deep.md` — Library-record references replaced throughout
- `paperforge/command_files/pf-*.md` — Identical changes to mirror copies (5 files)
- `tests/test_ld_deep_config.py` — Updated expected keys for removed `records`

## Decisions Made

- **control dir scan**: Changed stale-record detection from `paths.get("library_records")` to `paths.get("control")` — scans the control directory root for any leftover `.md` files since the `library-records/` subdirectory no longer exists.
- **Deprecation notice**: In pf-sync.md and setup_wizard.py, retained text mentioning that `--selection` and `--index` are deprecated, guiding users migrating from v1.8 rather than silently removing all references.
- **Test update**: Rather than skipping or deleting the ld_deep test, removed only the `records` key assertions and updated docstrings.

## Deviations from Plan

None - plan executed exactly as written. All LEGACY requirements (01-07) completed.

### Pre-existing Test Failures (not fixed)

Two pre-existing OCR state machine test failures were discovered:
- `test_retry_exhaustion_becomes_error` — expects `"error"` but gets `"blocked"`
- `test_full_cycle_from_pending_to_done` — expects `"done"` but gets `"queued"`

These are unrelated to library-records cleanup and existed prior to these changes. Logged for Phase 49 (Module Hardening) attention.

## Issues Encountered

- File encoding: `paperforge/skills/literature-qa/scripts/ld_deep.py` and other files contain UTF-8 Chinese characters, requiring explicit `encoding="utf-8"` when reading via Python on Windows.
- PowerShell encoding: Chinese characters in terminal output caused encoding issues during verification — mitigated by using Python scripts with explicit encoding.
- Busy filesystem: One edit to `paperforge/command_files/pf-ocr.md` returned a transient "Busy" error; the edit was successfully applied on retry.

## Next Phase Readiness

Phase 48 (Textual TUI Removal) is unblocked — all LEGACY requirements complete. Two pre-existing OCR test failures noted for Phase 49 triage.

---

*Phase: 47-library-records-deprecation-cleanup*
*Completed: 2026-05-07*

## Self-Check: PASSED

- All 16 modified files verified to exist
- All 5 commits verified in git log (`8f02fa7`, `bacf8ad`, `b9849cb`, `1548de2`, `6402ca5`)
- Zero `library_records` references confirmed across all production Python files
- Zero `library.record` references confirmed across all 10 command files
- 478/482 tests passing (2 pre-existing OCR failures unrelated)
