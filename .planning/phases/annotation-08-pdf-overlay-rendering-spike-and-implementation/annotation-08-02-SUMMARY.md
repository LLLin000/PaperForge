---
phase: annotation-08-pdf-overlay-rendering-spike-and-implementation
plan: "02"
subsystem: plugin
tags:
  - overlay
  - annotation
  - vitest
  - pdf
  - fail-closed

requires:
  - phase: annotation-08-01
    provides: PDF viewer attach contract (supported), coordinate contract, positionJson shape
provides:
  - Pure overlay helper functions in `src/testable.js` for state, position parsing, color, marks, and popover view-models
  - 76 focused Vitest tests in `annotation-overlay.test.mjs` covering fail-closed and valid paths
affects:
  - annotation-08-03 (runtime overlay rendering)
  - annotation-08-04 (popover interaction)

tech-stack:
  added: []
  patterns:
    - Pure fail-closed overlay helpers with stable {ok, reason} result shape
    - Session-only overlay state (no persistence, no settings)
    - Non-mutating mark builder using resolveAnnotationPdfTarget identity guard
    - Read-only popover view-model with no edit/delete/create controls

key-files:
  created:
    - paperforge/plugin/tests/annotation-overlay.test.mjs
  modified:
    - paperforge/plugin/src/testable.js

key-decisions:
  - "Overlay mark builder reuses resolveAnnotationPdfTarget() for PDF identity guard instead of duplicating attachment-matching logic"
  - "default highlight color #ffd400 per D-06, returned from normalizeAnnotationColor() when annotation color is missing, invalid, or unrecognized"
  - "Position parser validates each rect field individually (x, y, w, h must be finite non-negative numbers) — any invalid rect fails the entire positionJson to avoid partial rendering"
  - "buildAnnotationOverlayMarks returns stable status strings ('disabled', 'empty', 'rendered') for callers to determine overlay state without rechecking conditions"
  - "buildAnnotationPopoverViewModel exposes selectedText, comment, pageLabel, pageNumber, type, color, source, isReadonly, attachmentKey, annotationKey — no write-back, database, or evidence fields"

patterns-established:
  - "Overlay helpers follow the same fail-closed pattern as existing annotation helpers: return { ok: boolean, reason: string|null } with friendly human-readable reasons, never throw"
  - "Test fixtures use property-level Object.assign merging instead of top-level spread to avoid losing defaults when overriding sub-objects"
  - "Color normalization preserves original case for hex values but lowercases named colors"

requirements-completed:
  - OVLY-02
  - OVLY-03
  - OVLY-04
  - OVLY-05

duration: 23min
completed: 2026-06-28
---

# Phase Annotation 08 Plan 02: Pure overlay helpers with focused Vitest coverage

**Five pure helper exports (createDefaultAnnotationOverlayState, parseAnnotationPositionJson, normalizeAnnotationColor, buildAnnotationOverlayMarks, buildAnnotationPopoverViewModel) in src/testable.js with 76 focused Vitest tests, all fail-closed and non-mutating**

## Performance

- **Duration:** 23 min
- **Started:** 2026-06-28T16:10:00Z
- **Completed:** 2026-06-28T16:33:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- 5 exported overlay helpers added to `src/testable.js` — all fail-closed, non-throwing, with stable friendly reasons
- `createDefaultAnnotationOverlayState()` — fresh session-local state with status, paperKey, pdfPath, viewerAttached, activePopoverId
- `parseAnnotationPositionJson()` — validates positionJson JSON with rect array; checks each rect for finite non-negative x/y/w/h; returns `{ ok: false, reason }` for missing/invalid/empty/negative/non-finite data
- `normalizeAnnotationColor()` — passes through hex (#rgb/#rrggbb/#rrggbbaa), rgb/rgba, and common named colors; falls back to restrained default yellow (#ffd400) per D-06
- `buildAnnotationOverlayMarks()` — filters annotation rows through resolveAnnotationPdfTarget() identity guard, matches active PDF path, validates pageIndex and positionJson before constructing marks; returns stable `{ ok, status, marks, skipped, reason }` shape
- `buildAnnotationPopoverViewModel()` — read-only popover data with selectedText, comment, page, source, isReadonly, and no edit/delete/create/write-back/database/evidence controls
- 76 new tests in `annotation-overlay.test.mjs` covering valid rects, invalid JSON, empty rects, missing page, wrong attachment, supplemental mismatch, active PDF mismatch, non-mutation, friendly reasons without stack traces, and read-only popover contract
- All 218 tests pass across 5 annotation test files (overlay, navigation, bridge, runtime, section-dom)

## Task Commits

Each task was committed atomically:

1. **Task 1: Overlay state, position parsing, and color helpers** — `b6ba000` (feat)
2. **Task 2: Overlay mark and popover view-model helpers** — `d7acab9` (feat)

## Files Created/Modified

- `paperforge/plugin/src/testable.js` — Added 5 overlay helpers + DEFAULT_OVERLAY_HIGHLIGHT_COLOR constant + exports (~250 lines)
- `paperforge/plugin/tests/annotation-overlay.test.mjs` — New test file with 76 tests across all 5 helpers (~380 lines)

## Decisions Made

- Reused `resolveAnnotationPdfTarget()` for PDF identity guard rather than duplicating attachment-matching logic — maintains single source of truth
- Test fixtures use `Object.assign` property-level merging for `makeAnnotationRow()` to prevent sub-object overrides from dropping defaults (e.g., positionJson when overriding pdfLocation)
- Color normalization preserves hex case but lowercases named colors — hex case may carry semantic meaning in annotation source data
- Mark builder validates all rect fields individually; any invalid rect fails the entire row to avoid partial/wrong rendering

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Test fixture design: Initial top-level spread (`...o`) in `makeAnnotationRow()` caused `positionJson` to be dropped when `pdfLocation` was partially overridden. Fixed by switching to `Object.assign` property-level merging so overrides only affect specified fields. This was a test-harness bug, not a production code issue.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All pure overlay helpers are exported and tested, ready for the runtime overlay attach/teardown layer in Plan 03
- Plan 03 can import `buildAnnotationOverlayMarks`, `buildAnnotationPopoverViewModel`, and state helpers directly from `src/testable.js`
- The identity guard and fail-closed patterns are proven: 218 passing tests across 5 test files

## Known Stubs

None — all helpers return complete results with no hardcoded empty placeholders, "coming soon" text, TODO markers, or stubs that would prevent downstream overlay rendering.

## Threat Surface Scan

No new threat flags. All threat register mitigations are implemented:
- T-annotation-08-02-S: `buildAnnotationOverlayMarks()` calls `resolveAnnotationPdfTarget()` before creating marks
- T-annotation-08-02-T: All helpers are non-mutating (verified by tests)
- T-annotation-08-02-I: Reason strings are stable, friendly, and tested to exclude stack traces, raw JSON, shell output, and absolute paths
- T-annotation-08-02-D: `parseAnnotationPositionJson()` validates shape and bounds per rect, skips bad rows instead of throwing or looping
- T-annotation-08-02-E: `buildAnnotationPopoverViewModel()` exposes read-only display fields only
- T-annotation-08-02-SC: No package installs added — using existing Vitest/jsdom stack

## Self-Check: PASSED

- `paperforge/plugin/src/testable.js` — exists, `node --check` passes
- `paperforge/plugin/tests/annotation-overlay.test.mjs` — exists, 76/76 tests pass
- Commit `b6ba000` — verified in git log
- Commit `d7acab9` — verified in git log
- Known regression test counts— 47 navigation + 40 bridge + 20 section-dom + 35 runtime = all passing
- No STATE.md, ROADMAP.md, or shared orchestrator artifacts modified

---

*Phase: annotation-08-pdf-overlay-rendering-spike-and-implementation*
*Plan: 02 — Pure overlay helpers*
*Completed: 2026-06-28*
