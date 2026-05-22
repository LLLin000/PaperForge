# Obsidian PDF Overlay Feasibility Analysis

> Status: FEASIBLE | Reference: PDF++ (RyotaUshio/obsidian-pdf-plus)

## Verdict

**Technically feasible** via monkey-patching Obsidian's private PDF viewer internals. PDF++ (2095 stars, 254 releases) has proven this approach works. However, there is **no public Obsidian API** for PDF viewing — every hook is reverse-engineered.

## The Alternative: Why Not Build A Custom PDF View?

| Approach | Pros | Cons |
|----------|------|------|
| Monkey-patch native viewer | Seamless UX, reuse native features | Fragile, requires version-gating |
| Custom view type + loadPdfJs() | Stable API, full control | User loses native PDF features, UX fragmentation |

**User chose: monkey-patch native viewer.**

## How PDF++ Patches the PDF Viewer

### Core Patcher: `monkey-around`

```typescript
import { around } from 'monkey-around';

export const patchPDFInternals = (plugin: Plugin): boolean => {
    plugin.register(around(PDFViewerChild.prototype, {
        load(old) {
            return function () {
                // Plugin initialization here
                old.call(this);
            };
        },
        loadFile(old) {
            return function (file: TFile) {
                old.call(this, file);
                // Create visualizer, register event listeners
            };
        }
    }));
};
```

### Patch Chain

```
patchWorkspace()         → WorkspaceLeaf openLinkText
patchPDFView()           → PDFView.prototype (getState, setState, onLoadFile)
patchPDFInternals()      → PDFViewerComponent, PDFViewerChild, ObsidianViewer
patchPDFInternalFromPDFEmbed() → PDF embeds
patchBacklink()          → backlink pane
```

## DOM Structure of Obsidian's PDF Viewer

```
div.pdf-viewer-container
  div.pdf-viewer
    div.page[data-page-number="1"]
      canvas.canvasWrapper
        canvas               ← rendered PDF canvas
      div.textLayer
        span.textLayerNode[data-idx]
      div.annotationLayer
        section[data-annotation-id]
      div.custom-overlay-layer  ← PaperForge injects here
        div.annotation-highlight
    div.page[data-page-number="2"]...
```

## Key Obsidian Internal Classes

| Class | How to Access |
|-------|---------------|
| `PDFView` | `leaf.view` on 'pdf' type leaf |
| `PDFViewerComponent` | `pdfView.viewer` |
| `PDFViewerChild` | `viewerComponent.child` |
| `ObsidianViewer` | `child.pdfViewer` |
| `PDFPageView` | `pdfViewer.getPageView(n)` |
| `EventBus` | `child.pdfViewer.eventBus` |

All obtained via:
```typescript
const pdfLeaves = app.workspace.getLeavesOfType('pdf');
const pdfView = pdfLeaves[0].view as any;
```

## Events to Listen To

| Event | When to Rerender |
|-------|------------------|
| `textlayerrendered` | Page text layer ready, safe to render text-based annotations |
| `annotationlayerrendered` | Page annotation layer ready |
| `pagerendered` | Page canvas rendered |
| `pagechanging` | Current page changed |
| `scalechanged` | Zoom level changed |
| `pagesloaded` | All pages loaded |

```typescript
child.pdfViewer.eventBus.on('textlayerrendered', (data) => {
    const pageView = data.source; // PDFPageView
    renderAnnotationsForPage(pageView, annotationsForPage(pageView.id));
});
```

## Coordinate Transformation

### PDF → Overlay Position
```typescript
function placeAnnotationRect(rect: number[], pageView: PDFPageView) {
    const viewport = pageView.viewport;
    const [left, bottom, right, top] = rect;

    // Mirror Y axis (PDF origin is bottom-left, screen is top-left)
    const mirrored = window.pdfjsLib.Util.normalizeRect([
        left,
        viewport.viewBox[3] - bottom + viewport.viewBox[1],
        right,
        viewport.viewBox[3] - top + viewport.viewBox[1]
    ]);

    // Create overlay layer per page
    const pageDiv = pageView.div;
    let layer = pageDiv.querySelector('div.pf-annotation-overlay');
    if (!layer) {
        layer = pageDiv.createDiv('pf-annotation-overlay');
        window.pdfjsLib.setLayerDimensions(layer, pageView.viewport);
    }

    // Place rect with percentage positioning (zoom-independent)
    const pageW = viewport.viewBox[2] - viewport.viewBox[0];
    const pageH = viewport.viewBox[3] - viewport.viewBox[1];
    const el = createDiv('pf-annotation-rect');
    el.setCssStyles({
        left: `${100 * (mirrored[0] - viewport.viewBox[0]) / pageW}%`,
        top: `${100 * (mirrored[1] - viewport.viewBox[1]) / pageH}%`,
        width: `${100 * (mirrored[2] - mirrored[0]) / pageW}%`,
        height: `${100 * (mirrored[3] - mirrored[1]) / pageH}%`,
        background: `rgba(255, 212, 0, 0.25)`,
    });
    layer.appendChild(el);
}
```

## Selection → Annotation

```typescript
function getSelectionRect(pageView: PDFPageView): Rect[] | null {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return null;

    const textLayer = pageView.textLayer;
    if (!textLayer) return null;

    // Iterate through text layer nodes to find selected range
    // Extract PDF coordinates from text content items
    // Returns array of [left, top, right, bottom] rects
}
```

## Dark Mode Handling

```css
.theme-light .pf-annotation-highlight {
    background: rgba(255, 212, 0, 0.25);
}
.theme-dark .pf-annotation-highlight {
    background: rgba(255, 200, 0, 0.2);
}

.theme-light .pf-annotation-underline {
    border-bottom: 2px solid #ff6666;
}
.theme-dark .pf-annotation-underline {
    border-bottom: 2px solid #ff8888;
}
```

Listen for theme changes:
```typescript
app.workspace.on('css-change', () => {
    const isDark = document.body.classList.contains('theme-dark');
    // Re-render with appropriate colors
});
```

## Getting Current PDF Path

```typescript
const activeLeaf = app.workspace.activeLeaf;
if (activeLeaf?.view?.file?.extension === 'pdf') {
    const pdfFile: TFile = activeLeaf.view.file;
    const path = pdfFile.path; // e.g. "Resources/Literature/domain/paper.pdf"
}
```

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Obsidian version breakage | `requireApiVersion()` checks; version-gate patches |
| PDF.js version changes | PDF++ handles v1.7.7 vs v1.8.0 diffs (ObsidianViewer class vs factory) |
| Conflicts with other plugins | Document known incompatibilities; avoid patching same methods |
| Performance with 500+ annotations | Cache rects per annotation ID; debounce rerender; requestAnimationFrame |
| Mobile support | Check `Platform.isDesktopApp`; degrade gracefully |

## Recommended Libraries

| Library | Purpose |
|---------|---------|
| `monkey-around` | Prototype patching (PDF++ proven) |
| `obsidian` (built-in) | Plugin API, TFile, Workspace, loadPdfJs() |

No additional PDF.js bundling needed — Obsidian provides it natively.
