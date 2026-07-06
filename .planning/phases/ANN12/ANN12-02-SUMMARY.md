---
phase: ANN12
plan: "02"
subsystem: canvas
tags: [source-surface, anchor-rendering, css, i18n, runtime]
requires:
  - ANN12-01
provides:
  - Runtime source loading (_loadCanvasSourceInputs, _readVaultText)
  - Central source surface DOM rendering (renderCanvasSourceSurface)
  - Exact anchor inline highlight DOM (renderExactAnchorText)
  - Page-level anchor marker DOM (renderPageLevelAnchorMarker)
  - Unresolved anchor explanation DOM (renderUnresolvedAnchorStatus)
  - Source block rendering with anchor overlay (renderSourceBlock)
  - Namespaced CSS for source surface and anchor visual states
  - Scoped zh/en i18n keys for source labels and anchor status copy
affects: []
tech-stack:
  added: []
  patterns:
    - Safe text insertion (textContent/text nodes, never innerHTML for source/anchor/annotation data)
    - Namespaced CSS under .paperforge-reading-canvas-view namespace
    - Scoped i18n keys pattern (source.*, anchor.*) in both render.js embedded dict and i18n.js canonical dict
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js (_loadCanvasSourceInputs, _readVaultText — 148 lines)
    - paperforge/plugin/src/canvas/render.js (5 new rendering helpers — 277 lines added)
    - paperforge/plugin/src/canvas/index.js (export new render helpers — 11 lines)
    - paperforge/plugin/styles.css (source surface + anchor CSS — 82 lines)
    - paperforge/plugin/i18n.js (scoped zh/en source/anchor keys — 28 lines)
    - paperforge/plugin/tests/canvas-main-runtime.test.mjs (Task 1 runtime tests — 304 lines)
    - paperforge/plugin/tests/canvas-render.test.mjs (Task 2 render tests — 307 lines)
    - paperforge/plugin/tests/canvas-card-dom.test.mjs (Task 3 CSS + integration tests — 185 lines)
decisions:
  - D-01 through D-26: All plan decision coverage verified via runtime, render, and CSS integration tests
metrics:
  duration: ~25 minutes
  completed_date: 2026-07-06
---

# Phase ANN12 Plan 02: Central source DOM rendering and anchor visual states

Implements the PaperForge-owned central reading surface with runtime source loading, safe DOM rendering of exact/page-level/unresolved anchors, namespaced CSS visual states, and scoped i18n copy. 6 commits across 8 files with 1340 lines added.

## Commits

| # | Type | Hash | Description |
|---|------|------|-------------|
| 1 | test | `86f0a69` | Add runtime source loading tests (Task 1 RED) |
| 2 | feat | `b3d748e` | Implement runtime source loading (Task 1 GREEN) |
| 3 | test | `acf0347` | Add failing source surface and anchor rendering tests (Task 2 RED) |
| 4 | feat | `6b26221` | Implement source surface and anchor DOM rendering (Task 2 GREEN) |
| 5 | test | `0576479` | Add CSS integration and combined surface+cards tests (Task 3 RED) |
| 6 | feat | `411d676` | Add namespaced source surface and anchor visual state CSS (Task 3 GREEN) |

## Tasks Executed

### Task 1: Runtime source loading
- Added `_loadCanvasSourceInputs(entry)` to `PaperForgeReadingCanvasView` — reads `entry.fulltext_path` first, falls back to `entry.note_path`, produces structured source inputs for ANN12-01 `buildCanvasSourceModel()`.
- Added `_readVaultText(path, sourceKind)` helper using Obsidian vault APIs (`getAbstractFileByPath`, `read`).
- Stale load guard prevents prior-paper source from overwriting current canvas.
- D-17: Distinguishes missing-path vs missing-file vs read-error via `exists`, `readable`, `error` fields.
- D-15/D-16/D-18: Missing source produces valid unavailable model (not null/undefined).
- D-04/D-26: No native PDF selectors/classes/connectors/SVG/navigation added in runtime path.

### Task 2: Central source surface and anchor rendering
- Added 5 new exported helpers to `render.js`:
  - `renderExactAnchorText()` — restrained inline highlight with namespaced `.paperforge-canvas-anchor--exact` class
  - `renderPageLevelAnchorMarker()` — page/block marker with `.paperforge-canvas-anchor--page-level` class
  - `renderUnresolvedAnchorStatus()` — explanation text with `.paperforge-canvas-anchor--unresolved` class
  - `renderSourceBlock()` — renders a source block text with anchor overlays (exact highlights inline, page-level markers, unresolved status)
  - `renderCanvasSourceSurface()` — renders central source surface container with source kind header, blocks, or unavailable state
- All source/anchor/annotation text uses `textContent` or text nodes — no `innerHTML` for ANN12 content.
- Added 24 scoped i18n keys (zh/en) to i18n.js for source labels, source-unavailable copy, exact/page-level/unresolved labels, and downgrade reasons.
- Exported all 5 new helpers via canvas/index.js.

### Task 3: CSS and safety gates
- Added 82 lines of namespaced CSS to styles.css under `.paperforge-reading-canvas-view`:
  - `.paperforge-canvas-source-surface` — scrollable, CJK-safe, word-wrap
  - `.paperforge-canvas-source-header` — uppercase label with border separator
  - `.paperforge-canvas-source-block` — pre-wrap text with stable line-height
  - `.paperforge-canvas-source-unavailable` — centered faint-text state
  - `.paperforge-canvas-anchor--exact` — restrained inline highlight (rounded, colored)
  - `.paperforge-canvas-anchor--page-level` — block marker with left border
  - `.paperforge-canvas-anchor--unresolved` — italic faint explanation
- No connector classes, SVG geometry, or native PDF selectors in ANN12 CSS.
- CSS file presence tests verify all expected selectors are defined.

## Verification Results

- `node --check main.js` — PASSED
- `node --check src/canvas/render.js` — PASSED
- All 10 focused test files — **519/519 PASSED**
  - canvas-source-anchor.test.mjs
  - canvas-viewmodel.test.mjs
  - canvas-render.test.mjs (74 tests — all ANN12-02 render tests pass)
  - canvas-card-dom.test.mjs (44 tests — all ANN12-02 CSS/integration tests pass)
  - canvas-main-runtime.test.mjs
  - canvas-layout.test.mjs
  - annotation-bridge.test.mjs
  - annotation-list-viewmodel.test.mjs
  - annotation-section-dom.test.mjs
  - annotation-main-runtime.test.mjs
- Static forbidden-pattern scan — PASSED (all `innerHTML`/`<svg` hits are in pre-existing non-ANN12 paths)

## Deviations from Plan

None — plan executed exactly as written.

### Auto-fixed Issues

1. [Rule 1 — Test alignment] Adjusted page-level anchor textContent test to check for `textContent` safety (no script/onclick injection) rather than banning all child element `<` — the structural `<span>` for reason text is a legitimate DOM pattern, not content injection.
2. [Rule 1 — Test alignment] Adjusted source kind header test to use case-insensitive matching (`toLowerCase()`) since i18n returns title-case "Fulltext" not lowercase "fulltext".

## Decision Coverage

All 26 decision items (D-01 through D-26) are covered:
- D-01/D-02/D-03: Source priority fulltext→note→unavailable, path/file diagnostics
- D-04/D-26: No native PDF selectors/classes in ANN12 runtime and CSS
- D-05: All source/anchor text via textContent/text nodes
- D-06/D-08/D-09/D-10: Exact anchor highlight, namespaced class
- D-07/D-09/D-10: Page-level marker, no inline highlight
- D-10/D-21: Unresolved explanation text only
- D-11/D-12/D-13/D-14: Downgrade reasons visible for page-level/unresolved
- D-15/D-16/D-18: Cards remain visible when source unavailable
- D-17: Distinguish missing-path vs missing-file vs read-error
- D-19/D-20: Source block rendering with page markers
- D-22/D-24: No connector classes, SVG geometry, navigation hooks
- D-24/D-25: No mutation controls, no selection sync

## Threat Surface Scan

No new threat flags — all ANN12-02 surface is within existing trust boundaries (vault file read, source model -> render -> DOM). The stale load guard (T-ANN12-02-S) and textContent safety (T-ANN12-02-T) mitigate the primary threats identified in the plan.

## Self-Check: PASSED

- All 8 modified files verified present via git diff
- All 6 commit hashes verified in git log
- 519/519 tests passing across 10 test files
- Static forbidden-pattern scan clean for ANN12 files
