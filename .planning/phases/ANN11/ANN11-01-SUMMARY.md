---
phase: ANN11
plan: "01"
name: card-view-models-and-deterministic-layout
subsystem: canvas
tags:
  - annotation
  - canvas
  - card
  - layout
  - view-model
  - lane
requires:
  - ANN10-01
provides:
  - canvas/card-view-model
  - canvas/deterministic-layout
affects:
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-viewmodel.test.mjs
  - paperforge/plugin/tests/canvas-layout.test.mjs
tech-stack:
  added:
    - view-model.js — CommonJS card model projection
    - layout.js — CommonJS reading-order sort and lane assignment
  patterns:
    - Pure deterministic helpers over annotation state
    - No mutation controls, no action descriptors
    - No testable.js dependency in shipped canvas modules
key-files:
  created:
    - paperforge/plugin/src/canvas/view-model.js
    - paperforge/plugin/src/canvas/layout.js
    - paperforge/plugin/tests/canvas-viewmodel.test.mjs
    - paperforge/plugin/tests/canvas-layout.test.mjs
  modified:
    - paperforge/plugin/src/canvas/index.js
decisions:
  - D-01: Cards carry selected text, comment, page, color/type, source, provenance, read-only status
  - D-03: No expandable details, drawers, popovers, editable forms, or mutation controls
  - D-04: Missing selected text/comment render as explicit empty string placeholders with preview metadata
  - D-05: Cards sorted by stable reading/source order before lane assignment
  - D-06: Same-page same-sort-index uses stable identity tiebreaker
  - D-07: Lane assignment alternates left/right by sorted index
  - D-08: No random, draggable, persisted, localStorage, settings, or .canvas layout
  - D-09: Results are deterministic for same inputs
  - D-10/D-11: 11 distinct canvas states (idle, loading, ready, empty, missing-paper, missing-db, cli-error, invalid-json, missing-source, unsupported, refreshing, stale)
  - D-12: Error/stale states never masquerade as empty
  - D-13: Refreshing preserves cards with refreshing flag; stale preserves cards with stale flag
  - D-14: Missing-source preserves card visibility when annotation metadata is valid
  - D-18: Long, CJK, and HTML-like strings tested at view-model level
  - D-19: readOnlyLabel on card for restrained read-only signal
  - D-20: Source/attachment/provenance identity preserved
  - D-21: No create/edit/delete/save/import/apply/write-back controls
  - D-22: Forbidden verbs tested by string/JSON scan
metrics:
  plan_duration_minutes: 12
  tasks_total: 2
  tasks_completed: 2
  tests_total: 111
  files_created: 4
  files_modified: 1
  commits: 4
plan_date: 2026-07-06
---

# Phase ANN11 Plan 01: Card View-Models and Deterministic Layout

Turned ANN10's paper-scoped annotation state into safe, read-only card data with deterministic lane-layout contracts. Pure helper modules with no mutation controls, no anchors, no navigation, no connectors.

## Output

- **`view-model.js`** — `buildCanvasCard()`, `buildCanvasCardViewModel()`, `normalizeCanvasCardPreview()`
- **`layout.js`** — `compareCanvasCardsByReadingOrder()`, `sortCanvasCardsForReadingOrder()`, `assignCanvasCardsToLanes()`, `getCardIdentity()`
- **`index.js`** — Narrow CommonJS exports for ANN11 card/layout helpers (ANN10 exports preserved)
- **`canvas-viewmodel.test.mjs`** — 78 Vitest tests
- **`canvas-layout.test.mjs`** — 33 Vitest tests

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | `b92059c` — test(ANN11-01): add failing view-model test file | ✅ |
| GREEN (feat) | `4eb63d2` — feat(ANN11-01): implement card view-models | ✅ |
| RED (test) | `d1611a9` — test(ANN11-01): add failing layout test file | ✅ |
| GREEN (feat) | `231cfc8` — feat(ANN11-01): implement deterministic layout | ✅ |

## Decisions Implemented

### Card View-Model (view-model.js)

- **D-01 / CARD-01**: Cards carry `selectedText`, `comment`, `pageLabel`, `pageIndex`, `type`, `color`, `source`, `sourceAttachmentKey`, `sourceAnnotationKey`, `readOnly`, `readOnlyLabel`, `id`, and `anchor`.
- **D-03 / D-21**: No expandable details, drawers, popovers, editable forms, mutation state, or function properties. Forbidden verbs (`edit`, `delete`, `create`, `save`, `import`, `apply`, `writeBack`) tested via `Object.keys()` and JSON string scan.
- **D-04 / CARD-02**: Missing/null `selectedText` and `comment` map to `''` with preview metadata (`selectedTextPreview`, `commentPreview`) showing `{ text: '', truncated: false, expandable: false, isLong: false }`.
- **D-18 / CARD-02**: Long/CJK/HTML-like strings preserved as-data with preview metadata indicating truncation. HTML-like strings (`<script>alert(1)</script>`) preserved as literal text in the model.
- **D-19**: `readOnlyLabel` is `'Read-only'` for read-only cards, `''` for mutable.
- **D-20**: `sourceAttachmentKey`, `sourceAnnotationKey`, `source`, `pageIndex` preserve provenance for later evidence workflows.

### Canvas State Projection (view-model.js `buildCanvasCardViewModel`)

- **D-10 / D-11 / CANVAS-04**: Maps annotation state to 11+ states:
  - `idle`, `loading` — no cards
  - `ready` — cards with `lanes: { left, right }`
  - `empty` — no cards
  - `missing-paper`, `missing-db`, `cli-error`, `invalid-json`, `missing-source`, `unsupported` — no cards, distinct per state name
  - `refreshing` — preserves cards with `refreshing: true`
  - `stale` — preserves cards with per-card `stale: true`
- **D-12**: Error states never named `'empty'`.
- **D-13**: `refreshing` and `stale` states preserve existing cards.
- **D-14**: `missing-source` and `unsupported` handled as distinct state names.

### Deterministic Lane Layout (layout.js)

- **D-05 / CARD-03**: `compareCanvasCardsByReadingOrder()` sorts by page index → sortIndex → stable identity. Parity tested against `sortAnnotationsForReadingOrder()`.
- **D-06**: Same-page/sort-index falls back to stable identity (e.g., `'ann-a'` < `'ann-b'`).
- **D-07**: `assignCanvasCardsToLanes()` alternates even index → left, odd → right. Lane/laneIndex set on derived shallow copies.
- **D-08**: No random, draggable, persisted, localStorage, settings, or `.canvas` fields. Input objects not mutated.
- **D-09**: Deterministic — identical results for same input across 10 calls.

### No Go Items (verified absent)

- No create, edit, delete, save, import, apply, write-back controls
- No anchors, navigation, connectors
- No random/persisted/draggable layout
- No new dependencies (stack: CommonJS/Vitest/jsdom only)
- No testable.js imported in shipped canvas modules
- No SQLite, Zotero, CLI, or subprocess calls

## Deviations from Plan

None — plan executed exactly as written. All 111 focused tests pass with no Vitest startup errors.

## Test Results

```
 Test Files  5 passed (5)
      Tests  236 passed (236)
```

| Test File | Tests | Status |
|-----------|-------|--------|
| canvas-context.test.mjs | 27 | ✅ |
| canvas-viewmodel.test.mjs | 78 | ✅ |
| canvas-layout.test.mjs | 33 | ✅ |
| annotation-list-viewmodel.test.mjs | 78 | ✅ |
| canvas-controller.test.mjs | 20 | ✅ |

## Threat Surface Scan

No new security-relevant surface introduced. All card view-model and layout helpers are pure data projection functions with no I/O, subprocess, database, or network access. Card models store only identity and display metadata (no raw CLI output or stack traces). Lane assignment is deterministic with no persistence side effects.

## Self-Check: PASSED

- ✅ `paperforge/plugin/src/canvas/view-model.js` — exists
- ✅ `paperforge/plugin/src/canvas/layout.js` — exists
- ✅ `paperforge/plugin/tests/canvas-viewmodel.test.mjs` — exists
- ✅ `paperforge/plugin/tests/canvas-layout.test.mjs` — exists
- ✅ Commit `b92059c` — view-model test (RED)
- ✅ Commit `4eb63d2` — view-model implementation (GREEN)
- ✅ Commit `d1611a9` — layout test (RED)
- ✅ Commit `231cfc8` — layout implementation + index.js (GREEN)

## Known Stubs

None. All card view-model states are fully implemented with explicit fields and no placeholder/noop values.
