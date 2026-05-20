# PaperForge Plugin Lightweighting And Annotation Positioning

## Status

Proposed

## Goal

Clarify two decisions before more feature work:

1. How to keep the Obsidian plugin fast while preserving current behavior
2. Whether PaperForge annotations should stay local-first or be designed as a true Zotero annotation frontend

This document is intentionally conservative. The primary constraint is: new work must not make Obsidian feel slower.

## Non-Negotiables

1. Existing working PDF annotation behavior must not regress
2. Obsidian must not gain noticeable startup lag, scroll lag, or PDF interaction lag
3. Python remains the runtime truth source; the plugin reads snapshots and invokes CLI commands
4. No direct plugin reads from SQLite in steady state
5. Any future Zotero sync-back must not require dangerous local DB mutation during normal use

## Current Positioning

PaperForge should be positioned as:

`Python-backed literature workspace + Obsidian-native lightweight PDF augmentation layer`

It should not currently be positioned as:

- a full Zotero replacement inside Obsidian
- a full custom PDF reader replacing Obsidian's native viewer
- a system that writes directly into Zotero internals as its primary operating mode

This positioning matches the current architecture boundary in `AGENTS.md`:

- Plugin JS reads snapshots and renders UI
- Python CLI owns canonical runtime operations
- SQLite is a Python concern, not a plugin concern

## What Is Heavy Today

### 1. `paperforge/plugin/main.js` is a monolith

The plugin entry file now mixes:

- dashboard rendering
- setup wizard
- runtime health
- OCR polling
- subprocess orchestration
- PDF overlay internals
- annotation create/delete/edit

This is risky not because large files are aesthetically bad, but because it makes performance isolation difficult. A dashboard tweak can affect PDF code paths and vice versa.

### 2. Global PDF observation is broader than necessary

Current PDF activation uses `setupPdfObserver()` with a `MutationObserver` on `document.body` and then discovers PDF leaves dynamically.

This works, but it is broader than ideal. Even with filtering, body-level observation is an expensive foundation for a feature that should only exist while a PDF leaf is active.

Relevant code:

- `paperforge/plugin/main.js:564` `setupPdfObserver()`
- `paperforge/plugin/main.js:608` `injectPdfEventHooks()`

### 3. PDF annotation refresh is still too coarse

The overlay path already improved significantly by switching from DOM-only fallback to PDF.js handle/event-based rendering. However, these are still heavier than ideal:

- `_rebuildVisibleLayers()` loops through all `pagesCount`
- `scalechanged` triggers a broader rebuild than needed
- `fetchAnnotationsForPaper()` invalidation is paper-wide, not page-local

Relevant code:

- `paperforge/plugin/main.js:658` `_subscribePdfEvents()`
- `paperforge/plugin/main.js:724` `_rebuildVisibleLayers()`

### 4. Dashboard data paths are synchronous and occasionally expensive

The dashboard uses a mix of:

- subprocess calls: `paperforge dashboard --json`, `paperforge status --json`
- full-file `readFileSync()` + `JSON.parse()` on library index files

This is acceptable for an explicit dashboard view, but it should stay scoped to the dashboard and never leak into PDF interaction paths.

Relevant code:

- `paperforge/plugin/main.js:1990` `_fetchStats()`
- `paperforge/plugin/main.js:2028` `_fallbackFetchStats()`

### 5. Polling exists in multiple places

There is periodic polling for:

- export/OCR file changes
- some dashboard refresh paths

Polling is not automatically wrong, but it is easy for these loops to accumulate hidden overhead over time.

Relevant code:

- `paperforge/plugin/main.js:3342`
- `paperforge/plugin/main.js:5665`

## Lightweighting Strategy

### A. Startup should stay dumb

At startup, the plugin should only do these things eagerly:

- register views
- register commands
- register settings tab
- initialize minimal in-memory state

Everything else should be deferred until one of these user actions happens:

- open dashboard
- open PDF
- trigger sync/OCR/manual command

This means no eager annotation cache parsing, no eager dashboard subprocess calls, and no heavy PDF work until a PDF leaf is actually opened.

### B. PDF work should be current-leaf scoped

The ideal PDF runtime model is:

- one active PDF context
- one resolved PDF.js handle per active viewer
- one page-local overlay layer per visible page
- one short-lived cache per visible page

Avoid:

- global body-level discovery once a direct leaf hook becomes practical
- whole-document rebuilds after local edits
- cross-leaf shared mutable PDF state beyond a minimal active-context pointer

### C. Annotation rendering should be page-local and incremental

Target behavior:

- create: append one annotation's rects only
- delete: remove all DOM rects for one annotation id only
- patch: update one annotation's DOM only
- page render: render that page only
- zoom: rerender only mounted/visible pages

Avoid:

- clearing all overlay layers for a paper on small local changes
- looping all pages when only one visible page changed

### D. Annotation selection/create should cache only what is needed

The correct create path is now:

- DOM range -> text item offsets
- PDF.js `getTextContent({ includeChars: true })`
- per-character PDF rects
- line-level merged rects

This is architecturally correct, but must be lightweighted further:

- cache `textContent(includeChars:true)` per current page only
- invalidate that cache on page rerender / zoom / leaf change
- never compute chars for unopened pages

### E. Dashboard should remain opt-in, not ambient

A future PDF-specific dashboard/panel is viable only if it is:

- opened explicitly
- scoped to the current PDF
- backed by current-paper snapshots
- not wired into PDF viewer repaint paths

This panel should not own the viewer. It should complement it.

## Innovative But Safe Solutions Worth Adopting

These ideas are worth using because they improve UX without violating current constraints.

### 1. Zotero-style dual mode toolbar

From Zotero's documented behavior:

- unlocked mode: text selection shows a color chooser popup
- locked mode: user preselects highlight/underline + color, then every selection creates immediately

This is a strong fit because it is lightweight UI with high workflow value.

### 2. PDF++ philosophy: augment, do not replace

PDF++'s best lesson is not its feature set, but its product strategy:

- stay on top of Obsidian's native PDF viewer
- add narrowly scoped capabilities
- prefer local contextual UI over large replacement surfaces

PaperForge should copy that philosophy, not PDF++'s full breadth.

### 3. Current-PDF contextual panel instead of global dashboard clone

Rather than cloning Zotero's full sidebar, a safer and lighter design is:

- current PDF metadata
- annotations list for current paper only
- filter by page/color/type
- jump to page
- append annotation to note
- show OCR/fulltext state

This gives the user most of what they need while keeping scope tight.

## Annotation Sync-Back Decision

### Option A: No sync-back, local-first annotations only

Pros:

- simplest
- safest
- fully consistent with current architecture
- no Zotero sync/version semantics

Cons:

- PaperForge annotations and Zotero annotations diverge
- user ends up with two annotation systems

### Option B: Direct SQLite write-back to Zotero

Pros:

- can appear simple locally
- no separate network step

Cons:

- writes into Zotero internals outside supported API boundaries
- high breakage risk across Zotero updates
- local DB lock/consistency hazards
- conflict/version semantics become PaperForge's burden
- violates the current project boundary philosophy

Decision:

**Reject for normal product direction.**

Direct SQLite write-back is acceptable only as a one-off local experiment, not as the main PaperForge strategy.

### Option C: Zotero Web API sync-back

Pros:

- aligns with Zotero's supported sync model
- compatible with future multi-device and group semantics
- preserves local-first create path while allowing deliberate upstream sync

Cons:

- materially more complex
- requires queueing, conflict handling, retry logic, and mapping local annotations to remote Zotero annotation items

Decision:

**Keep as the only serious future sync-back route, but do not prioritize now.**

## Recommended Product Positioning

### Current phase

PaperForge annotations should be treated as:

`PaperForge-local PDF working annotations with Zotero import compatibility`

Meaning:

- importing Zotero annotations is core
- rendering/import/delete/create/edit locally is core
- note/dashboard integration is core
- Zotero sync-back is explicitly deferred

### Future phase trigger

Only start Zotero Web API sync-back work when all of the following are true:

1. current local annotation UX is stable
2. visible-page rendering is lightweight
3. delete/create/edit flows are reliable
4. the user still wants one unified annotation source instead of local-first augmentation

## Recommended Next Phases

### Phase 1: Lightweight existing annotation runtime

Do not add net-new surface area yet. Optimize current behavior.

Target changes:

- replace whole-document rebuilds with visible-page rebuilds
- add page-local `includeChars` cache
- make create/delete/patch DOM updates annotation-local
- reduce global observers
- remove remaining debug logging

### Phase 2: Lightweight annotation toolbar

Minimal scope only:

- highlight
- underline
- note
- color picker
- locked/unlocked state

No complex floating inspector, no extra panel coupling.

### Phase 3: Current-PDF annotation panel

Only for the currently opened PDF:

- annotation list
- page jump
- filters
- comment/tags
- append to note
- OCR/fulltext presence

### Phase 4: Re-evaluate Zotero sync-back

At this stage, choose deliberately:

- stay local-first forever
- or implement Web API queue-based sync-back

## Success Criteria

The plugin is considered acceptably lightweight when:

1. Opening a PDF does not trigger noticeable global UI lag
2. Scrolling a large PDF does not cause whole-document overlay rebuilds
3. Create/delete/edit feel immediate on the active page
4. Opening the dashboard is heavier than opening a PDF, but only because it is explicitly requested
5. No background polling or observer path is doing meaningful work when the relevant feature is not in use

## Final Recommendation

1. Keep PaperForge positioned as a lightweight augmentation layer, not a Zotero replacement
2. Optimize current annotation runtime before adding more annotation UI
3. Reject SQLite write-back as a product direction
4. Preserve Web API sync-back as the only credible future unification route
5. Build any future PDF dashboard as a current-PDF contextual panel, not a full reader/sidebar clone
