# PaperForge PDF Annotation Layer PDF.js Internal Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current DOM-only PDF annotation overlay with a PDF.js-internal, viewport-aligned overlay implementation that renders imported Zotero annotations visibly and correctly inside Obsidian's native PDF viewer.

**Architecture:** Keep the proven Python import/cache pipeline unchanged. Rewrite the plugin-side overlay path so that it discovers PDF.js page internals, mounts one overlay per `pageView.div`, aligns each layer with `window.pdfjsLib.setLayerDimensions(...)`, and repaints through page render events instead of generic DOM mutation retries.

**Tech Stack:** Python 3.10+, SQLite cache, Obsidian plugin CommonJS (`main.js`), PDF.js runtime internals, optional `monkey-around`, Vitest, pytest

---

## File Map

### Python Files

- Modify: `paperforge/annotation/cache.py` — keep cache contract stable; preserve optional page size metadata but do not expand scope further unless strictly needed for plugin fallback

### Plugin Runtime Files

- Modify: `paperforge/plugin/main.js` — replace DOM-only overlay flow with PDF.js internal route
- Modify: `paperforge/plugin/src/testable.js` — add pure helpers for viewport math and internal guard logic
- Modify: `paperforge/plugin/styles.css` — simplify overlay visuals after alignment is fixed; keep only necessary visible-state styles

### Tests

- Modify: `paperforge/plugin/tests/runtime.test.mjs` — internal guard logic, viewport percentage helpers, page grouping helpers
- Modify: `paperforge/plugin/tests/commands.test.mjs` — only if annotation command bridge arguments change
- Modify: `paperforge/plugin/tests/errors.test.mjs` — soft-disable behavior when PDF internals unavailable

### Reference Inputs

- Read: `docs/superpowers/specs/2026-05-20-pdf-annotation-layer-pdfjs-internal-design.md`
- Read: `patch-plan/plugin-overlay-adapter.md`
- Read: `reports/04-obsidian-pdf-overlay-feasibility.md`

---

## Task 1: Freeze and Test the Current Data Contract

**Files:**
- Modify: `paperforge/plugin/tests/runtime.test.mjs`
- Reference: `paperforge/annotation/cache.py`

- [ ] **Step 1: Write failing tests for the plugin-side annotation cache assumptions**

Cover:

- annotation objects use full field names (`type`, `position`, `page_index`, `zotero_attachment_key`)
- viewport renderer can consume imported Zotero-style `position.rects`
- cache grouping by `page_index` stays zero-based

- [ ] **Step 2: Run the focused plugin runtime tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: FAIL for the new assertions.

- [ ] **Step 3: Implement the minimal testable helpers needed by the new renderer**

Add pure helpers in `src/testable.js` for:

- `getAnnotationPosition(ann)`
- `getAnnotationRectsFromPosition(position)`
- `normalizePdfRectToViewportPercent(rect, viewBox)`
- `groupAnnotationsByPageIndex(annotations)`

- [ ] **Step 4: Re-run the focused plugin runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/testable.js paperforge/plugin/tests/runtime.test.mjs
git commit -m "test: lock annotation cache and viewport helper contracts"
```

---

## Task 2: Add Internal PDF.js Discovery Guards

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/src/testable.js`
- Modify: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Write failing tests for internal availability checks**

Cover:

- `window.pdfjsLib.setLayerDimensions` detection
- internal PDF view shape guard
- graceful disablement when page internals are missing

- [ ] **Step 2: Run the focused error/runtime tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

Expected: FAIL for the new internal guard assertions.

- [ ] **Step 3: Implement minimal runtime guards**

Add helpers for:

- `hasPdfJsLayerAlignment(windowObj)`
- `resolvePdfInternalHandle(view)`
- `canRenderPdfInternalOverlay(handle)`

In `main.js`, emit one concise disablement log instead of continuing with broken rendering.

- [ ] **Step 4: Re-run the focused tests**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/src/testable.js paperforge/plugin/tests/errors.test.mjs paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: add PDF.js internal overlay guards"
```

---

## Task 3: Replace MutationObserver Rendering with PDF Viewer Event Hooks

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/tests/runtime.test.mjs`

- [ ] **Step 1: Write failing tests for page-render event wiring decisions**

Cover:

- first file load fetches annotations once
- page repaint requests are page-scoped
- generic subtree mutation is no longer the primary repaint driver

- [ ] **Step 2: Run the focused runtime tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: FAIL for the new page event wiring assertions.

- [ ] **Step 3: Implement minimal event-driven lifecycle**

In `main.js`:

- patch the native PDF view load path to capture the internal viewer handle
- subscribe to whichever of these are available from the runtime shape:
  - `pagerendered`
  - `textlayerrendered`
  - `annotationlayerrendered`
  - `scalechanged`
- keep MutationObserver only as a narrowly scoped fallback if an event path is unavailable

- [ ] **Step 4: Re-run the focused runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: drive overlay repaint from PDF viewer events"
```

---

## Task 4: Add PageView-Aligned Layer Management

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/tests/runtime.test.mjs`

- [ ] **Step 1: Write failing tests for page layer creation/alignment helpers**

Cover:

- one layer per page
- layer mounted on `pageView.div`
- `setLayerDimensions(layer, viewport)` called when available
- page clear only removes PaperForge-owned rects

- [ ] **Step 2: Run the focused runtime tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: FAIL for the new layer-management assertions.

- [ ] **Step 3: Implement minimal layer manager behavior**

In `main.js` add logic equivalent to:

- `getOrCreateOverlayLayer(pageView)`
- `alignOverlayLayer(layer, pageView.viewport)`
- `clearOverlayPage(pageNumber)`

Simplify CSS so the layer behaves like a PDF++-style aligned layer instead of a guessed absolute box.

- [ ] **Step 4: Re-run the focused runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: align overlay layers to PDF.js page viewports"
```

---

## Task 5: Rewrite Rect Rendering to Use Viewport ViewBox

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/src/testable.js`
- Modify: `paperforge/plugin/tests/runtime.test.mjs`

- [ ] **Step 1: Write failing tests for viewport-based rect normalization**

Cover:

- input rect format is `[left, bottom, right, top]`
- Y mirroring uses viewport/viewBox coordinates
- output percentages are derived from `viewBox`, not guessed page sizes

- [ ] **Step 2: Run the focused runtime tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: FAIL for the new normalization assertions.

- [ ] **Step 3: Implement minimal viewport-based renderer**

In `main.js`:

- stop using hardcoded letter/A4 fallback as the primary mapping path
- normalize each rect against `pageView.viewport.viewBox`
- preserve readonly state, popover hooks, and local action metadata

In `src/testable.js`, expose the pure geometry transform for tests.

- [ ] **Step 4: Re-run the focused runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/src/testable.js paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: render annotation rects from PDF.js viewport coordinates"
```

---

## Task 6: Reconnect Popovers and Local Actions on the New Layer

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Write failing tests for local interaction behavior on aligned layers**

Cover:

- click target still opens popover
- readonly imported annotations stay readonly
- local annotations still expose delete/edit path

- [ ] **Step 2: Run the focused tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

Expected: FAIL for the new interaction assertions.

- [ ] **Step 3: Implement the minimal interaction reconnect**

Ensure the new viewport-aligned layer still attaches:

- click handlers
- hover handlers
- popover placement
- local delete/edit actions

- [ ] **Step 4: Re-run the focused tests**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css paperforge/plugin/tests/errors.test.mjs paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: reconnect popovers and local actions on aligned overlay layers"
```

---

## Task 7: Preserve or Soft-Disable Selection-to-Create

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/tests/runtime.test.mjs`

- [ ] **Step 1: Write failing tests for selection create behavior under the new lifecycle**

Cover one of two explicitly acceptable outcomes:

- selection-create still works after text layer readiness, or
- selection-create is soft-disabled behind a clear console/user message pending follow-up

- [ ] **Step 2: Run the focused runtime tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: FAIL for the new selection-path assertions.

- [ ] **Step 3: Implement the minimal supported outcome**

Preferred:

- bind selection-create only after page text-layer readiness on the internal page route

Fallback if runtime shape prevents safe support in this phase:

- disable selection-create temporarily with a documented message and follow-up note in the spec/plan

- [ ] **Step 4: Re-run the focused runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: stabilize selection create for internal PDF overlay route"
```

---

## Task 8: Clean Up Temporary Debug Instrumentation

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Write failing tests for production logging expectations**

Cover:

- plugin keeps concise lifecycle logs only
- no `visual-probe`, `hitTest`, `pageBox`, `layerBox`, `rectBox` debug spam in the stable path

- [ ] **Step 2: Run the focused tests to verify failure**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

Expected: FAIL because the temporary debugging code is still present.

- [ ] **Step 3: Remove or gate temporary diagnostics**

Keep only concise logs such as:

- overlay enabled/disabled
- annotation count fetched
- one clear internal-shape failure message when applicable

- [ ] **Step 4: Re-run the focused tests**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css paperforge/plugin/tests/errors.test.mjs paperforge/plugin/tests/runtime.test.mjs
git commit -m "chore: remove temporary PDF overlay debug instrumentation"
```

---

## Task 9: Real-World Verification on a Zotero-Backed PDF

**Files:**
- Modify only if verification reveals real defects

- [ ] **Step 1: Run Python and plugin automated test slices**

Run:

```bash
python -m pytest tests/unit/ tests/cli/ -v --tb=short
cd paperforge/plugin && npx vitest run
```

Expected: PASS.

- [ ] **Step 2: Verify against the real Literature-hub vault PDF**

Use the existing real paper already exercised during debugging:

- vault PDF path under `System/Zotero/storage/5AWBHQ59/...pdf`
- expected paper id `9ILH6L6W`

Confirm:

- imported Zotero highlights are visible on the correct lines
- zoom preserves alignment
- scrolling to later annotated pages preserves alignment
- popover opens on click

- [ ] **Step 3: If verification fails, fix only the discovered root cause and re-run Step 1 and Step 2**

- [ ] **Step 4: Commit final verification-backed fixes**

```bash
git add paperforge/plugin/main.js paperforge/plugin/src/testable.js paperforge/plugin/styles.css paperforge/plugin/tests/runtime.test.mjs paperforge/plugin/tests/errors.test.mjs paperforge/annotation/cache.py
git commit -m "fix: finalize PDF.js internal annotation overlay route"
```

---

## Completion Criteria

Do not consider this plan complete until all of the following are true:

- the plugin no longer relies on generic page DOM geometry as its primary placement method
- layer alignment uses PDF.js viewer internals or a clearly documented fallback path
- a real imported Zotero annotation is visibly aligned on the target PDF inside Obsidian
- broad debug instrumentation has been removed from the normal path
- automated test slices pass
