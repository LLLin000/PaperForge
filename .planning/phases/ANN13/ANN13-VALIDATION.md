# ANN13 Validation Matrix

**Phase:** ANN13 - Bidirectional Navigation and Fallback Paths  
**Generated:** 2026-07-06  
**Status:** Planned

## Validation Goal

ANN13 is valid when the Reading Canvas supports honest bidirectional navigation between annotation cards and PaperForge-owned source anchors, preserves clear selection state, and exposes v0.2 PDF page fallback only through an explicit safe button when canvas source navigation cannot locate a supported source target.

## Requirement Coverage

| Requirement | Planned Coverage | Verification |
| --- | --- | --- |
| NAV-01 | Card activation resolves exact, page-level, unresolved, and missing-DOM cases through pure navigation helpers, then runtime scrolls only on explicit user activation. | `canvas-navigation.test.mjs`, `canvas-render.test.mjs`, `canvas-main-runtime.test.mjs` |
| NAV-02 | Source exact anchors and page-level markers activate the matching card or page group and move real focus to a single card when one exists. | `canvas-navigation.test.mjs`, `canvas-card-dom.test.mjs`, `canvas-main-runtime.test.mjs` |
| NAV-03 | Unsupported canvas navigation exposes a real "Open PDF page" button only when v0.2 target resolution returns a trusted PDF path and valid page target. | `canvas-navigation.test.mjs`, `annotation-navigation.test.mjs`, `annotation-main-runtime.test.mjs`, `canvas-main-runtime.test.mjs` |

## Decision Coverage

| Decision | Planned Verification |
| --- | --- |
| D-01 | Exact card selection maps to the exact anchor target and runtime calls `scrollIntoView` for the inline exact element only on explicit card activation. |
| D-02 | Page-level card selection maps to a page marker/group target, not guessed sentence text. |
| D-03 | Unresolved card selection does not scroll and produces an unresolved/navigation status plus eligible fallback only when safe. |
| D-04 | Selection state remains visible until another selection or Escape clears it. |
| D-05 | Missing DOM source targets never guess, never auto-open PDF, and keep selected card/status/fallback state. |
| D-06 | Refresh/stale/re-render preservation never performs automatic scroll. |
| D-07 | Source exact anchor activation selects/focuses the corresponding card and marks both sides selected. |
| D-08 | Page-level marker activation selects a group of related cards instead of pretending to be one exact card. |
| D-09 | Single source-to-card navigation moves real DOM focus to a focusable card. |
| D-10 | Missing/stale card targets clear dangling selection and show temporary unavailable status. |
| D-11 | Paper changes and teardown clear all selection, group, focus, and navigation status. |
| D-12 | Successful refresh may preserve still-valid selection without scroll or focus theft. |
| D-13 | Refresh that removes the selected card/anchor clears selection and emits one-time status. |
| D-14 | Escape clears selection and temporary status without changing scroll position. |
| D-15 | PDF fallback is shown only when canvas navigation is unavailable and a trustworthy v0.2 page target exists. |
| D-16 | PDF fallback is activated only by explicit fallback button click; selection never auto-jumps to PDF. |
| D-17 | Fallback visible copy and aria labels use "Open PDF page" / localized equivalent. |
| D-18 | Fallback is hidden when PDF path, valid pageIndex, attachment identity, or paper identity safety is missing. |
| D-19 | Fallback reuses v0.2 PDF page resolution and attachment checks instead of a new resolver. |
| D-20 | Cards, exact anchors, page-level markers, and fallback buttons are tabbable; unresolved status text is not. |
| D-21 | Enter/Space activate focused cards/anchors/markers/buttons; Escape clears selection. |
| D-22 | Selected cards/source targets expose visual selected classes and `aria-selected`. |
| D-23 | Fallback actions are real `button` elements with clear `aria-label`. |
| D-24 | DOM uses natural tab order and does not introduce roving tabindex, listbox, or arrow-key systems. |
| D-25 | Read-only boundary is preserved; no create/edit/delete/save/import/apply/write-back/evidence mutation controls. |
| D-26 | No connector classes, connector geometry, SVG paths, hover lines, or final relationship polish are introduced. |
| D-27 | Canvas navigation does not depend on native Obsidian PDF viewer DOM internals; fallback may call existing `openLinkText` after v0.2 safety checks. |

## Focused Verification Commands

```powershell
Push-Location paperforge/plugin
node --check src/canvas/navigation.js
node --check src/canvas/render.js
node --check main.js
npm.cmd test -- canvas-navigation.test.mjs canvas-source-anchor.test.mjs canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs
Pop-Location
```

## Forbidden-Scope Scan

Execution should include a grep-style scan proving ANN13 did not add connector or mutation surfaces:

```powershell
rg -n "paperforge-canvas-connector|connector-line|<svg|create annotation|edit annotation|delete annotation|write-back|apply annotation|native pdf viewer|pdf-viewer" paperforge/plugin
```

The expected result is no new ANN13-owned connector geometry, SVG relationship paths, native PDF viewer DOM coupling, or mutation controls.

