---
phase: annotation-07
plan: 02
name: Wire PDF navigator into Obsidian runtime
subsystem: paperforge-plugin
tags:
  - annotation
  - pdf-navigation
  - runtime
  - test
requires:
  - annotation-07-01 (PDF jump-target resolver)
provides:
  - Runtime-callable `_openAnnotationPdf(row)` on PaperForgeStatusView
affects:
  - paperforge/plugin/main.js
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
tech-stack:
  added:
    - Mirror of extractVaultPdfPath, buildPaperPdfCandidates, resolveAnnotationPdfTarget in main.js
  patterns:
    - Conservative var/function style for main.js compatibility
    - Notice feedback for user-facing rejection
    - vault.getAbstractFileByPath verification before openLinkText
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/tests/annotation-main-runtime.test.mjs
decisions:
  - Mirrored helpers use `var`/function style matching existing main.js conventions
  - _openAnnotationPdf verifies vault file existence before opening
  - Page-badge is wired via click event listener (not mouseup or delegation)
  - Notice stubs in tests use a global noticeCalls array for assertion
duration: ~15 minutes
completed_date: 2026-06-25
---

# Phase 7 Plan 02: Wire PDF Navigator into Obsidian Runtime — Summary

Mirrored the three Plan 01 PDF jump-target helpers (`extractVaultPdfPath`, `buildPaperPdfCandidates`, `resolveAnnotationPdfTarget`) from `src/testable.js` into `main.js`, added the `PaperForgeStatusView._openAnnotationPdf(row)` method, wired page-badge clicks to call it, and extended runtime tests to cover all navigation scenarios.

## Tasks Executed

### Task 1 — Mirror PDF jump-target helpers into main.js

- Mirrored `extractVaultPdfPath`, `buildPaperPdfCandidates`, `resolveAnnotationPdfTarget` from `src/testable.js` into `main.js`
- Used `var` declarations and function style consistent with existing main.js conventions
- Added annotation comment headers indicating mirrors with source provenance
- Exposed helpers via `module.exports.__test` for runtime test access
- `node --check main.js` passes

**Commit:** `ce520ac`

### Task 2 — Add `_openAnnotationPdf(row)` method + wire page-badge click

- Added `PaperForgeStatusView._openAnnotationPdf(row)` method that:
  1. Calls `resolveAnnotationPdfTarget(row, this._currentPaperEntry)`
  2. On failure: shows `new Notice(reason, 5000)` and returns
  3. On success: verifies PDF path via `this.app.vault.getAbstractFileByPath(path)`
  4. If missing: shows Notice and returns
  5. Opens PDF via `this.app.workspace.openLinkText(linkText, '')`
- Wired page-badge `.paperforge-annotation-page-badge` click in `_renderAnnotationRows` to call `_openAnnotationPdf(row)`
- Read-only navigation — never mutates UI state, annotation state, or calls `_renderPaperMode()`/filesystem writers
- `node --check main.js` passes

**Commit:** `d2159fc`

### Task 3 — Extend runtime test stubs + add navigation tests

- Made `Notice` stub observable by capturing instances in a global `noticeCalls` array
- Imported `resolveAnnotationPdfTarget` from `module.exports.__test`
- Added `noticeCalls.length = 0` in `beforeEach`/`afterEach`
- Added **Plan 02** test suites:
  - **Direct `_openAnnotationPdf` tests:** confirmed identity + pageIndex, unmatched identity, missing vault file, null pageIndex, negative pageIndex
  - **UI state preservation:** page-badge click does not alter `_annotationUiState`
  - **Expand does not navigate:** expand button does not call `openLinkText`

**Commit:** `571e9eb`

### Task 4 — Verification tests

All test suites pass:

| Test file | Tests | Status |
|---|---|---|
| `annotation-main-runtime.test.mjs` | 35/35 | PASS |
| `annotation-navigation.test.mjs` | 47/47 | PASS |
| `annotation-bridge.test.mjs` | 40/40 | PASS |
| `annotation-section-dom.test.mjs` | 15/15 | PASS |
| **Total** | **137/137** | **ALL PASS** |

## Deviations from Plan

None — plan executed exactly as written.

## Verification

### Syntax check

```bash
node --check main.js
# PASS
```

### Test results

```bash
# focused runtime tests (35)
npm test -- tests/annotation-main-runtime.test.mjs   # 35/35 pass

# regression suites (102)
npm test -- tests/annotation-navigation.test.mjs     # 47/47 pass
npm test -- tests/annotation-bridge.test.mjs          # 40/40 pass
npm test -- tests/annotation-section-dom.test.mjs    # 15/15 pass
```

## Self-Check: PASSED

- [x] `main.js` — mirrored three helpers present and parsable
- [x] `main.js` — `_openAnnotationPdf` method present on prototype
- [x] `main.js` — page-badge click listener wired in `_renderAnnotationRows`
- [x] `main.js` — helpers exposed in `module.exports.__test`
- [x] `tests/annotation-main-runtime.test.mjs` — Notice capture stubs present
- [x] `tests/annotation-main-runtime.test.mjs` — Plan 02 test suites added
- [x] All 137 tests pass across all annotation test files
- [x] `node --check main.js` passes
