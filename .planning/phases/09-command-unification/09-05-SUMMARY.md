---
phase: 09-command-unification
plan: "05"
subsystem: docs
tags: [cli, documentation, commands, paperforge, sync, ocr]

requires:
  - phase: 09-command-unification
    provides: New pf-* command docs created and old lp-/ld- docs deleted
provides:
  - Updated AGENTS.md with unified command references
  - Updated README.md with unified command references
  - Updated docs/INSTALLATION.md and docs/setup-guide.md
  - Updated setup_wizard.py output text
  - Updated pipeline/worker/scripts/literature_pipeline.py output text
  - Updated tests/test_command_docs.py to validate new pf-* docs
  - Updated tests/test_smoke.py docstring
affects: [user-onboarding, agent-commands, cli-interface]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - AGENTS.md
    - README.md
    - docs/INSTALLATION.md
    - docs/setup-guide.md
    - setup_wizard.py
    - pipeline/worker/scripts/literature_pipeline.py
    - tests/test_command_docs.py
    - tests/test_smoke.py

key-decisions:
  - "Keep old command references only in migration tables/sections, not in primary documentation"
  - "Old commands (selection-sync, index-refresh, ocr run, /LD-*) still work at CLI level for backward compatibility"
  - "Add TestUnifiedCommandsInUserDocs to prevent regression of old commands in primary docs"

patterns-established: []

requirements-completed: []

---

# Phase 09 Plan 05: Update AGENTS.md and Tests for New Command Names Summary

**Updated all user-facing documentation and tests to reference the unified `paperforge sync`, `paperforge ocr`, and `/pf-*` command interface, with v1.1→v1.2 migration notes and backward-compatible CLI aliases.**

## Performance

- **Duration:** 15 min
- **Started:** 2025-04-24T00:00:00Z
- **Completed:** 2025-04-24T00:15:00Z
- **Tasks:** 1
- **Files modified:** 8

## Accomplishments
- Updated AGENTS.md with unified command references and v1.1→v1.2 migration table
- Updated README.md, docs/INSTALLATION.md, docs/setup-guide.md with new commands
- Updated setup_wizard.py next-steps output to use `paperforge sync` and `paperforge ocr`
- Updated literature_pipeline.py deep-reading output to use `paperforge ocr` and `/pf-deep`
- Rewrote tests/test_command_docs.py to validate new `pf-*` command docs
- Added TestUnifiedCommandsInUserDocs to prevent old command regression in primary docs

## Task Commits

1. **Task 5: Update user-facing docs** - `62ec894` (docs)
2. **Task 5: Update tests** - `b140398` (test)
3. **Task 5: Update setup wizard and worker** - `d04100d` (chore)

## Files Created/Modified
- `AGENTS.md` - Updated command reference table, data flow diagram, usage guide, command cheat sheet, FAQ, and added v1.1→v1.2 migration section
- `README.md` - Updated core commands and agent command examples
- `docs/INSTALLATION.md` - Updated next-steps to use unified commands
- `docs/setup-guide.md` - Updated workflow commands and FAQ
- `setup_wizard.py` - Updated DoneStep next-steps and command tables
- `pipeline/worker/scripts/literature_pipeline.py` - Updated deep-reading output text
- `tests/test_command_docs.py` - Rewrote to reference new pf-* docs, added unified command regression tests
- `tests/test_smoke.py` - Updated docstring for sync command

## Decisions Made
- Keep old command references only in migration tables/sections, not in primary documentation flow
- Old CLI commands still function for backward compatibility (handled in cli.py), but docs only show new names
- Add automated tests to prevent accidental re-introduction of old command names in primary user docs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Two pre-existing test failures in `test_pdf_resolver.py` unrelated to this task (attachment path normalization)
- All documentation and CLI-related tests pass (178/180 tests pass, 2 skipped)

## Next Phase Readiness
- Task 5 complete; Phase 09 Task 6 (Verification & Cleanup) can proceed
- All user-facing docs now consistent with unified command interface

---
*Phase: 09-command-unification*
*Completed: 2025-04-24*

## Self-Check: PASSED

- [x] AGENTS.md updated with new command references
- [x] README.md updated with new command references
- [x] docs/INSTALLATION.md updated
- [x] docs/setup-guide.md updated
- [x] setup_wizard.py updated
- [x] pipeline/worker/scripts/literature_pipeline.py updated
- [x] tests/test_command_docs.py updated and passes (19/19)
- [x] tests/test_smoke.py updated and passes (14/14)
- [x] All commits verified (62ec894, b140398, d04100d)
- [x] SUMMARY.md created
