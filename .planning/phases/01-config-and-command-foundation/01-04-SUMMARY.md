---
phase: 01-config-and-command-foundation
plan: 04
subsystem: documentation
tags: [documentation, cli, paperforge, command-docs, stable-commands]

# Dependency graph
requires:
  - phase: 01-config-and-command-foundation
    provides: paperforge.json and configurable paths (plans 01-03)
provides:
  - Stable `paperforge ...` commands as primary user-facing interface
  - Placeholder-free command docs for CMD-01, CMD-02, CMD-03, CMD-04
  - Regression tests preventing unresolved-token command examples
affects: [phase-02, phase-03, phase-04]

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [TDD for docs, stable-command documentation, fallback-legacy pattern]

key-files:
  created:
    - tests/test_command_docs.py
  modified:
    - command/lp-status.md
    - command/lp-selection-sync.md
    - command/lp-index-refresh.md
    - command/lp-ocr.md
    - command/ld-deep.md
    - README.md
    - docs/INSTALLATION.md
    - docs/setup-guide.md
    - setup_wizard.py

key-decisions:
  - "Primary commands use `paperforge status|selection-sync|index-refresh|ocr run|deep-reading` instead of `python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py`"
  - "Legacy direct worker invocation kept as fallback with path resolution via `paperforge paths --json`"
  - "Test scope excludes AGENTS.md frontmatter field examples and architecture diagrams (those are not user-run examples)"

patterns-established:
  - "Stable-command-first pattern: primary doc shows `paperforge X`, secondary fallback shows resolved path construction"
  - "TDD for docs: tests verify content presence/absence before editing, ensuring regression protection"

requirements-completed: [CONF-03, CMD-01, CMD-02, CMD-03]

# Metrics
duration: 4min 28sec
completed: 2026-04-23
---

# Phase 1 Plan 4: Command Documentation Stable Commands Summary

**Stable `paperforge` CLI as primary user command interface with regression tests preventing unresolved-token regressions**

## Performance

- **Duration:** 4 min 28 sec
- **Started:** 2026-04-23T11:36:07Z
- **Completed:** 2026-04-23T11:40:35Z
- **Tasks:** 2
- **Files modified:** 9 files created/modified (1 new, 9 updated)

## Accomplishments
- User-facing command docs now show stable `paperforge status|selection-sync|index-refresh|ocr run` as primary commands
- Legacy `python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py` demoted to fallback with path-resolution instructions
- `command/ld-deep.md` updated to use `paperforge deep-reading` for queue preflight and `paperforge paths --json` for variable discovery
- `README.md`, `docs/INSTALLATION.md`, `docs/setup-guide.md`, `setup_wizard.py` all updated to prefer stable commands
- Regression test suite (`tests/test_command_docs.py`) with 15 assertions prevents future unresolved-token regressions in user-run examples

## Task Commits

Each task was committed atomically:

1. **Task 1: Add docs regression tests for stable commands** - `baa2d77` (test)
2. **Task 2: Replace unresolved path-token command examples with stable launcher commands** - `51d35d6` (feat)

**Plan metadata:** `51d35d6` (docs: complete plan)

_Note: TDD tasks may have multiple commits (test -> feat -> refactor)_

## Files Created/Modified
- `tests/test_command_docs.py` - 15-test suite verifying stable commands and no unresolved `<system_dir>` tokens in user examples
- `command/lp-status.md` - Primary command: `paperforge status`; fallback with `paperforge paths --json`
- `command/lp-selection-sync.md` - Primary: `paperforge selection-sync`
- `command/lp-index-refresh.md` - Primary: `paperforge index-refresh`
- `command/lp-ocr.md` - Primary: `paperforge ocr run`
- `command/ld-deep.md` - Queue preflight via `paperforge deep-reading`; path discovery via `paperforge paths --json`
- `README.md` - Core commands section rewritten to lead with `paperforge` commands, legacy as fallback
- `docs/INSTALLATION.md` - Installation verification now uses `paperforge paths` and `paperforge status`
- `docs/setup-guide.md` - Quick-start steps now use `paperforge selection-sync` and `paperforge index-refresh`
- `setup_wizard.py` - DoneStep now shows `pip install -e .` and `paperforge` commands as primary next steps

## Decisions Made
- Primary commands use `paperforge ...` syntax; legacy Python invocation retained as documented fallback
- Test scope carefully limited to user-run code blocks; architecture diagrams and AGENTS.md frontmatter examples excluded from unresolved-token checks (per plan TDD spec)
- `paperforge paths --json` chosen as the path-resolution mechanism for fallback commands (deterministic, machine-parseable)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - no blocking issues during execution.

## User Setup Required
None - no external service configuration required beyond existing prerequisites.

## Next Phase Readiness
- Command documentation foundation complete (CONF-03, CMD-01, CMD-02, CMD-03 satisfied)
- Phase 1 remaining plans (if any) can proceed without command doc blockers
- PaperForge CLI (`paperforge` command) must be implemented in a future plan to make the primary commands functional (currently tests verify docs only; the actual CLI module does not exist in this repo yet)

---
*Phase: 01-config-and-command-foundation*
*Completed: 2026-04-23*
