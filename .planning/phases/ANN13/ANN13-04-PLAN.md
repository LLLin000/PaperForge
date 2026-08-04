---
phase: ANN13
plan: ANN13-04
type: execute
status: planned
wave: 4
depends_on:
  - ANN13-01
  - ANN13-02
  - ANN13-03
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  - paperforge/plugin/tests/annotation-section-dom.test.mjs
requirements:
  - NAV-01
  - NAV-02
  - NAV-03
requirements_addressed:
  - NAV-01
  - NAV-02
  - NAV-03
user_setup: []
autonomous: true
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-05
  - D-06
  - D-07
  - D-08
  - D-09
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16
  - D-17
  - D-18
  - D-19
  - D-20
  - D-21
  - D-22
  - D-23
  - D-24
  - D-25
  - D-26
  - D-27
must_haves:
  truths:
    - "D-01/D-02/D-03/D-04/D-05/D-06: Runtime card activation scrolls exact or page-level source targets only on explicit activation, keeps honest status for unresolved/missing targets, and never steals scroll on refresh."
    - "D-07/D-08/D-09/D-10: Runtime source activation focuses a real card for single-card targets, selects page groups for page markers, and clears unavailable selections."
    - "D-11/D-12/D-13/D-14: Runtime lifecycle clears or preserves selected DOM state correctly across paper changes, refreshes, stale renders, teardown, and Escape."
    - "D-15/D-16/D-17/D-18/D-19: Runtime fallback opens v0.2 PDF page only from explicit Open PDF page button click after safety checks."
    - "D-20/D-21/D-22/D-23/D-24: Runtime keyboard behavior supports Enter/Space/Escape and preserves natural tab order."
    - "D-25/D-26/D-27: Runtime adds no mutation controls, connector geometry/SVG/relationship-line layer, or native PDF viewer DOM dependency."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Loaded canvas integration, event delegation, focus/scroll lifecycle, and explicit fallback opening"
    - path: "paperforge/plugin/tests/canvas-main-runtime.test.mjs"
      provides: "Runtime event, focus, scroll, Escape, refresh, teardown, and fallback tests"
  key_links:
    - from: "paperforge/plugin/src/canvas/navigation.js"
      to: "paperforge/plugin/main.js"
      via: "runtime applies pure decisions to DOM focus, scroll, and status"
      pattern: "no auto-scroll on refresh"
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/testable.js"
      via: "fallback reuses v0.2 PDF target safety before openLinkText"
      pattern: "explicit Open PDF page button"
---

# ANN13-04 Plan: Runtime Integration, Lifecycle, and Explicit PDF Opening

## Objective

Connect the pure navigation model and rendered DOM hooks to `PaperForgeReadingCanvasView`, including mandatory loaded cards + source surface runtime rendering, delegated activation, lifecycle cleanup, and explicit safe PDF page opening.

## Scope

- `main.js` runtime loaded-state integration for cards plus source surface.
- Delegated click/keyboard event handling.
- DOM focus/scroll and selected-state application.
- Explicit fallback button opening through existing v0.2 safety path.
- Runtime tests.

## Out of Scope

- No ANN15 live native PDF harness claims.
- No connector/SVG relationship layer, native PDF viewer DOM selectors, mutation controls, fuzzy jumps, or automatic PDF opening.

## Tasks

### Task 1: Add Mandatory Loaded Canvas Runtime Rendering

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`

**Action:** Replace the idle-only valid-context path with the narrow loaded-state path required for ANN13 tests: annotations, source model, cards, lanes, and source surface render together for a fixed paper context.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check main.js
npm.cmd test -- canvas-main-runtime.test.mjs
Pop-Location
```

**Done:** Runtime tests prove the real `PaperForgeReadingCanvasView` can render cards and source anchors in one DOM tree for a paper. This is mandatory, not conditional.

### Task 2: Wire Delegated Card and Source Activation

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`

**Action:** Add delegated click and Enter/Space handlers that call ANN13 navigation helpers, update selected DOM state, invoke `scrollIntoView` only on explicit activation, and move real focus for single-card source targets.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-main-runtime.test.mjs
Pop-Location
```

**Done:** Tests prove card-to-source exact/page-level navigation, source-to-card focus, page-group selection, and no scroll for unresolved/missing DOM cases.

### Task 3: Wire Lifecycle and Keyboard Clearing

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`

**Action:** Clear or preserve runtime selection on Escape, refresh, stale render, paper change, and `onClose`.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-main-runtime.test.mjs
Pop-Location
```

**Done:** Tests prove Escape clears without scroll, refresh preserves valid selection without scroll/focus theft, removed targets clear with status, and teardown/paper change clears all selection/listeners.

### Task 4: Wire Explicit Safe PDF Fallback Opening

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`, `tests/annotation-main-runtime.test.mjs`, `tests/annotation-section-dom.test.mjs`

**Action:** On fallback button click only, reuse v0.2 PDF target/vault safety checks and call `app.workspace.openLinkText(linkText, '')`.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-main-runtime.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-navigation.test.mjs
Pop-Location
```

**Done:** Tests prove selecting cards/sources never calls `openLinkText`; explicit eligible fallback click does; ineligible fallback never renders or opens.

## Acceptance Criteria

- NAV-01, NAV-02, and NAV-03 work through the real `PaperForgeReadingCanvasView`, not only isolated helper tests.
- Runtime loaded-state integration is required and tested.
- All fallback opening remains explicit, safe, and v0.2-compatible.
