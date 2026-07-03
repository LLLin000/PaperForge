# Architecture Research: annotation v0.3 Visual Reading Canvas

**Project:** PaperForge annotation v0.3 Visual Reading Canvas
**Researched:** 2026-07-02
**Mode:** Ecosystem / integration architecture
**Overall confidence:** HIGH for codebase integration, MEDIUM for live Obsidian PDF-viewer behavior

## Executive Recommendation

Build the v0.3 canvas as a new PaperForge-owned Obsidian `ItemView`, not as another branch inside `PaperForgeStatusView._renderPaperMode()` and not as an overlay on the native Obsidian PDF viewer. The current plugin already has the right data contracts: `loadAnnotationsForPaper()`, `ANNOTATION_LOAD_STATES`, `buildAnnotationListViewModel()`, `resolveAnnotationPdfTarget()`, `buildAnnotationOverlayMarks()`, and read-only popover helpers in `paperforge/plugin/src/testable.js`. The canvas should consume those contracts and hide all layout, lane, anchor, and connector complexity behind new deep modules.

The central architecture decision is:

```text
Existing annotation bridge/list/overlay data
  -> new canvas view-model module
  -> new PaperForge Reading Canvas ItemView
  -> PaperForge-owned reading surface + card lanes + connector layer
  -> safe fallback to existing annotation list/PDF navigation
```

Do not couple the new canvas to native Obsidian PDF internals such as `.pdf-embed`, `.pdf-viewer`, page-layer DOM, or canvas elements. The v0.2 overlay may keep that risk-gated path as an optional enhancement, but the v0.3 canvas should own its DOM and geometry. The MVP can render a text-first central reading surface from `fulltext_path`/formal note content and keep PDF grounding as page-level navigation through `openLinkText()`. Exact PDF rectangle connectors should only render when a PaperForge-owned surface can confirm geometry.

## Existing Architecture Fit

Current relevant facts from the codebase:

| Existing Surface | Current Role | Canvas Implication |
|------------------|--------------|--------------------|
| `PaperForgeStatusView` in `paperforge/plugin/main.js` | Right-side/dashboard ItemView with global, collection, and paper modes | Keep it as the dashboard and entry point. Do not add the canvas layout here. |
| `loadAnnotationsForPaper()` in `src/testable.js` | CLI bridge: `annotation status --json` then `annotation export --paper KEY --json` | Reuse directly as the canvas annotation source. No backend rework. |
| `createAnnotationLifecycleController()` | Pure stale-result guarded active-paper annotation loader | Reuse pattern for canvas session state. |
| `buildAnnotationListViewModel()` | Existing list UI projection | Reuse row sorting/filtering ideas, but create a canvas-specific view-model instead of bending list rows into cards. |
| `resolveAnnotationPdfTarget()` | Safe attachment/page identity resolver | Reuse for card navigation and PDF fallback. |
| `buildAnnotationOverlayMarks()` | Converts annotation rows and PDF path into mark view-models | Reuse parsing/color/identity logic, but do not reuse native viewer DOM attachment. |
| `_tryAttachAnnotationOverlay()` / `_findPdfViewerRoot()` | Risk-gated native PDF viewer overlay | Treat as v0.2 legacy/fallback only. Do not make the canvas depend on these selectors. |
| `styles.css` annotation sections | Existing compact sidebar/list and overlay styles | Add separate `.paperforge-reading-canvas-*` styles. Avoid mutating list styles for canvas layout. |

## Recommended Architecture

```text
paperforge/plugin/main.js
  - registers dashboard view and new canvas view
  - adds command/button to open canvas
  - delegates canvas runtime to src/canvas/*

paperforge/plugin/src/canvas/
  context.js        - resolve active paper/index entry/view state
  annotations.js    - load lifecycle wrapper around existing annotation bridge
  view-model.js     - build cards, lanes, anchors, empty/error/fallback states
  layout.js         - lane assignment and connector geometry planning
  surface.js        - PaperForge-owned reading surface contract
  render.js         - DOM rendering helpers for view, lanes, cards, connectors
  controller.js     - canvas session state, event wiring, refresh/navigation

paperforge/plugin/src/testable.js
  - exports pure canvas helpers for Vitest

paperforge/plugin/styles.css
  - owns canvas layout, lane, card, anchor, selected, and connector styles
```

The deep-module boundary should be `PaperForgeReadingCanvasView`: Obsidian lifecycle in, one small controller API out. The view class should not manually compute lane layout, parse annotation coordinates, or decide fallback states inline.

### New Modules

| Module | Responsibility | Interface Shape |
|--------|----------------|-----------------|
| `src/canvas/context.js` | Resolve a canvas paper context from view state, active file, or explicit paper key. | `resolveCanvasContext({ app, paperKey, indexItems }) -> { ok, paperKey, entry, source, reason }` |
| `src/canvas/annotations.js` | Wrap existing annotation loader with stale guards and refresh reasons. | `createCanvasAnnotationController({ loader })` |
| `src/canvas/view-model.js` | Convert paper entry + annotation state + UI state into renderable canvas state. | `buildReadingCanvasViewModel({ entry, annotationState, surfaceState, uiState })` |
| `src/canvas/layout.js` | Assign annotation cards to left/right lanes and create connector intents from anchor/card IDs. | `planCanvasLayout({ cards, anchors, viewport })` |
| `src/canvas/surface.js` | Define PaperForge-owned reading surface contract and text-first MVP implementation. | `createTextReadingSurface({ app, entry })`, future `createPdfReadingSurface()` |
| `src/canvas/render.js` | Render DOM for header, central surface, lanes, cards, connector SVG, fallback states. | `renderReadingCanvas(rootEl, vm, handlers)` |
| `src/canvas/controller.js` | Coordinate context, annotation loading, surface mounting, card selection, scroll, refresh, teardown. | `new PaperForgeCanvasController({ app, plugin, contentEl, state })` |

### Modified Modules

| Module | Modification |
|--------|--------------|
| `paperforge/plugin/main.js` | Add `VIEW_TYPE_PAPERFORGE_CANVAS`, register the view, add command `PaperForge: Open Reading Canvas`, add paper-mode button, export test hook. Keep changes thin. |
| `paperforge/plugin/src/testable.js` | Re-export pure canvas helpers or import from `src/canvas/*` so tests do not depend on Obsidian. |
| `paperforge/plugin/styles.css` | Add namespaced canvas styles only. Do not repurpose `.paperforge-annotations-*` list classes. |
| `paperforge/plugin/tests/*.test.mjs` | Add canvas view-model, layout, controller, and DOM tests. Preserve existing annotation tests. |

No Python annotation backend modules should change for the MVP.

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| Canvas View | Obsidian `ItemView` lifecycle, view type, display text/icon, opening with state | Canvas Controller |
| Canvas Controller | Session state, active paper, refresh, stale-load guard, selected card, teardown | Context resolver, annotation controller, reading surface, renderer |
| Context Resolver | Maps explicit `paperKey`, active note, active PDF, or workspace path to canonical index entry | Existing index loading helpers from dashboard |
| Annotation Controller | Loads annotations through existing CLI bridge, preserves stale renderable data on failure | `loadAnnotationsForPaper()`, `mergeAnnotationRefreshResult()` |
| Canvas View-Model | Builds cards, lanes, anchor states, fallback banners, navigation actions | Existing normalized annotation rows and paper entry |
| Reading Surface | Renders central PaperForge-owned content and exposes anchor geometry registry | Vault reads, annotation anchors |
| Card Lane Renderer | Displays read-only annotation cards with selected text, comment, page, type/color, provenance | Canvas view-model and controller handlers |
| Connector Layer | Draws visual lines between registered anchors and visible cards | Layout planner, DOM measurements |
| Fallback Adapter | Opens existing dashboard/list/PDF page jump when canvas prerequisites fail | `PaperForgeStatusView.open()`, `openLinkText()` |

## Data Flow

### Open Canvas

```text
User command / dashboard button
  -> open or reveal VIEW_TYPE_PAPERFORGE_CANVAS with { paperKey }
  -> Canvas View creates Canvas Controller
  -> Context Resolver finds canonical entry from index
  -> Annotation Controller loads existing annotation state
  -> Reading Surface mounts text/PDF-safe central surface
  -> buildReadingCanvasViewModel()
  -> renderReadingCanvas()
```

### Annotation Card Navigation

```text
Card click
  -> controller selects card
  -> if canvas anchor exists: scroll central surface to anchor and highlight card/anchor
  -> else if resolveAnnotationPdfTarget() succeeds: open PDF through app.workspace.openLinkText()
  -> else: show read-only unavailable reason
```

### Connector Rendering

```text
Annotation rows
  -> build canvas card models with stable ids from getAnnotationIdentity()
  -> reading surface registers anchors by card/annotation id
  -> layout module assigns cards to left/right lanes
  -> connector layer measures PaperForge-owned DOM nodes
  -> SVG paths render only for confirmed visible anchor/card pairs
```

Connectors must be opportunistic. Missing coordinates, missing PDF identity, missing page labels, or unconfirmed text anchors should degrade to a grounded card without a connector, not to a native PDF DOM probe.

## View-Model Contract

Create a canvas-specific view-model instead of passing list rows directly to the renderer.

```javascript
{
  state: "ready" | "loading" | "empty" | "missing-paper" | "missing-db" | "error",
  paper: {
    key: "ZOTEROKEY",
    title: "...",
    authors: [],
    year: 2024,
    pdfTarget: { ok: true, path: "Resources/...", page: null }
  },
  surface: {
    kind: "text" | "pdf-placeholder" | "unavailable",
    sourcePath: "Resources/Literature/.../fulltext.md",
    anchors: []
  },
  lanes: {
    left: [card],
    right: [card]
  },
  connectors: [
    { id, fromAnchorId, toCardId, status: "ready" | "pending-geometry" }
  ],
  fallback: {
    canOpenDashboardList: true,
    canOpenPdf: true,
    reason: null
  }
}
```

Each card should include:

```javascript
{
  id,
  annotationId,
  lane: "left" | "right",
  selectedText,
  comment,
  pageLabel,
  pageNumber,
  type,
  color,
  source,
  isReadonly: true,
  attachmentKey,
  anchor: {
    status: "exact" | "page" | "unresolved",
    anchorId,
    reason
  }
}
```

This keeps the renderer simple and makes the roadmap testable phase by phase.

## Reading Surface Strategy

### MVP Surface: Text-First

Use `fulltext_path` or the formal note body as the first central reading surface. This is the lowest-risk way to build a PaperForge-controlled canvas because the plugin can read vault files and render sanitized text/Markdown without depending on Obsidian PDF internals.

Recommended MVP behavior:

- If `entry.fulltext_path` exists, render the OCR/fulltext content in the central column.
- If only `entry.note_path` exists, render the paper overview or formal note content as a degraded reading surface.
- If neither exists, show an unavailable surface with buttons for existing PDF/list fallback.
- Create page-level anchor bands when annotation rows have `pageIndex`/`pageLabel`.
- Create exact text anchors only when selected text can be matched unambiguously in the rendered text. Otherwise mark the card `anchor.status = "page"` or `"unresolved"`.

### PDF Surface: Future Behind Same Interface

A richer PDF surface can be added later behind `surface.js`, but it must be PaperForge-owned. Acceptable directions:

- A bundled PDF renderer controlled by PaperForge.
- A simple PDF placeholder/preview that delegates page opening to Obsidian through `openLinkText()`.

Avoid:

- Querying Obsidian native PDF page DOM for the canvas.
- Depending on `.pdf-embed`, `.pdf-viewer`, `.pdf-container`, `canvas`, or `[data-page-number]` in the canvas MVP.
- Writing code where connector geometry depends on the active native PDF leaf.

## Obsidian Surface Integration

Use two distinct Obsidian surfaces:

| Surface | Role |
|---------|------|
| Existing `paperforge-status` view | Dashboard, paper overview, compact annotation list, setup/runtime controls |
| New `paperforge-reading-canvas` view | Main reading workspace for one paper, with central surface, side annotation lanes, and connectors |

Open behavior:

```javascript
static async open(plugin, paperKey) {
  const leaf = plugin.app.workspace.getLeaf(true);
  await leaf.setViewState({
    type: VIEW_TYPE_PAPERFORGE_CANVAS,
    active: true,
    state: { paperKey }
  });
  plugin.app.workspace.revealLeaf(leaf);
}
```

The canvas should prefer explicit view state over global active-file tracking. The dashboard can follow active files because it is a companion panel. The canvas is a reading workspace and should not suddenly switch papers when the user clicks another leaf. Add a manual "follow active paper" mode only after the stable explicit-paper MVP works.

## Fallback Architecture

Fallback is part of the design, not an exception path.

| Missing Capability | Canvas Behavior | Fallback |
|--------------------|-----------------|----------|
| No paper key | Show missing-paper state | Button: open dashboard |
| Paper key not in index | Show stale/missing index state | Button: sync or dashboard |
| No annotations DB | Show missing-db state | Existing annotation status/list flow remains source of truth |
| No annotations | Show empty canvas with paper surface | Existing PDF/fulltext buttons remain usable |
| No fulltext/note surface | Show cards in lanes with unavailable center | Card page buttons use `openLinkText()` |
| No exact anchor geometry | Render cards without connector | Page-level navigation remains available |
| Canvas runtime error | Tear down canvas DOM | Open existing status view/list |

## Testing Surface

### Pure Vitest Tests

Add tests under `paperforge/plugin/tests/`:

| Test File | Coverage |
|-----------|----------|
| `canvas-viewmodel.test.mjs` | State mapping, card fields, read-only provenance, fallback states |
| `canvas-layout.test.mjs` | Left/right lane assignment, stable ordering, connector intent creation |
| `canvas-anchors.test.mjs` | Exact/page/unresolved anchor classification and degradation |
| `canvas-controller.test.mjs` | Stale load guard, refresh behavior, explicit paper state |
| `canvas-dom.test.mjs` | jsdom render, no `innerHTML` for annotation text, cleanup on close |

### Existing Tests to Preserve

Run existing plugin tests after each canvas phase:

```bash
cd paperforge/plugin
npm test
node --check main.js
```

Relevant existing suites:

- `annotation-bridge.test.mjs`
- `annotation-lifecycle.test.mjs`
- `annotation-list-viewmodel.test.mjs`
- `annotation-navigation.test.mjs`
- `annotation-overlay.test.mjs`
- `annotation-main-runtime.test.mjs`
- `annotation-section-dom.test.mjs`

### Manual/Runtime Gate

The v0.2 live Obsidian PDF viewer harness is still pending. v0.3 must not claim native PDF overlay reliability until that harness is recorded. The canvas MVP can be complete without that harness if it uses PaperForge-owned DOM and page-level `openLinkText()` fallback.

## Build Order for Roadmap

1. **Canvas Module Skeleton**
   - Add `VIEW_TYPE_PAPERFORGE_CANVAS`.
   - Add `src/canvas/*` module skeletons and test exports.
   - Add open command and paper-mode dashboard button.
   - Deliverable: blank canvas opens for explicit paper key and tears down cleanly.

2. **Context and Annotation Controller**
   - Extract/reuse context resolution from status view.
   - Wrap `loadAnnotationsForPaper()` with stale guards.
   - Preserve missing-paper, missing-db, empty, CLI-error, invalid-json states.
   - Deliverable: canvas can load the same annotation state as the existing list.

3. **Canvas View-Model and Cards**
   - Build canvas card model from normalized annotation rows.
   - Preserve sorting by reading order and read-only provenance.
   - Add left/right lane assignment.
   - Deliverable: side lanes show cards without central connectors.

4. **Reading Surface MVP**
   - Render fulltext/formal note central surface.
   - Register page-level and exact text anchors where safe.
   - Add selected-card scroll behavior.
   - Deliverable: cards navigate to central anchors or fall back to PDF page open.

5. **Connector Foundation**
   - Add SVG connector layer over PaperForge-owned canvas DOM.
   - Compute geometry only from canvas-owned anchors/cards.
   - Hide connectors when geometry is unavailable.
   - Deliverable: connector lines work for confirmed central anchors without native PDF DOM coupling.

6. **Safe Fallback and Polish**
   - Add missing-state banners, dashboard/list fallback buttons, refresh states, cleanup tests.
   - Run existing annotation test suite and `node --check`.
   - Deliverable: Canvas MVP is usable and cannot regress existing annotation list/overlay.

## Phase Dependencies

```text
Canvas view registration
  -> context resolver
  -> annotation controller
  -> canvas view-model
  -> lane/card renderer
  -> reading surface anchors
  -> connector layer
  -> fallback polish
```

The connector layer depends on the reading surface anchor registry. Do not build connectors first; without owned anchors it will pull the implementation toward native PDF internals.

## Anti-Patterns to Avoid

### Adding Canvas Logic Directly to `_renderPaperMode()`

**What goes wrong:** `main.js` is already large and mixes dashboard, settings, annotation list, overlay, runtime, and setup concerns.
**Instead:** Register a separate canvas view and delegate runtime work to `src/canvas/controller.js`.

### Sharing DOM Classes With the Existing Annotation List

**What goes wrong:** Canvas cards and compact sidebar rows need different density, layout, interaction, and resize behavior.
**Instead:** Use namespaced classes such as `.paperforge-reading-canvas`, `.paperforge-canvas-card`, `.paperforge-canvas-lane`, `.paperforge-canvas-connector`.

### Treating Native PDF Overlay as the Canvas Foundation

**What goes wrong:** Native PDF DOM selectors are explicitly risk-gated in v0.2 and may change across Obsidian versions.
**Instead:** Keep native overlay optional and build the canvas on PaperForge-owned DOM. Use `openLinkText()` for PDF navigation fallback.

### Re-querying Annotations Independently Per Component

**What goes wrong:** Lanes, connectors, and surface highlights can race and show different annotation snapshots.
**Instead:** One canvas controller owns one annotation state snapshot and passes it through the view-model.

### Making Canvas Read/Write

**What goes wrong:** Editing annotations introduces schema, conflict, and Zotero write-back decisions outside v0.3 scope.
**Instead:** Every card and popover remains read-only. Explicitly omit edit/delete/save/write-back controls.

## Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `main.js` grows further | High | New `src/canvas/*` modules, tiny registration changes only |
| Canvas accidentally depends on native PDF internals | High | Text-first surface, owned DOM anchors, tests that do not require `.pdf-*` selectors |
| Annotation state drift between dashboard and canvas | Medium | Reuse existing loader and normalized row contracts |
| Connector layout is unstable on resize/scroll | Medium | Connector layer measures only visible owned DOM nodes and redraws on `ResizeObserver`/scroll |
| Fulltext does not map cleanly to PDF annotations | Medium | Page-level anchors first, exact anchors only when unambiguous |
| Testable source diverges from shipped `main.js` | Medium | Prefer `require('./src/canvas/*')` from `main.js`; avoid manual copy/paste for new canvas helpers |

## Sources

- `.planning/PROJECT.md` - current milestone scope and carry-over constraints.
- `.planning/codebase/ARCHITECTURE.md` - existing CLI/plugin/domain layer map and annotation display flow.
- `.planning/codebase/STRUCTURE.md` - where to add plugin UI and annotation code.
- `.planning/codebase/CONCERNS.md` - `main.js` bloat, native Obsidian runtime fragility, test gaps.
- `paperforge/plugin/main.js` - current `PaperForgeStatusView`, annotation list runtime, overlay runtime, view registration.
- `paperforge/plugin/src/testable.js` - annotation bridge, lifecycle controller, list view-models, navigation helpers, overlay mark builders.
- `paperforge/plugin/styles.css` - existing dashboard, annotation list, and overlay styling boundaries.

## Research Notes

The `gsd-tools` research-plan and confidence-classifier CLI was not available on PATH in this environment, so no cache seam was used. This architecture is based on the checked-in project docs and source files listed above. Confidence is high for the PaperForge integration recommendation because it follows existing local contracts; confidence remains medium for any live Obsidian PDF-viewer internals because the milestone itself records that the live PDF harness is still pending.
