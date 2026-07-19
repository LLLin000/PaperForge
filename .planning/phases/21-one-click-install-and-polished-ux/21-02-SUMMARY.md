---
phase: 21-one-click-install-and-polished-ux
plan: 02
subsystem: plugin
tags: [obsidian, plugin, subprocess, spawn, chinese-ui, error-handling]
requires:
  - phase: 21-one-click-install-and-polished-ux/01
    provides: Install button, _validate(), _statusArea, CSS status classes
provides:
  - _runSetup() subprocess orchestration with spawn
  - _showNotice(), _formatSetupError(), _processSetupOutput(), _setStatus() helpers
  - Button disable/enable lifecycle with double-click prevention
  - Chinese error pattern mapping (5 patterns)
affects: []
tech-stack:
  added: []
  patterns:
    - spawn (not exec) for non-blocking subprocess with stdout streaming
    - try/finally for guaranteed button re-enable
    - Pattern-based error mapping to user-facing messages
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
key-decisions:
  - "Use spawn (not exec): streams stdout line-by-line for step progress"
  - "Use --headless (not --non-interactive): correct CLI flag name"
  - "Pass API key via --paddleocr-key flag (not env var PADDLEOCR_API_TOKEN)"
  - "Explicit directory args override headless_setup built-in defaults"
  - "Error messages in Chinese, raw stderr logged to console only"
requirements-completed: [INST-01, INST-02, INST-04]
duration: 5 min
completed: 2026-04-29
---

# Phase 21 Plan 02: Subprocess Orchestration & Notice Formatting

**_runSetup() subprocess spawn with Chinese error mapping, step-by-step progress updates, and double-click prevention via try/finally button lifecycle**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-29T14:43:00Z
- **Completed:** 2026-04-29T14:48:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `_runSetup(button)` async method spawns `python -m paperforge setup --headless` with explicit args
- Button disabled during execution, re-enabled in `finally` — prevents double-click
- `_showNotice()` renders success/error/progress via Obsidian Notice API with appropriate durations
- `_formatSetupError()` maps 5+ common error patterns to Chinese messages (Python not found, module missing, permission denied, path not found, timeout)
- `_processSetupOutput()` parses `[*]` / `[OK]` / `[FAIL]` step markers from stdout for real-time status updates
- `_setStatus()` updates status area with color-coded CSS class (success/error/progress)
- Raw stderr logged to console only — user never sees raw tracebacks (INST-02 compliance)
- Sidebar and commands unchanged (INST-04 verified)

## Task Commits

1. **Task 1+2: Add _runSetup() + 4 notice helpers** - `5803898` (feat)

**Plan metadata:** (final commit after summary)

## Files Created/Modified

- `paperforge/plugin/main.js` - Added `_runSetup()` (73 lines), `_showNotice()`, `_formatSetupError()`, `_processSetupOutput()`, `_setStatus()` (45 lines total)

## Decisions Made

- **spawn over exec**: `spawn` streams stdout line-by-line so `_processSetupOutput()` can show step progress. `exec` buffers all output — no intermediate feedback.
- **--headless over --non-interactive**: The CLI defines `--headless` flag. The initial draft incorrectly used `--non-interactive` — corrected per code review.
- **--paddleocr-key flag**: The `headless_setup()` function reads API key from CLI argument, not from `PADDLEOCR_API_TOKEN` env var.
- **Explicit directory args**: Plugin's defaults (20_Resources, Control) differ from headless_setup's built-in defaults (03_Resources, LiteratureControl). Must override via `--resources-dir` and `--control-dir`.
- **Error mapping patterns**: 5 patterns cover the most common failure modes for first-time users. Full error always available via `console.error()`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 21 complete — both plans delivered. One-click install button with field validation, subprocess orchestration, Chinese step-by-step feedback, and error handling. Ready for v1.5 milestone verification.

## Self-Check: PASSED

- [x] All 5 methods present in main.js (_runSetup, _showNotice, _formatSetupError, _processSetupOutput, _setStatus)
- [x] Uses --headless, not --non-interactive
- [x] INST-02: No raw error exposure in new Notice calls (uses _formatSetupError)
- [x] INST-04: Sidebar and commands preserved (PaperForgeStatusView, addCommand, addRibbonIcon)
- [x] SUMMARY.md created in plan directory

---

*Phase: 21-one-click-install-and-polished-ux*
*Completed: 2026-04-29*
