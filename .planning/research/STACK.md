# Stack Research: annotation v0.3 Visual Reading Canvas

**Project:** PaperForge annotation v0.3 Visual Reading Canvas
**Researched:** 2026-07-03
**Mode:** Stack / implementation choices
**Overall confidence:** HIGH for local plugin stack choices, MEDIUM for future PDF rendering choices

## Executive Recommendation

Build the v0.3 Canvas MVP with the existing Obsidian plugin stack:

- Obsidian `ItemView` for a new PaperForge-owned reading canvas surface
- Plain JavaScript/CommonJS modules under `paperforge/plugin/src/canvas/`
- Existing `vitest`, `jsdom`, `obsidian`, and `obsidian-test-mocks` for automated coverage
- Plain DOM plus SVG for side lanes, cards, anchors, and focused connector lines
- Existing annotation bridge/list/navigation/overlay helpers as the data source

Do not add React, Svelte, D3, Cytoscape, PDF.js, canvas-rendering libraries, or a build system in the Canvas MVP unless a later spike proves the plain DOM approach cannot satisfy the requirements. The first milestone should prove the product shape and integration seam, not introduce a UI framework migration.

## Current Stack Inputs

| Area | Current State | v0.3 Implication |
|------|---------------|------------------|
| Plugin module format | `paperforge/plugin/package.json` uses CommonJS and no bundler | Keep canvas modules compatible with the existing runtime path. |
| Test stack | `vitest`, `jsdom`, `obsidian`, `obsidian-test-mocks` | Add canvas tests beside existing annotation tests. |
| Annotation data | Existing CLI bridge and normalized JS annotation state | Reuse existing contracts; no new backend dependency. |
| Runtime UI | Large `paperforge/plugin/main.js` plus pure helpers in `src/testable.js` | Keep `main.js` changes thin; put new logic behind canvas modules and test hooks. |
| Styling | Single `styles.css` with namespaced PaperForge sections | Add `.paperforge-reading-canvas-*` selectors; avoid reusing sidebar list classes. |

## Recommended Additions

### 1. New Obsidian View Type

Add a new `VIEW_TYPE_PAPERFORGE_READING_CANVAS` registered by the plugin. This gives the canvas its own pane, lifecycle, and view state instead of making the existing dashboard view carry another complex mode.

Suggested responsibility:

```text
PaperForgeReadingCanvasView
  - Obsidian ItemView lifecycle
  - explicit paperKey state
  - delegates load/render/teardown to canvas controller
```

### 2. Canvas Modules Under `src/canvas/`

Use deep modules with small interfaces:

| Module | Purpose |
|--------|---------|
| `context.js` | Resolve explicit paper key / index entry / fallback reason. |
| `controller.js` | Own session state, refresh, selection, teardown, and event wiring. |
| `view-model.js` | Build cards, lanes, anchors, fallback states, and connector intents. |
| `layout.js` | Deterministic left/right lane assignment and connector planning. |
| `surface.js` | PaperForge-owned central reading surface contract. |
| `render.js` | DOM rendering helpers for shell, lanes, cards, anchors, connectors. |

This keeps canvas complexity out of `PaperForgeStatusView` and limits `main.js` to view registration plus integration.

### 3. Plain DOM + SVG Connector Layer

Use normal DOM elements for cards and anchors, with an SVG overlay for connector paths. This is enough for:

- focused selected/hovered card-to-anchor connector lines
- scroll/resize recalculation
- deterministic geometry from PaperForge-owned DOM

Do not introduce a graph/canvas library yet. The MVP does not need freeform node editing, physics, pan/zoom, or multi-paper graph layout.

### 4. Text-First Central Surface

Start with a PaperForge-owned text or page-level reading surface from existing vault files/index metadata. Exact PDF rendering can remain a future adapter behind the same surface interface.

The MVP should support:

- central reading content when fulltext/formal-note content is available
- page-level anchors when exact text positions are unavailable
- existing PDF page open fallback through `resolveAnnotationPdfTarget()` / `openLinkText()`

Avoid making the canvas depend on `.pdf-embed`, `.pdf-viewer`, or native Obsidian PDF DOM selectors.

## Dependencies Not Recommended for MVP

| Dependency / Stack Change | Why Not Now |
|---------------------------|-------------|
| React/Svelte/Vue | Would require bundling/runtime changes and compete with the existing Obsidian DOM style. |
| D3/Cytoscape/graph libs | Overkill for deterministic lanes and focused connectors. |
| PDF.js integration | Heavy, security/performance-sensitive, and unnecessary for first canvas value. |
| Obsidian Canvas file format | Creates a second source of truth and persistent layout semantics too early. |
| New Python annotation APIs | Existing CLI/PFResult bridge already provides the needed data. |
| Persistent canvas settings/localStorage | v0.3 UI state should remain session-local until explicit layout persistence is designed. |

## Testing Strategy

Add focused Vitest suites:

| Test File | Purpose |
|-----------|---------|
| `canvas-viewmodel.test.mjs` | Cards, lanes, fallback states, read-only fields. |
| `canvas-layout.test.mjs` | Deterministic lane placement and connector intent rules. |
| `canvas-surface.test.mjs` | Text/page anchor availability and degradation. |
| `canvas-controller.test.mjs` | Stale load guards, paper-key identity, refresh, teardown. |
| `canvas-dom.test.mjs` | jsdom rendering, no unsafe HTML, forbidden controls absent. |

Keep running the v0.2 focused annotation gate after canvas phases:

```powershell
node --check main.js
npm.cmd test -- annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-overlay.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
```

## Build Contract Risk

The largest stack risk is not missing technology; it is the current lack of a clean shipped-source boundary. `main.js` is the loaded Obsidian entrypoint, while `src/testable.js` holds pure helper copies. v0.3 should avoid expanding that drift.

Preferred approach:

1. Put canvas pure helpers in `src/canvas/*`.
2. Export those helpers for tests.
3. Have `main.js` require or inline only a thin integration layer.
4. Add a runtime test through `main.js.__test` proving the shipped entrypoint uses the same canvas view-model behavior.

If direct `require('./src/canvas/*')` is not possible in the shipped Obsidian plugin, keep a documented manual copy step and parity tests, but treat that as debt to remove.

## Version and Compatibility Notes

- Current plugin dev stack: `vitest ^2.1.0`, `jsdom ^25.0.0`, `obsidian ^1.12.0`, `obsidian-test-mocks ^2.0.0`.
- Current package uses `"type": "commonjs"`.
- No network/runtime dependencies are needed for the MVP.
- New UI should use Obsidian CSS variables and existing PaperForge design tokens, but with canvas-specific class names.

## Roadmap Guidance

1. Start with view registration and deep module skeletons.
2. Build card/view-model contracts before visual polish.
3. Add a controlled central surface before connector lines.
4. Add connectors only over confirmed PaperForge-owned anchors/cards.
5. Keep live Obsidian verification separate from jsdom confidence.

## Sources

- `paperforge/plugin/package.json`
- `.planning/PROJECT.md`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/research/FEATURES.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`
