---
phase: annotation-07-pdf-jump-navigation
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-07-02
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/styles.css
    - paperforge/plugin/tests/annotation-section-dom.test.mjs
decisions:
  - Badge availability is pre-computed at render time via resolveAnnotationPdfTarget (no side effects)
  - Disabled button uses HTML `disabled` attribute so click events never fire (not just aria-disabled)
  - stopPropagation on badge click ensures expand isolation
  - Enabled badge tooltip: "Open PDF at page N"; disabled: "Annotation source PDF not available"
  - D-11: confirmed PDF + null pageIndex → badge still enabled ("Open PDF" without "at page")
  - Button reset in CSS uses border:none + cursor:pointer; :disabled uses pointer-events:none + opacity:0.5
  - :focus-visible uses 2px outline with --interactive-accent for keyboard accessibility
  - Phase 6 forbidden-navigation assertion replaced with positive jump-button assertion
  - All overlay/popover/edit/delete/write-back/database/concept prohibitions retained
duration: ~15 min
completed_date: 2026-06-28
requirements:
  - OVLY-01
---

# Phase 7 Plan 03: Page-Badge Jump Affordance — Summary

**Converted the annotation page badge from a static `<span>` to a semantic `<button>` with accessible tooltip, aria-label, disabled-state computation, compact interaction styling, and 5 new DOM regression tests proving navigation/expansion isolation.**

## Tasks Executed

### Task 1 (TDD) — Convert page badge to accessible isolated jump control

**RED phase:**
- Added `pdfLocation` to `makeAnnotationRow` fixture with defaults matching the view's entry
- Updated default `pdf_path` to realistic Zotero storage path for attachment-key matching
- Changed badge tag assertion from `'SPAN'` to `'BUTTON'` in the D-08/D-10 test
- Added 4 new badge-semantics tests: enabled tooltip/aria-label, disabled explanation, D-11 null-pageIndex, and click isolation
- Replaced D-24 "no PDF jump" negative assertion with positive badge-as-jump-button assertion
- Added D-03 isolation test: badge click leaves `expandedIds` unchanged; expand click never calls `openLinkText`

**GREEN phase:**
- Replaced `createEl('span', ...)` with `createEl('button', ...)` in `_renderAnnotationRows()`
- Pre-compute availability via `resolveAnnotationPdfTarget(row, this._currentPaperEntry)` at render time
- Enabled badge: sets `title` and `aria-label` to "Open PDF" (+ "at page N" when valid page exists)
- Disabled badge: sets `disabled=true`, `aria-disabled="true"`, title explains unavailability
- Badge click handler adds `ev.stopPropagation()` for expansion isolation
- All 5 previously-failing RED tests pass after GREEN implementation

**Commit:** `a0abbcc`

### Task 2 (auto) — Style jump states and run consolidated regressions

- Added CSS button reset (`border: none`, `cursor: pointer`, `transition`) to page badge
- Added `:hover` state using `--background-modifier-hover` and `--text-normal`
- Added `:focus-visible` keyboard accessibility ring (2px outline via `--interactive-accent`)
- Added `:disabled` state (`cursor: default`, `opacity: 0.5`, `pointer-events: none`)
- Verified all 3 required CSS tokens present via PowerShell scan

**Verification results:**

| Suite | Tests | Status |
|-------|-------|--------|
| `annotation-navigation.test.mjs` | 47/47 | PASS |
| `annotation-main-runtime.test.mjs` | 35/35 | PASS |
| `annotation-section-dom.test.mjs` | 20/20 | PASS (was 15, 5 new) |
| `annotation-bridge.test.mjs` | 40/40 | PASS |
| **Focused total** | **142/142** | **ALL PASS** |
| **Full plugin suite** | **273 pass / 3 baseline failures** | **No regression** |

Baseline failures (unchanged, unrelated to annotation):
- 2 `buildRuntimeInstallCommand` tests in `errors.test.mjs` (undef url)
- 1 `resolvePythonExecutable` test in `runtime.test.mjs` (Windows `py -3` expectation)

**Commit:** `55b1cf2`

## Deviations from Plan

None — plan executed exactly as written.

## Acceptance Criteria Verification

- [x] Page badge is the only row-level jump action (D-01: positive assertion replaces Phase 6 negative)
- [x] Tooltip, aria-label, focus-visible, and disabled semantics present (D-02)
- [x] Jump and expansion controls are independent (D-03: click isolation test in both directions)
- [x] Uncertain attachment identity renders disabled badge (D-07: `ARIA-disabled="true"`, title explains)
- [x] Invalid page data still enables navigation for confirmed PDF (D-11: null pageIndex test)
- [x] UI state (expandedIds, filters, grouping) preserved after navigation (D-13: isolation test)
- [x] No overlay, mutation, or editing behavior introduced (D-15: retained prohibition tests)

## Self-Check: PASSED

- [x] Task 1 committed at `a0abbcc` with descriptive message
- [x] Task 2 committed at `55b1cf2` with descriptive message
- [x] `node --check main.js` passes
- [x] All annotation test suites pass (142/142 focused, 273/276 full)
- [x] CSS tokens verified: `.paperforge-annotation-page-badge`, `:focus-visible`, `:disabled`
- [x] SUMMARY.md created at specified path
- [x] No STATE.md or ROADMAP.md modifications
