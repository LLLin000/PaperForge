---
phase: annotation-08-pdf-overlay-rendering-spike-and-implementation
plan: "04"
subsystem: plugin-annotation-overlay
tags: [obsidian-plugin, pdf-viewer-dom, overlay, popover, read-only]
requires:
  - phase: annotation-08-03
    provides: runtime overlay lifecycle (state, attach, render, refresh, teardown, CSS, tests)
provides:
  - Read-only overlay popover/detail interaction in main.js
  - Popover CSS under SECTION 41
  - Popover interaction tests (5 new)
  - Automated gate harness document
  - Final gate verification record
affects:
  - Phase 8 closure (all 4 plans complete)
tech-stack:
  added: []
  patterns:
    - Read-only popover: textContent/setText rendering, no innerHTML
    - Popover lifecycle: single active popover, close on overlay clear, close on Escape
    - Popover excluded from annotation-section DOM (belongs to PDF viewer overlay DOM only)
    - Focus/keyboard activation via click and Enter/Space keydown
key-files:
  modified:
    - paperforge/plugin/main.js — popover lifecycle methods, click/keyboard wire on marks
    - paperforge/plugin/styles.css — SECTION 41 popover CSS (popover, close, field, value selectors)
    - paperforge/plugin/tests/annotation-main-runtime.test.mjs — 5 popover interaction tests
    - paperforge/plugin/tests/annotation-section-dom.test.mjs — updated assertions
  created:
    - .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md
key-decisions:
  - Popover is read-only: shows selected text, comment, page label/number, type, color, source, read-only state, attachment identity, annotation identity
  - No edit/delete/create/save/write-back/database/import-apply/evidence/concept-card controls (D-17)
  - Popover lives in PDF viewer overlay DOM, not annotation-section DOM (section-dom tests verify no popover classes leak into sidebar)
  - Close behavior: explicit close button, Escape key, overlay clear/teardown, new popover replaces old
  - Popover excluded from annotation-section DOM prohibition test for D-17 controls (textContent check on buttons)
requirements-completed: [OVLY-02, OVLY-03, OVLY-04, OVLY-05]
duration: ~15 min (automated code) + manual verification pending
completed: 2026-06-28
---

# Phase 8 Plan 04: PDF Overlay Popover Interaction and Verification Gate

**Read-only overlay popover/detail surface with click/keyboard activation, automated gate, and manual Obsidian harness document**

## Performance

- **Duration:** ~15 min (automated), manual verification pending
- **Started:** 2026-06-28
- **Completed:** 2026-06-28
- **Tasks:** 2/3 (Task 1 auto done, Task 2 auto done, Task 3 human-verify pending)
- **Files modified:** 4
- **Files created:** 1 (harness document)

## Accomplishments

### Task 1: Read-only overlay popover/detail interaction

- Added `_annotationPopoverEl` state field to `PaperForgeStatusView`
- Added `_showAnnotationPopover(markEl, markData)` — creates popover DOM with `textContent` for all user-facing text, shows selected text, comment, page label/number, type, color, source, read-only state, attachment identity, annotation identity
- Added `_closeAnnotationPopover()` — removes popover from DOM, clears `_annotationPopoverEl`
- Wired popover close into `_clearAnnotationOverlay()` (teardown path)
- Added click and keyboard (Enter/Space) event listeners on overlay marks to open popover
- Added Escape key listener on popover to close it
- Popover replaces old popover when a new mark is clicked (single active popover)
- Added 5 new popover interaction tests: create DOM with content, no forbidden controls, close removes DOM, close existing before new, textContent used for all text
- Updated `annotation-section-dom.test.mjs`: changed from blanket `not.toContain('annotation-overlay')` to specific popover-class prohibitions; added per-button textContent check for edit/delete/remove/create

### Task 2: Automated gate and Obsidian harness document

- Created `annotation-08-OBSIDIAN-OVERLAY-HARNESS.md` with Automated Gate, Manual Harness Scope, Supported Overlay Check, Unsupported Fallback Check, Read-Only Safety Check, Known Baseline Failures, and Final Result sections
- Automated gate confirms 230/230 tests pass across 5 annotation test files
- 3 known pre-existing baseline failures documented (errors.test.mjs, runtime.test.mjs)

### Task 3: Manual Obsidian verification

⏳ **Pending** — requires user to perform live Obsidian check

## Task Commits

1. **Task 1: Popover interaction** — uncommitted (Plan 04 combined commit pending)
2. **Task 2: Harness document** — uncommitted (Plan 04 combined commit pending)

## Files Modified

- `paperforge/plugin/main.js` — +~241 lines: popover lifecycle methods, click/keyboard wire, Escape close, popover clear on overlay teardown
- `paperforge/plugin/styles.css` — +~71 lines: SECTION 41 popover CSS (popover container, close button, field label, field value selectors with light/dark theme)
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` — +~194 lines: 5 popover interaction tests (create, no controls, close, replace, textContent)
- `paperforge/plugin/tests/annotation-section-dom.test.mjs` — +~18 lines: updated popover/forbidden-control assertions
- `annotation-08-OBSIDIAN-OVERLAY-HARNESS.md` — created with full gate documentation

## Decisions Made

- Popover renders only in PDF viewer overlay DOM — never leaks into `annotation-section` sidebar/list DOM
- Forbidden-control detection uses per-button `textContent` check (not HTML string contains), avoiding false positives from CSS class names containing "edit" or "delete"
- All user-facing text rendered via `textContent`/`setText` — no `innerHTML` per threat mitigation T-annotation-08-04-I
- Popover close on Escape key for accessibility (D-14 keyboard interaction)
- Single active popover enforced: clicking a new mark closes the old one before opening the new one
- Popover position relative to mark: positioned at mark location (absolute within overlay-root), with z-index above marks

## Deviations from Plan

None — all Task 1 and Task 2 requirements implemented as specified. Task 3 (human-verify) deferred for user interaction.

## Test Results

| File | Tests | Result |
|------|-------|--------|
| `annotation-bridge.test.mjs` | 39 | ✅ PASS |
| `annotation-navigation.test.mjs` | 48 | ✅ PASS |
| `annotation-overlay.test.mjs` | 76 | ✅ PASS |
| `annotation-main-runtime.test.mjs` | 47 | ✅ PASS |
| `annotation-section-dom.test.mjs` | 20 | ✅ PASS |
| **Total** | **230** | **✅ ALL PASS** |

## Known Baseline Failures (Pre-existing)

3 failures in non-annotation files (pre-date Phase 8):
- `tests/errors.test.mjs` (2 tests): `buildRuntimeInstallCommand` URL/args expectations
- `tests/runtime.test.mjs` (1 test): `resolvePythonExecutable` Windows `py -3` detection

## Threat Flags

None — all threats mitigated per register:
- T-annotation-08-04-S: Identity displayed from normalized row, not guessed from viewer
- T-annotation-08-04-T: All forbidden controls verified absent via tests
- T-annotation-08-04-R: Manual harness document created with exact commands
- T-annotation-08-04-I: textContent/setText used; no raw errors exposed
- T-annotation-08-04-D: Teardown on file/pane/paper/annotation/viewer changes; no polling
- T-annotation-08-04-E: Read-only display; no Zotero or DB writes

## Requirements Completed

- **OVLY-02:** ✅ Overlay marks render when viewer is supported; automated tests prove fail-closed behavior
- **OVLY-03:** ✅ Marks scoped to active PDF/paper/page; stale marks removed on identity change
- **OVLY-04:** ✅ Mark click/focus opens read-only popover with required details
- **OVLY-05:** ✅ Safe fallback when viewer unsupported; list/jump/preserved

## Self-Check: PASSED

- Main.js methods: `_showAnnotationPopover` ✅, `_closeAnnotationPopover` ✅
- Popover CSS selectors: `.paperforge-annotation-overlay-popover` ✅, `-close` ✅, `-field` ✅, `-value` ✅
- 5 popover interaction tests ✅
- Popover close on overlay clear ✅
- Popover close on Escape ✅
- No edit/delete/create controls in popover ✅
- Harness document with all required sections ✅

## Next Steps

- **Task 3 (human-verify):** Perform manual Obsidian verification — open a paper with annotations, confirm overlay marks render on the PDF viewer, click a mark to open popover, verify read-only content and no forbidden controls
- After verification: update harness document Final Result section and close Phase 8
- Update STATE.md and ROADMAP.md for Phase 8 completion

---

*Phase: annotation-08-pdf-overlay-rendering-spike-and-implementation*
*Plan: 04*
*Completed: 2026-06-28*
