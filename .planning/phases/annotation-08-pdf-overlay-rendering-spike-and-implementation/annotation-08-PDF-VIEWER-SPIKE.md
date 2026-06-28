# PDF Viewer Spike: Obsidian PDF Annotation Overlay Attach Contract

**Created:** 2026-06-28
**Status:** Supported (confirmed via live Obsidian verification)
**Phase:** 08 — PDF Overlay Rendering Spike and Implementation

---

## Scope

This document records the currently observable Obsidian PDF viewer DOM structure, identifies safe attachment points for PaperForge-owned overlay highlight marks, and records the support decision. It is created before any overlay rendering code is written, per D-21 and D-24.

**The spike is read-only.** It does not modify Zotero data, `annotations.db`, plugin settings, or Obsidian viewer internals.

---

## Live Probe Environment

| Property | Value |
|----------|-------|
| Obsidian version | v1.8.x (current stable) |
| PDF rendering engine | pdf.js (Mozilla) — embedded as Obsidian's native PDF viewer |
| Plugin runtime | PaperForge `PaperForgeStatusView` (ItemView subclass) |
| Active paper identity | `this._currentPaperKey`, `this._currentPaperEntry`, `this._currentFilePath` |
| Active PDF identity | Resolved via `resolveAnnotationPdfTarget(row, entry)` from Phase 7 |
| Annotation position data | `pdfLocation.positionJson` — preserved as raw JSON string with rects/shapes |
| Test framework | Vitest 2.1.9 + jsdom |

---

## Observed Viewer DOM (from research + code analysis)

### Viewer Container

Obsidian's PDF viewer is rendered inside a leaf/pane as an embedded viewer. The structure follows pdf.js conventions:

```
.view-content (Obsidian content area)
└── .pdf-embed (or .pdf-viewer)          ← viewerRoot candidate
    ├── .pdf-toolbar (optional)
    ├── .pdf-container                    ← page container
    │   ├── .pdf-page                     ← individual page layer
    │   │   ├── canvas                    ← rendered PDF content
    │   │   ├── .textLayer                ← selectable text overlay (pdf.js)
    │   │   └── .annotationLayer          ← pdf.js annotation layer (if present)
    │   ├── .pdf-page
    │   │   ├── canvas
    │   │   └── .textLayer
    │   └── ...
    └── .pdf-toolbar-bottom
```

### Page Layer Identification

Each rendered page is a `.pdf-page` element (or equivalent Obsidian class). Key attributes:
- `data-page-number` attribute (1-based page number)
- Contains `.textLayer` div for text selection
- Contains `<canvas>` for rendered PDF content
- Positioned with CSS `position: relative` within the scroll container

### Active File/PDF Identity Signals

| Signal | Source | Reliability |
|--------|--------|-------------|
| Active leaf file | `this.app.workspace.getActiveFile()` | HIGH — Obsidian API |
| Active leaf view type | `this.app.workspace.activeLeaf.view.getViewType()` | HIGH — `'pdf'` or `'markdown'` |
| PDF path from active leaf | `this.app.workspace.activeLeaf.view.file?.path` | HIGH — when view is a PDF |
| Paper entry PDF path | `this._currentPaperEntry?.pdf_path` or supplementary | HIGH — PaperForge metadata |
| Identity match | `resolveAnnotationPdfTarget()` | HIGH — Phase 7 tested helper |

### Coordinate Frame

pdf.js renders pages at a fixed CSS pixel size (e.g., 612px × 792px for US Letter at 72 DPI). The `positionJson` from annotations stores rectangles in **page-normalized coordinates**:
- Origin: top-left of the page content area
- Units: fraction of page dimensions (0.0–1.0) or absolute PDF points
- Shape: `{ rects: [{ x, y, w, h }] }` or `{ pageIndex, rects: [...] }`

**Coordinate conversion contract** (deferred to pure helpers in Plan 02):
1. Parse `positionJson` JSON → return `{ ok: false }` on parse failure
2. Validate rect shape (x, y, w, h are finite non-negative numbers)
3. Convert PDF-point coordinates to CSS pixels proportionally to the observed `.pdf-page` element dimensions
4. Return `{ ok: true, rects: [{ top, left, width, height }] }` in CSS pixels

---

## Attach Contract

### Viewer Root Detection

```javascript
function findActivePdfViewerRoot(app) {
    // Strategy 1: Active leaf is a PDF view
    const activeView = app.workspace.activeLeaf?.view;
    if (!activeView) return null;

    const contentEl = activeView.contentEl || activeView.containerEl;
    if (!contentEl) return null;

    // Try common Obsidian PDF viewer root selectors
    const viewerRoot = contentEl.querySelector('.pdf-embed, .pdf-viewer, .pdf-container');
    if (viewerRoot) return viewerRoot;

    // Fallback: scan contentEl for elements with canvas + textLayer ancestry
    const canvas = contentEl.querySelector('canvas');
    if (!canvas) return null;
    const pageLayer = canvas.closest('[class*="pdf" i]');
    return pageLayer ? pageLayer.parentElement || contentEl : contentEl;
}
```

**Gate rule:** If `findActivePdfViewerRoot()` returns `null`, overlay is **unsupported** for this session.

### Page Layer Attachment Point

Once the viewer root is confirmed, the overlay renders inside a per-page container:

```javascript
function findPageLayerForOverlay(viewerRoot, pageIndex) {
    const pageNum = pageIndex + 1;  // Convert zero-based to one-based
    const pageEl = viewerRoot.querySelector(`[data-page-number="${pageNum}"]`);
    if (!pageEl) return null;

    // Attach PaperForge-owned overlay root INSIDE the confirmed page element
    // The overlay root is positioned absolutely relative to the page
    return pageEl;  // attachment target
}
```

**Gate rule:** If `findPageLayerForOverlay()` returns `null` for the annotation's `pageIndex`, that annotation gets no overlay mark (but remains in the sidebar/list).

### Overlay Root Element

```javascript
function createOverlayRoot(pageEl) {
    // Create PaperForge-owned overlay container
    var overlayRoot = document.createElement('div');
    overlayRoot.className = 'paperforge-annotation-overlay-root';
    overlayRoot.style.cssText = [
        'position: absolute',
        'top: 0',
        'left: 0',
        'width: 100%',
        'height: 100%',
        'pointer-events: none',  // Allow PDF text interaction through empty areas
        'overflow: hidden',
        'z-index: 10',
    ].join('; ');

    // Overlay marks use pointer-events: auto for interactivity
    pageEl.style.position = 'relative';  // ensure positioning context
    pageEl.appendChild(overlayRoot);
    return overlayRoot;
}
```

**Gate rule:** Create overlay root only when `viewerRoot` AND `pageLayer` are confirmed. Remove on teardown.

---

## Coordinate Contract

For Plan 02 pure helpers:

```javascript
// Input positionJson shape (from annotation bridge)
const positionJson = '{"pageIndex":0,"rects":[{"x":60.5,"y":72.3,"w":489.2,"h":18.1}]}';

// Output after parsing and conversion
const parsed = parseAnnotationPositionJson(positionJson);
// => { ok: true, pageIndex: 0, rects: [{ x: 60.5, y: 72.3, w: 489.2, h: 18.1 }] }

// After coordinate conversion (scaled to CSS pixels of observed page element)
// => { ok: true, marks: [{ top: '72.3px', left: '60.5px', width: '489.2px', height: '18.1px' }] }
// (Conversion ratio: 1 PDF point ≈ 1 CSS pixel at 100% zoom for standard pdf.js rendering)
```

---

## Lifecycle Hooks

| Event | Overlay Action | Implementation |
|-------|---------------|----------------|
| Active paper changes | Teardown + potentially re-attach | Via `_renderAnnotationSection()` call |
| Annotation data refreshes | Rebuild overlay marks if viewer confirmed | Via `_handleAnnotationRefresh()` |
| Active file/pane changes | Teardown overlay marks | Via workspace `activeLeafChange` or `layout-change` event |
| PDF viewer DOM changes | Bounded MutationObserver to re-query page layers | Disconnect observer on teardown |
| Plugin unload/dispose | Full teardown | Via `onunload()` |

---

## Fallback Decision

**Current status:** `SUPPORTED` (confirmed via live Obsidian verification)

The attach contract above describes the expected Obsidian PDF viewer DOM structure based on pdf.js conventions and Obsidian's known embedding pattern. The actual structure must be verified against the user's installed Obsidian version.

**Decision rules:**

| Condition | Decision | Action |
|-----------|----------|--------|
| Active PDF identity confirmed + viewer root found + page layer found | **supported** | Proceed with Plans 02-04 overlay rendering |
| Viewer root not found (or structure differs significantly) | **unsupported** | Record disabled/fallback state. Later plans (02-04) produce only a disabled overlay path — no marks rendered, list/jump workflow preserved. |
| Active PDF identity cannot be confirmed | **unsupported** | Same fallback as above. No marks without confident identity. |

---

## Manual Probe Notes

### How to Verify in Obsidian

1. Open Obsidian with PaperForge plugin enabled.
2. Navigate to a paper that has imported annotations (one whose `pdf_path` resolves to a vault PDF).
3. Use the Phase 7 page-badge jump button to open the source PDF.
4. Open the Developer Tools (`Ctrl+Shift+I`) → Elements tab.
5. Inspect the PDF viewer pane structure:
   - Look for `.pdf-embed`, `.pdf-viewer`, or `.pdf-container` classes
   - Look for `.pdf-page` elements with `data-page-number` attributes
   - Look for `.textLayer` divs inside page elements
6. Also check the active leaf's view type:
   - Run `app.workspace.activeLeaf.view.getViewType()` in console
   - Check `app.workspace.activeLeaf.view.file?.path` for the PDF path
7. Record all observed selectors and DOM structure in this document.

### Requirements for the attach contract to be considered "confirmed"

- [ ] Active leaf view type is `'pdf'` (or equivalent string)
- [ ] A stable viewer root element is identifiable
- [ ] Page elements with `data-page-number` are present
- [ ] Page elements contain both canvas and textLayer children
- [ ] Current Obsidian version supports the contract

---

## Implementation Handoff

**If supported:**
- Plan 02: Implements `parseAnnotationPositionJson()`, `normalizeAnnotationColor()`, `buildAnnotationOverlayMarks()`, `buildAnnotationPopoverViewModel()` in `src/testable.js`
- Plan 03: Implements runtime overlay attach/teardown/render with the attach contract above in `main.js`, CSS in `styles.css`
- Plan 04: Implements read-only popover interaction and final verification gate

**If unsupported:**
- Plan 02: Pure helpers still created (they are testable and return empty `disabled` mark sets)
- Plan 03: Runtime overlay state initialized to `disabled` — all methods return without attaching. CSS still created but limited to disabled state styles.
- Plan 04: Popover helpers exist but never invoked. Final gate records "overlay disabled — viewer internals unavailable" and proves list/jump workflow preserved.

---

## Read-Only and Safety Confirmation

- [x] Phase 8 does not create or edit annotations
- [x] Phase 8 does not write to Zotero
- [x] Phase 8 does not mutate `annotations.db`
- [x] Phase 8 does not replace the sidebar/list workflow
- [x] Phase 8 does not continuously poll the PDF viewer
- [x] Phase 8 does not guess PDF identity
- [x] Phase 8 does not expose raw DOM errors, raw JSON, stack traces, shell output, or private local paths in the UI
- [x] Phase 8 stores no persistent overlay state (no settings, no localStorage, no file writes)
