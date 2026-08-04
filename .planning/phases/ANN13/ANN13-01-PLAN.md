---
phase: ANN13
plan: ANN13-01
type: execute
status: planned
wave: 1
depends_on: []
files_modified:
  - paperforge/plugin/src/canvas/navigation.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-navigation.test.mjs
requirements:
  - NAV-01
  - NAV-02
requirements_addressed:
  - NAV-01
  - NAV-02
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
  - D-25
  - D-26
  - D-27
must_haves:
  truths:
    - "D-01/D-02/D-03: Pure navigation reducers classify exact, page-level, unresolved, and missing-DOM card activation without fuzzy matching or guessed source jumps."
    - "D-04/D-05/D-06: Selection state persists until explicit replacement or Escape, missing DOM targets never auto-fallback, and refresh preservation never requests scroll."
    - "D-07/D-08/D-09/D-10: Source-to-card reducers distinguish single-card focus targets, page-level groups, and unavailable/stale card targets."
    - "D-11/D-12/D-13/D-14: Lifecycle reducers clear or preserve selection correctly across paper change, teardown, refresh, stale load, and Escape."
    - "D-25/D-26/D-27: Navigation reducers remain read-only, introduce no connector geometry/SVG contract, and do not depend on native Obsidian PDF viewer DOM internals."
  artifacts:
    - path: "paperforge/plugin/src/canvas/navigation.js"
      provides: "Pure ANN13 selection, target, lifecycle, and page-group reducers"
    - path: "paperforge/plugin/src/canvas/index.js"
      provides: "CommonJS export surface for ANN13 navigation helpers"
    - path: "paperforge/plugin/tests/canvas-navigation.test.mjs"
      provides: "Unit coverage for card/source/page/lifecycle navigation states"
  key_links:
    - from: "paperforge/plugin/src/canvas/anchors.js"
      to: "paperforge/plugin/src/canvas/navigation.js"
      via: "ANN12 exact/page-level/unresolved anchor statuses are consumed, not recomputed"
      pattern: "exact|page-level|unresolved"
---

# ANN13-01 Plan: Pure Selection and Navigation Reducers

## Objective

Create the pure navigation state contract for card-to-source, source-to-card, page-group, and lifecycle behavior. This plan does not touch DOM, CSS, i18n, or Obsidian workspace APIs.

## Scope

- New `paperforge/plugin/src/canvas/navigation.js`.
- Narrow export additions in `paperforge/plugin/src/canvas/index.js`.
- New unit tests in `paperforge/plugin/tests/canvas-navigation.test.mjs`.

## Out of Scope

- DOM event listeners, focus, `scrollIntoView`, fallback buttons, `openLinkText`, CSS, i18n.
- Connector geometry/classes/SVG paths, native PDF viewer DOM coupling, edit/writeback/import/apply/mutation controls, fuzzy matching, guessed jumps.

## Tasks

### Task 1: Define Navigation State Shapes

**Files:** `src/canvas/navigation.js`, `tests/canvas-navigation.test.mjs`

**Action:** Add state factories/constants for `none`, `card-anchor`, `page-group`, `source-target-unavailable`, `card-unavailable`, and `previous-selection-unavailable`.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-navigation.test.mjs
Pop-Location
```

**Done:** Tests prove every state is serializable, read-only in shape, and contains no DOM element or Obsidian object references.

### Task 2: Implement Card-to-Source Decisions

**Files:** `src/canvas/navigation.js`, `tests/canvas-navigation.test.mjs`

**Action:** Implement card activation reducers for exact, page-level, unresolved, and missing-DOM targets.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-navigation.test.mjs canvas-source-anchor.test.mjs
Pop-Location
```

**Done:** Exact requests source-anchor scroll, page-level requests page-marker scroll, unresolved never scrolls, and missing DOM target keeps card selected with unable-to-locate status and no auto-fallback.

### Task 3: Implement Source-to-Card and Page-Group Decisions

**Files:** `src/canvas/navigation.js`, `tests/canvas-navigation.test.mjs`

**Action:** Implement source activation reducers for single exact anchors, page-level markers with multiple card IDs, and unavailable/stale card targets.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-navigation.test.mjs
Pop-Location
```

**Done:** Exact source target resolves one card focus target; page-level target resolves a group; unavailable card clears dangling selection with temporary status.

### Task 4: Implement Lifecycle Reducers and Exports

**Files:** `src/canvas/navigation.js`, `src/canvas/index.js`, `tests/canvas-navigation.test.mjs`

**Action:** Add Escape, paper-change, teardown, refresh-preserve, and refresh-clear reducers, then export the helper surface.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check src/canvas/navigation.js
node --check src/canvas/index.js
npm.cmd test -- canvas-navigation.test.mjs
Pop-Location
```

**Done:** Refresh can preserve still-valid selection without scroll/focus requests; paper change/teardown/Escape clear state; removed selected targets clear with one-time status.

## Acceptance Criteria

- NAV-01 and NAV-02 have pure, DOM-independent navigation decisions.
- D-01 through D-14 are represented in testable reducers.
- D-25 through D-27 scope fences are preserved by construction.
