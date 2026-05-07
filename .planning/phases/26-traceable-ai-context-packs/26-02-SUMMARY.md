---
phase: 26-traceable-ai-context-packs
plan: 02
subsystem: cli
tags: [context-pack, canonical-index, json, provenance, ai-readiness]

# Dependency graph
requires:
  - phase: 25-surface-convergence-doctor-repair
    provides: canonical index format with lifecycle, health, maturity fields
  - phase: 23-canonical-asset-index-safe-rebuilds
    provides: atomic_write_index, build_envelope, read_index helpers
  - phase: 24-derived-lifecycle-health-maturity
    provides: compute_lifecycle, compute_health, compute_maturity, compute_next_step
provides:
  - paperforge context CLI command (single-key, --domain, --collection, --all)
  - context module in commands/context.py with _format_context_entry
  - Provenance trace (9 paths per entry: paper_root, main_note_path, fulltext_path, etc.)
  - AI readiness explanation (blocking_factors + blocking_explanation when lifecycle != ai_context_ready)
affects:
  - 26-03 (plugin Copy Context actions — consumes context command output)
  - Agent skills (literature-qa can call paperforge context <key> for AI context)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI command module with run(args) -> int entry point"
    - "Lazy import of read_index inside run() to avoid circular deps"
    - "_format_context_entry() wraps raw index entry with _provenance and _ai_readiness"
    - "Single-key outputs dict, multi-entry outputs JSON array"

key-files:
  created:
    - paperforge/commands/context.py
    - tests/test_context.py
  modified:
    - paperforge/cli.py
    - paperforge/commands/__init__.py

key-decisions:
  - "D-01: Canonical index entry IS the AI context — no separate context pack format"
  - "D-06: Always output JSON, no --json flag needed"
  - "D-09: Provenance is inherent — entry paths sufficient, no extra layer"
  - "D-10: No new dependencies — uses existing read_index from asset_index.py"

patterns-established:
  - "Context command wraps entry with _provenance (9 path keys) and _ai_readiness (lifecycle, blocking_factors, blocking_explanation)"
  - "Blocking explanation built from has_pdf, ocr_status, deep_reading_status, and health fields"
  - "Test pattern: _write_index() helper creates mock canonical index, capsys/print capture for output assertions"

requirements-completed:
  - AIC-02
  - AIC-03
  - AIC-04

# Metrics
duration: 60 min
completed: 2026-05-04
---

# Phase 26 Plan 02: Traceable AI Context Packs — CLI Context Command

**paperforge context CLI command that reads the canonical index and outputs JSON context entries with provenance traces and AI readiness explanations**

## Performance

- **Duration:** 60 min
- **Started:** 2026-05-04T12:43:00Z
- **Completed:** 2026-05-04T12:46:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Created `paperforge/commands/context.py` with `run(args)` supporting four access modes: single-key (`paperforge context <key>`), `--domain`, `--collection`, and `--all`
- `_format_context_entry()` wraps each canonical index entry with `_provenance` (9 source path keys) and `_ai_readiness` (lifecycle, blocking factors, blocking explanation)
- Wired the context command into the CLI: subparser with positional `key` (nargs="?"), `--domain`, `--collection`, `--all` flags, and dispatch in `main()`
- Registered `"context"` in `_COMMAND_REGISTRY` for dynamic module loading
- Wrote 14 comprehensive tests covering all modes, provenance traceability, blocking explanations at different lifecycle stages, missing key errors, empty filter results, and missing index handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Create context command module with single-key output and provenance** - `f933075` (feat)
2. **Task 2: Wire context command into CLI (subparser + main dispatch + command registry)** - `ace77d5` (feat)
3. **Task 3: Write tests for context command modes, filtering, and provenance output** - `09dab7e` (test)

**Plan metadata:** (pending — committed after SUMMARY + state updates)

## Files Created/Modified

- `paperforge/commands/context.py` - Core context command module with `run(args)`, `_format_context_entry()`, four access modes
- `paperforge/cli.py` - Added context subparser (key, --domain, --collection, --all) and dispatch in `main()`
- `paperforge/commands/__init__.py` - Added `"context": "paperforge.commands.context"` to command registry
- `tests/test_context.py` - 14 tests covering all command modes, provenance, and AI readiness

## Decisions Made

- **D-01 followed:** Canonical index entry IS the AI context, no separate pack format
- **D-06 followed:** Always output JSON, no `--json` flag
- **D-09 followed:** Provenance is inherent — `_provenance` block provides all 9 path keys from the entry itself
- **D-10 followed:** No new dependencies — only uses existing `read_index` from `asset_index.py`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 26-01 (plugin Copy Context actions) can now consume the `paperforge context` command and its JSON output
- Plan 26-03 (plugin integration) depends on the context command existing
- All three commits are on `milestone/v1.6-ai-ready-asset-foundation`

## Self-Check: PASSED

- [x] All 4 created files exist on disk
- [x] All 3 commits present in git log (f933075, ace77d5, 09dab7e)
- [x] All 14 tests pass (`pytest tests/test_context.py -q`)

---

*Phase: 26-traceable-ai-context-packs*
*Completed: 2026-05-04*
