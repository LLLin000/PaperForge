# Phase ANN10 Research: Canvas Data Contract and View Registration

**Researched:** 2026-07-04
**Status:** Complete
**Mode:** Local orchestrator research after two `gsd-phase-researcher` subagents timed out before writing an artifact.

## Research Summary

Phase ANN10 should land as two implementation slices:

1. Build the `paperforge/plugin/src/canvas/*` contract modules and pure tests.
2. Wire those contracts into `main.js` with a new `ItemView`, command palette entry, paper panel button, runtime tests, and the focused v0.2 annotation regression gate.

This split keeps the first wave focused on testable canvas state contracts and the second wave focused on Obsidian runtime integration. It also keeps Phase ANN10 inside CANVAS-01/CANVAS-02 and avoids drifting into cards, anchors, connectors, or visual polish.

## Codebase Findings

### Runtime Entry

- `paperforge/plugin/main.js` imports `ItemView` from Obsidian and currently registers only `VIEW_TYPE_PAPERFORGE = 'paperforge-status'`.
- `PaperForgePlugin.onload()` is the correct integration point for registering a second view type and command.
- `PaperForgeStatusView._renderPaperMode()` is the likely location for the paper panel button because it already owns the current paper `entry` and `_currentPaperKey`.
- `PaperForgeStatusView` currently stores `_currentPaperKey`, `_currentPaperEntry`, `_annotationState`, and `_annotationLoadSeq`. The canvas view must not rely on those globals after opening; it needs its own explicit `paperKey`.

### Testable Contracts

- `paperforge/plugin/src/testable.js` already exports `ANNOTATION_LOAD_STATES`, `makeAnnotationState()`, `loadAnnotationsForPaper()`, and `createAnnotationLifecycleController()`.
- Canvas annotation loading should wrap these contracts instead of creating new subprocess arguments or direct DB access.
- Existing plugin tests use CommonJS `require()` and jsdom/Obsidian mocks; new canvas tests should follow `.test.mjs` patterns.

### Existing Focused Regression Gates

The Phase ANN10 final gate should keep using:

- `node --check main.js`
- `npm.cmd test -- annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-overlay.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs`

These tests are the v0.2 bridge/list/navigation/overlay safety net. New canvas tests should be added to the focused command, not replace it.

## Recommended Module Seams

### `paperforge/plugin/src/canvas/context.js`

Owns canvas context resolution:

- Accept explicit paper entries from the paper panel.
- Accept active-paper resolver output from command palette flows.
- Return stable `{ ok, paperKey, entry, reason }`-style objects.
- Never infer from raw title/path when an explicit `entry.key` exists.

### `paperforge/plugin/src/canvas/annotations.js`

Owns canvas annotation loading as a wrapper:

- Call injected or imported `loadAnnotationsForPaper()`.
- Preserve v0.2 load states and messages.
- Make it obvious no new DB, Zotero, or Python subprocess contract is introduced.

### `paperforge/plugin/src/canvas/controller.js`

Owns session lifecycle:

- Store immutable `paperKey` for the open canvas session.
- Track a monotonic load sequence for stale result discard.
- Expose refresh/load/teardown methods that can be driven from the `ItemView`.

### `paperforge/plugin/src/canvas/render.js`

Owns Phase ANN10 shell DOM only:

- Render shell, paper identity heading, loading, empty, missing-paper, CLI-error, missing-source, and unsupported states.
- Use text-safe DOM methods only.
- Assert no forbidden write controls.

### `paperforge/plugin/src/canvas/index.js`

Owns narrow CommonJS exports for `main.js` and tests.

## Runtime Wiring Recommendation

- Add `VIEW_TYPE_PAPERFORGE_READING_CANVAS = 'paperforge-reading-canvas'`.
- Add `PaperForgeReadingCanvasView extends ItemView`.
- Add a static/open helper or plugin method that accepts `{ paperKey, entry }` and opens/reuses a leaf for that paper.
- From paper panel, pass `entry.key` directly.
- From command palette, use existing active-paper resolution. If unavailable, show a concise `Notice`.
- Do not auto-switch an open canvas when the active paper changes elsewhere.

## Import Risk

The repo uses CommonJS and `paperforge/plugin/package.json` has `"type": "commonjs"`, so `require('./src/canvas')` from `main.js` should be viable. However, previous v0.2 work encountered helper drift between `main.js` and `src/testable.js`. Plans must require runtime tests proving the shipped `main.js` path uses the same canvas helpers as the pure tests.

If runtime require fails in live Obsidian, temporary inlining is allowed only with explicit debt in the summary and parity tests.

## Pitfalls

- Do not add a global canvas browser or paper picker in ANN10.
- Do not make canvas follow active paper changes automatically.
- Do not add cards, anchors, connectors, pan/zoom, or rich visual polish.
- Do not create new Python CLI commands or annotation database readers.
- Do not mutate `annotations.db`, Zotero data, vault notes, settings, localStorage, or `.canvas` files.
- Do not hide or regress existing v0.2 annotation list/jump/overlay fallback behavior.

## RESEARCH COMPLETE

Artifact written: `.planning/phases/ANN10/ANN10-RESEARCH.md`
