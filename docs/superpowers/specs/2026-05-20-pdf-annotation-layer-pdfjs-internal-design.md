# PaperForge PDF Annotation Layer: PDF.js Internal Route Design

**Date:** 2026-05-20
**Status:** Proposed
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

PaperForge should replace its current DOM-only PDF overlay experiment with a PDF.js-internal overlay architecture modeled on PDF++.

The critical design change is:

1. Stop treating Obsidian's native PDF viewer as a generic DOM tree.
2. Patch the viewer lifecycle to obtain PDF.js page objects (`pageView`, `viewport`).
3. Mount annotation layers on `pageView.div`.
4. Align each layer with `window.pdfjsLib.setLayerDimensions(layer, pageView.viewport)`.
5. Render annotation rects in the same viewport coordinate space used by PDF.js.

This design keeps the existing Python-side import/cache model, but replaces the plugin-side rendering path.

---

## 2. Why A New Design Is Needed

The first overlay implementation proved that PaperForge can:

- import real Zotero annotations from `zotero.sqlite`
- normalize them correctly into `annotations.db`
- expose them to the plugin through `annotation-cache.json`
- compute real screen-space rect DOM nodes

However, real-world debugging against a live paper showed that the current rendering strategy is still wrong.

### 2.1 Proven Facts From Debugging

For the real Zotero annotation `LJ8FR3BS`:

- Zotero SQLite, `annotations.db`, and `annotation-cache.json` all agree on:
  - `parent_key = 5AWBHQ59`
  - `type = highlight`
  - `color = #aaaaaa`
  - `pageIndex = 0`
  - `rects = [[61.137, 323.189, 291.762, 331.788], ...]`
- The plugin creates real overlay rect DOM nodes.
- The overlay rect has a valid `getBoundingClientRect()`.
- `document.elementFromPoint()` at the rect center returns the overlay node itself (`SELF`).

So the failure is not:

- SQLite parsing
- import normalization
- JSON cache shape
- missing DOM nodes
- trivial `z-index` loss

### 2.2 Actual Failure Mode

The failure is architectural:

- the plugin currently renders into a generic absolute-positioned layer inferred from `.page`, `canvas`, and related DOM boxes
- PDF++ does not do that
- PDF++ renders through PDF.js page internals and explicitly aligns the layer with `setLayerDimensions(..., viewport)`

The DOM-only route is therefore considered disproven for PaperForge.

---

## 3. Product Decision

### Chosen Plugin-Side Route

- **Keep:** Python import pipeline, `annotations.db`, CLI/cache bridge
- **Replace:** DOM-only overlay placement logic
- **Adopt:** PDF.js internal page/viewport aligned rendering

### Why

This is the smallest change that addresses the proven root cause without reopening the Python architecture.

---

## 4. Goals

### 4.1 Primary Goals

1. Render imported Zotero annotations visibly and reliably inside Obsidian's native PDF viewer.
2. Use the same page viewport coordinate system as PDF.js.
3. Re-render overlays from PDF viewer lifecycle events instead of generic DOM mutation heuristics.
4. Preserve existing local annotation create/edit/delete capabilities where possible.

### 4.2 Secondary Goals

1. Remove noisy debug-only rendering paths from the plugin.
2. Reduce overlay re-render churn during scroll/zoom.
3. Keep the current `annotation-cache.json` read path intact.

### 4.3 Non-Goals

1. No rewrite of the Python annotation import layer.
2. No custom embedded PDF reader.
3. No Zotero write-back in this phase.
4. No attempt to support every Obsidian version; private PDF internals remain a managed compatibility risk.

---

## 5. Design Principles

1. **Python data path stays stable.** The rendering rewrite should not disturb the proven SQLite import/cache pipeline.
2. **Render in PDF.js coordinate space, not guessed DOM space.**
3. **Use native viewer lifecycle events, not broad MutationObserver retries.**
4. **Patch the smallest internal surface that exposes `pageView` and `viewport`.**
5. **Fail soft.** If PDF internals are unavailable, the plugin should disable overlays for that session rather than degrade the whole viewer.

---

## 6. Research Basis

### 6.1 PDF++ Reference Pattern

PDF++ creates its layer like this conceptually:

```ts
const pageDiv = pageView.div;
let layer = pageDiv.querySelector('div.pdf-plus-backlink-highlight-layer');
if (!layer) {
  layer = pageDiv.createDiv('pdf-plus-backlink-highlight-layer');
  window.pdfjsLib.setLayerDimensions(layer, pageView.viewport);
}
```

It also renders rectangles using the viewport's `viewBox`, not guessed page DOM dimensions.

### 6.2 Current PaperForge Gap

PaperForge currently:

- appends `.pf-annotation-overlay` directly to `.page`
- infers layer geometry from visible DOM boxes
- derives coordinates from cached page sizes and percentages
- uses MutationObserver as a coarse refresh trigger

This is close enough to create DOM nodes, but not close enough to guarantee native viewer alignment.

---

## 7. Proposed Architecture

## 7.1 System Overview

```text
annotation-cache.json
        ↓
Obsidian plugin file→paper resolution
        ↓
PDF view internal patch
        ↓
PDF.js pageView / viewport discovery
        ↓
viewport-aligned overlay layer
        ↓
annotation rect rendering + local actions
```

## 7.2 Internal Patch Boundary

The plugin should patch the native PDF viewer only far enough to gain access to:

- current PDF file path
- `pdfViewer`
- `pdfViewer.getPageView(pageNumberIndex)`
- PDF.js event bus events such as:
  - `pagerendered`
  - `textlayerrendered`
  - `annotationlayerrendered`
  - `scalechanged`

## 7.3 Layer Alignment

For each annotated page:

1. Get `pageView`.
2. Get or create `.pf-annotation-overlay` on `pageView.div`.
3. Call `window.pdfjsLib.setLayerDimensions(layer, pageView.viewport)`.
4. Render rects as percentages of `pageView.viewport.viewBox`.

## 7.4 Coordinate Mapping

Input rects remain Zotero/PDF coordinates:

```text
[left, bottom, right, top]
```

Rendering should:

1. mirror Y into viewport display space
2. normalize against `viewport.viewBox`
3. set CSS percentages relative to the aligned overlay layer

This removes the need to guess page dimensions from:

- canvas pixels
- DOM boxes
- hardcoded letter/A4 fallbacks

## 7.5 Event-Driven Refresh

Replace broad mutation-driven rerenders with page/viewer events:

- initial file load → fetch annotations once
- `pagerendered` / `textlayerrendered` → ensure page layer exists, repaint that page only
- `scalechanged` → clear/rebuild visible layers
- annotation create/delete/update → invalidate local page cache and repaint affected page only

---

## 8. Data Contracts

## 8.1 Cache Contract

The existing `annotation-cache.json` contract remains valid.

Required fields per annotation:

- `id`
- `paper_id`
- `zotero_key`
- `zotero_attachment_key`
- `type`
- `page_index`
- `selected_text`
- `comment`
- `color`
- `sort_index`
- `position.rects`
- `is_readonly`

`page_width/page_height` may remain in the cache as optional debug metadata, but the plugin should no longer depend on them for final placement when `viewport` is available.

## 8.2 Plugin Runtime State

The plugin should maintain:

- current `pdfPath`
- current `paperId`
- current annotations grouped by `page_index`
- per-page overlay layer references
- per-page rendered annotation ids for cheap repaint decisions

---

## 9. Module/File Strategy

Respect current repo reality:

- `paperforge/plugin/main.js` remains the runtime entry point
- `paperforge/plugin/src/testable.js` remains the home for pure helpers

Recommended logical slices inside `main.js`:

1. PDF internal discovery helpers
2. overlay layer manager
3. viewport-based rect renderer
4. event registration / teardown
5. selection-to-create and popover actions

No forced multi-file runtime split is required for this phase.

---

## 10. Risks

### Risk 1: Obsidian PDF internals differ across versions

Mitigation:

- add version/shape guards around internal access
- log a single concise disablement message
- avoid crashing plugin startup

### Risk 2: Cannot reliably obtain `pageView` from current patch point

Mitigation:

- probe multiple internal access paths already documented by PDF++ research
- patch at file-load and render-event boundaries
- fall back to disabling overlays rather than continuing with DOM-only placement

### Risk 3: Selection-create path depends on text layer timing

Mitigation:

- register selection handlers only after page text layer render readiness
- keep current create command bridge unchanged until overlay rendering is stable

---

## 11. Acceptance Criteria

The phase is complete when all of the following are true on a real Zotero-backed PDF in Obsidian:

1. Imported annotations appear visibly on the correct page and over the correct text region.
2. Overlays remain aligned after zoom changes.
3. Overlays remain aligned after scrolling to newly rendered pages.
4. Console no longer depends on broad debug spam to understand rendering state.
5. The plugin no longer depends on guessed letter/A4 sizing for primary placement.
6. Existing local create/delete behavior still works, or is explicitly soft-disabled with a documented reason.

---

## 12. Rollout Note

This design supersedes only the plugin-side rendering path of the earlier 2026-05-20 annotation-layer design. The Python-side architecture, database boundary, and cache contract remain in force.
