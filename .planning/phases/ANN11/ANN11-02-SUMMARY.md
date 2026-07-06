---
phase: ANN11
plan: "02"
name: card-lane-rendering-css-and-runtime
subsystem: canvas
tags:
  - annotation
  - canvas
  - card
  - layout
  - render
  - DOM
  - CSS
  - i18n
  - runtime
requires:
  - ANN10-02
  - ANN11-01
provides:
  - canvas/render-card-lanes
  - canvas/card-css
  - canvas/i18n
affects:
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/i18n.js
  - paperforge/plugin/main.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-render.test.mjs
  - paperforge/plugin/tests/canvas-card-dom.test.mjs
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
tech-stack:
  added:
    - i18n.js — zh/en dictionary with t() helper and detectLang()
    - styles.css card/lane section — namespaced CSS for card lane display
  patterns:
    - All annotation-derived text uses textContent, never innerHTML
    - Stable CSS geometry with max-height, overflow, gradient fade
    - CJK-safe word-break/overflow-wrap
    - No hover resize, no viewport-scaled fonts
key-files:
  created:
    - paperforge/plugin/i18n.js
  modified:
    - paperforge/plugin/src/canvas/render.js
    - paperforge/plugin/styles.css
    - paperforge/plugin/main.js
    - paperforge/plugin/src/canvas/index.js
    - paperforge/plugin/tests/canvas-render.test.mjs
    - paperforge/plugin/tests/canvas-card-dom.test.mjs
    - paperforge/plugin/tests/canvas-main-runtime.test.mjs
decisions:
  - D-01/D-02/CARD-01: Cards render with selected text preview, comment, page, color/type, source/provenance, read-only badge
  - D-03/D-21/D-22/CARD-04: No expandable details, drawers, popovers, editable forms, forbidden controls, anchors, connectors, draggable handles
  - D-04/D-18/CARD-02: Missing text renders as empty element with --empty class; long/CJK text has max-height, overflow, gradient fade via CSS
  - D-10 through D-14/CANVAS-04: 11+ distinct canvas states render correctly; ready/refreshing/stale preserve cards
  - D-15/D-16/D-17: Card lane CSS uses stable dimensions, bounded previews, CJK-safe wrapping, no viewport-scaled fonts, no hover resize
  - D-19: Read-only badge with --true/--false modifier classes, restrained styling
  - D-20: Source/provenance displayed as monospace text with identity keys
metrics:
  plan_duration_minutes: 14
  tasks_total: 3
  tasks_completed: 3
  tests_total: 405
  files_created: 1
  files_modified: 6
  commits: 4
plan_date: 2026-07-06
---

# Phase ANN11 Plan 02: Card Lane Rendering, CSS, and Runtime

Produced read-only annotation card DOM, namespaced resilient CSS, i18n labels, and guarded runtime regression after ANN10-02 pre-flight gate.

## Output

- **`render.js`** — Extended with `renderCanvasCard()`, `renderCanvasCardLanes()`, `renderCanvasRefreshing()`, updated `renderCanvasView()` dispatch for ready/refreshing/stale states with cards
- **`i18n.js`** — New zh/en dictionary with `t()` helper, `detectLang()` for card labels, placeholders, read-only badges, state copy
- **`styles.css`** — Namespaced card/lane CSS: `.paperforge-canvas-card`, `.paperforge-canvas-lane-left/right`, `.paperforge-canvas-lanes`, preview classes, read-only badge, gradient fades
- **`main.js`** — LANG.en ANN11 card labels (13 lines)
- **`index.js`** — Exports `renderCanvasCard`, `renderCanvasCardLanes`, `renderCanvasRefreshing`
- **Tests**: 405 tests across 9 files (all pass)

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| Task 2 RED (test) | `80a322a` — test(ANN11-02): add failing card lane DOM and render tests | ✅ |
| Task 2 GREEN (feat) | `7d43f1b` — feat(ANN11-02): render read-only card lanes | ✅ |
| Task 3 RED (test) | `6d0e4eb` — test(ANN11-02): add CSS resilience, i18n, runtime tests | ✅ |
| Task 3 GREEN (feat) | `5fcf3b0` — feat(ANN11-02): add resilient card/lane CSS and i18n | ✅ |

## Task 1: Pre-flight ANN10-02 Runtime Gate

Verified ANN10-02 Reading Canvas wiring before any file edit:
- ✅ `VIEW_TYPE_PAPERFORGE_READING_CANVAS` constant
- ✅ `PaperForgeReadingCanvasView` class with view registration
- ✅ Command wiring (`paperforge-open-reading-canvas`)
- ✅ Paper-panel button with explicit paperKey path
- ✅ CommonJS delegation to `./src/canvas` in `_renderCanvas()`
- ✅ `node --check main.js` passes
- ✅ Runtime tests exist (canvas-main-runtime.test.mjs: 13 tests, all pass)

No ANN11 runtime invention needed — upstream wiring is complete.

## Task 2: Card Lane DOM Rendering

### renderCanvasCard(card)
- Creates `.paperforge-canvas-card` element with `data-card-id` attribute
- Sub-elements:
  - `.paperforge-canvas-card-selected-text` (+ `--empty`/`--long` modifiers)
  - `.paperforge-canvas-card-comment` (+ `--empty`/`--long` modifiers)
  - `.paperforge-canvas-card-page`
  - `.paperforge-canvas-card-type` (with inline `borderLeftColor` from card color)
  - `.paperforge-canvas-card-source` (source · attachmentKey · annotationKey)
  - `.paperforge-canvas-card-readonly` (+ `--true`/`--false` modifiers)
- All text via `textContent` — no innerHTML for annotation data
- Verified HTML-like strings (`<script>alert(1)</script>`) rendered as raw text

### renderCanvasCardLanes(contentEl, lanes)
- Creates `.paperforge-canvas-lanes` container
- Left/right lane sub-containers with `data-lane-index="0"`/`"1"`
- Cards rendered into lanes preserving ANN11-01 deterministic order
- No re-sorting, drag, or persistence in DOM

### renderCanvasView Updates
- `ready` state with `vm.lanes` → renders card lanes
- `ready` state without `vm.lanes` → empty placeholder (backward compatible)
- `refreshing` state → refreshing message + preserved cards
- `stale` state → preserved cards + stale banner

## Task 3: CSS + Runtime Regression

### Card/Lane CSS (styles.css)
- `.paperforge-canvas-lanes`: flex row, 12px gap, full width
- `.paperforge-canvas-lane-left/right`: flex column, 50% width, min-width: 0
- `.paperforge-canvas-card`: max-height 320px, overflow-y, no inline width/height
- `.paperforge-canvas-card-selected-text`: max-height 4.5em, gradient fade, CJK-safe word-break
- `.paperforge-canvas-card-comment`: max-height 3.6em, gradient fade, CJK-safe
- `.paperforge-canvas-card-readonly`: uppercase, restrained badge, fit-content
- No viewport-scaled fonts, no negative spacing, no hover resize

### i18n.js
- zh/en dictionaries for: `card.selected_text`, `card.comment`, `card.page`, `card.type`, `card.source`, `card.read_only`, `card.read_only_label`, `card.no_comment`, `card.no_selected_text`, `state.refreshing`, `state.stale`
- `t(key, lang?)` helper with auto-detect via `navigator.language`
- `detectLang()` with navigator + process.env.LANG fallback
- Tests verify both zh/en strings exist and unknown keys fall through

### Runtime Regression
- ANN10-02 wiring preserved: no duplicate view registration, no new loaders
- Canvas module exports ANN11 render helpers through index.js
- Forbidden controls absent in runtime DOM (edit/delete/create/save/import/apply/write-back)
- No anchor/connector/draggable classes in runtime surface

## No Go Items (verified absent)

- No source anchors, card-to-source navigation, connector lines
- No draggable/freeform layout, persistent layout state, edit/write controls
- No new Obsidian ItemView, command, paper-panel button, or active-paper resolver
- No direct database/Zotero/Python/API calls
- No new packages (CommonJS/Vitest/jsdom only)
- No innerHTML for annotation-derived card fields
- No ANN11 runtime ownership creep into ANN10-02's view/button wiring

## Test Results

```
 Test Files  9 passed (9)
      Tests  405 passed (405)
```

| Test File | Tests | Status |
|-----------|-------|--------|
| canvas-viewmodel.test.mjs | 78 | ✅ |
| canvas-layout.test.mjs | 33 | ✅ |
| canvas-render.test.mjs | 50 | ✅ |
| canvas-card-dom.test.mjs | 30 | ✅ |
| canvas-main-runtime.test.mjs | 29 | ✅ |
| annotation-bridge.test.mjs | 40 | ✅ |
| annotation-list-viewmodel.test.mjs | 78 | ✅ |
| annotation-section-dom.test.mjs | 20 | ✅ |
| annotation-main-runtime.test.mjs | 47 | ✅ |

## Threat Surface Scan

All card DOM rendering uses textContent for annotation-derived fields. No innerHTML injection surfaces. CSS is namespaced under `.paperforge-reading-canvas-view` — no global style leakage. No new network, subprocess, or database paths introduced. Forbidden control words are tested at both unit and runtime level.

## Self-Check: PASSED

- ✅ `paperforge/plugin/i18n.js` — created
- ✅ `paperforge/plugin/src/canvas/render.js` — extended with card/lane rendering
- ✅ `paperforge/plugin/styles.css` — card/lane CSS section added
- ✅ `paperforge/plugin/tests/canvas-card-dom.test.mjs` — 30 tests (8 new)
- ✅ `paperforge/plugin/tests/canvas-main-runtime.test.mjs` — 29 tests (16 new)
- ✅ Commit `80a322a` — Task 2 RED
- ✅ Commit `7d43f1b` — Task 2 GREEN
- ✅ Commit `6d0e4eb` — Task 3 RED
- ✅ Commit `5fcf3b0` — Task 3 GREEN
- ✅ All 405 tests pass across 9 test files
- ✅ `node --check main.js` passes

## Known Stubs

None. Card DOM rendering, CSS, i18n, and runtime regression are fully implemented.
