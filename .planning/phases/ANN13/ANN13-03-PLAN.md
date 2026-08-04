---
phase: ANN13
plan: ANN13-03
type: execute
status: planned
wave: 3
depends_on:
  - ANN13-01
  - ANN13-02
files_modified:
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/i18n.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/canvas-render.test.mjs
  - paperforge/plugin/tests/canvas-card-dom.test.mjs
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
  - D-07
  - D-08
  - D-09
  - D-15
  - D-17
  - D-18
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
    - "D-01/D-02/D-03/D-04: Rendered cards and source targets expose stable selection hooks for exact, page-level, unresolved, and selected states."
    - "D-07/D-08/D-09: Rendered exact anchors and page-level markers expose card/group identity needed for source-to-card focus."
    - "D-15/D-17/D-18/D-23: Fallback DOM is a real Open PDF page button only when eligible and has clear aria labels."
    - "D-20/D-21/D-22/D-24: Cards, exact anchors, page markers, and fallback buttons are naturally tabbable and use aria-selected without roving tabindex/listbox behavior."
    - "D-25/D-26/D-27: Render/CSS/i18n add no mutation controls, connector geometry/classes/SVG paths, or native PDF viewer DOM dependency."
  artifacts:
    - path: "paperforge/plugin/src/canvas/render.js"
      provides: "Focusable, accessible card/source/fallback DOM with selected states"
    - path: "paperforge/plugin/i18n.js"
      provides: "Localized navigation status and Open PDF page copy"
    - path: "paperforge/plugin/styles.css"
      provides: "Namespaced selected/focus/status styles without connector classes"
  key_links:
    - from: "paperforge/plugin/src/canvas/navigation.js"
      to: "paperforge/plugin/src/canvas/render.js"
      via: "render consumes selected/fallback state and emits data hooks"
      pattern: "data-card-id|data-anchor-id|aria-selected"
---

# ANN13-03 Plan: Render DOM Hooks, ARIA, Keyboard Targets

## Objective

Render cards, exact anchors, page-level markers, status text, and fallback buttons with the stable DOM hooks and accessibility attributes required by ANN13 runtime navigation.

## Scope

- `render.js` DOM attributes, focusability, selected state, and fallback button rendering.
- i18n copy for navigation statuses and "Open PDF page".
- CSS selected/focus/status styles.
- DOM/render tests.

## Out of Scope

- No runtime event delegation, `scrollIntoView`, `focus()`, or `openLinkText`.
- No connector/SVG relationship layer, native PDF viewer DOM dependency, mutation controls, fuzzy matching.

## Tasks

### Task 1: Render Focusable Card and Source Targets

**Files:** `src/canvas/render.js`, `tests/canvas-render.test.mjs`, `tests/canvas-card-dom.test.mjs`

**Action:** Add `data-card-id`, `data-anchor-id`, `data-anchor-status`, `data-page-index`, natural `tabIndex`, and `aria-selected` to actionable cards/exact anchors/page markers.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs
Pop-Location
```

**Done:** Cards, exact anchors, and page markers are tabbable/actionable; unresolved status text is not tabbable.

### Task 2: Render Selected and Page-Group States

**Files:** `src/canvas/render.js`, `styles.css`, `tests/canvas-render.test.mjs`, `tests/canvas-card-dom.test.mjs`

**Action:** Render selected card/source classes, related page-group card classes, and restrained namespaced CSS.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs
Pop-Location
```

**Done:** Visual state and `aria-selected` agree; page-level groups do not pretend to be one exact card.

### Task 3: Render Explicit Fallback Button and Copy

**Files:** `src/canvas/render.js`, `i18n.js`, `tests/canvas-render.test.mjs`

**Action:** Render a real fallback `button` with "Open PDF page" / localized label only when eligibility is true.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs
Pop-Location
```

**Done:** Button has clear text and `aria-label`; unresolved status text remains non-actionable; ineligible fallback renders no button.

### Task 4: Add Forbidden-Scope DOM Regression

**Files:** `tests/canvas-card-dom.test.mjs`, `tests/canvas-render.test.mjs`

**Action:** Add assertions that ANN13 render output contains no connector classes, SVG relationship layer, mutation controls, or native PDF viewer DOM selectors.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs
Pop-Location
```

**Done:** Tests fail if ANN13 render output introduces forbidden connector/mutation/native-PDF coupling markers.

## Acceptance Criteria

- NAV-01/NAV-02 have actionable DOM targets.
- NAV-03 has explicit fallback button DOM but no runtime open.
- D-17 and D-20 through D-24 are test-covered before runtime integration.
