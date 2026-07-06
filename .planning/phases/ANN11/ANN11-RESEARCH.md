# Phase ANN11: Annotation Card View-Models and Layout - Research

**Researched:** 2026-07-05
**Domain:** Obsidian plugin annotation card view-models, deterministic side-lane layout, and read-only DOM rendering
**Confidence:** MEDIUM-HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Card Information Density
- **D-01:** Annotation cards should always show the selected text preview, comment preview, page, color/type, source/provenance line, and read-only status.
- **D-02:** The card should feel compact enough to sit beside a central reading surface, but it must not hide the core evidence fields needed to recognize the annotation.
- **D-03:** Phase ANN11 should not add expandable details, drawers, popovers, editable forms, or local card mutation flows. A later phase may add richer interaction after card/source navigation exists.
- **D-04:** Missing selected text or missing comment values should render as explicit, quiet placeholders rather than disappearing or collapsing the card.

### Deterministic Side-Lane Placement
- **D-05:** Cards are sorted by stable reading/source order before lane assignment.
- **D-06:** Within the same page or source group, original source/order metadata should be preserved when available; otherwise the implementation may fall back to stable normalized annotation identity/order.
- **D-07:** Lane assignment should alternate cards between left and right lanes after sorting, producing a balanced reference-UI-like reading canvas without storing layout state.
- **D-08:** Phase ANN11 must not introduce draggable cards, random layout, user-persisted lane choices, localStorage/settings persistence, or Obsidian `.canvas` persistence.
- **D-09:** The planner may choose exact tie-breakers, but the result must be deterministic for the same annotation input.

### Explicit Canvas States
- **D-10:** The canvas shell keeps a central status/surface area while side lanes render card content only when annotation data is loaded and usable.
- **D-11:** Loaded, empty, missing paper, missing annotation database, missing source, command failure, refresh, and stale-result states must be explicit view-model states.
- **D-12:** Error and stale states should never masquerade as an empty annotation list.
- **D-13:** During refresh, existing cards may remain visible only if clearly marked as refreshing/stale-safe; otherwise the renderer should show a clear refreshing state.
- **D-14:** Missing source or unsupported future anchoring should preserve card visibility when annotation metadata is otherwise valid, but the card must expose source/provenance limitations for later phases.

### Long Text, CJK, and Layout Resilience
- **D-15:** Selected text and comment previews should use bounded line counts, safe wrapping, and maximum card height so long content cannot stretch lanes or resize the canvas unexpectedly.
- **D-16:** CJK-heavy content must wrap naturally and avoid overlap, clipped controls, negative spacing tricks, or viewport-scaled font behavior.
- **D-17:** Cards should use stable dimensions and CSS constraints that keep hover/focus/read-only/status elements from shifting the lane layout.
- **D-18:** Phase ANN11 should test long selected text, long comments, missing values, and CJK-heavy values at the view-model and DOM level.

### Read-Only and Provenance Signals
- **D-19:** Cards must visibly communicate read-only status in a restrained way, such as a small badge or metadata chip.
- **D-20:** Cards should preserve source, attachment/provenance, page, type, and color metadata needed by later evidence workflows.
- **D-21:** Card interactions may support selection/focus styling as a future navigation affordance, but Phase ANN11 must not expose create, edit, delete, save, import, apply, or write-back controls.
- **D-22:** Tests should assert forbidden controls/verbs are absent from card rendering and interactions, mirroring the v0.2 annotation list safety gate.

### the agent's Discretion
The user approved the recommended choices for card density, lane placement, state handling, long/CJK text behavior, and read-only/provenance signaling. The planner may choose exact function names, CSS class names, DOM structure, placeholder copy, tie-breaker order, and focused test filenames as long as the decisions above are preserved.

### the agent's Discretion
The user approved the recommended choices for card density, lane placement, state handling, long/CJK text behavior, and read-only/provenance signaling. The planner may choose exact function names, CSS class names, DOM structure, placeholder copy, tie-breaker order, and focused test filenames as long as the decisions above are preserved.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Source anchors belong to Annotation Phase ANN12.
- Bidirectional card/source navigation belongs to Annotation Phase ANN13.
- Connector lines and final visual polish belong to Annotation Phase ANN14.
- Final canvas verification and live harness record belong to Annotation Phase ANN15.
- Expandable details, draggable/freeform card layout, persistent lane choices, local annotation editing, Zotero write-back, AI-generated cards, multi-paper boards, and Obsidian `.canvas` persistence remain future scope.
</user_constraints>

## Summary

ANN11 should add a canvas-specific card projection over the existing normalized v0.2 annotation state, then assign those cards to deterministic left/right lanes by reusing the existing reading-order sort before alternating lane placement. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] [VERIFIED: paperforge/plugin/src/testable.js] The phase should not introduce a new annotation loader, direct SQLite/Zotero reads, Python subprocess commands, edit controls, persistent layout, source anchors, navigation, or connectors. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: .planning/research/PITFALLS.md]

The natural implementation seam is `paperforge/plugin/src/canvas/view-model.js` for explicit canvas/card states and `paperforge/plugin/src/canvas/layout.js` for deterministic lane assignment. [VERIFIED: .planning/research/ARCHITECTURE.md] Current ANN10 code already has `context.js`, `annotations.js`, `controller.js`, `render.js`, and `index.js`; `view-model.js` and `layout.js` are still absent. [VERIFIED: codebase grep] The current `main.js` does not yet expose the planned Reading Canvas runtime view/command, so ANN11 planning should include a dependency checkpoint that ANN10 Plan 02 is complete before DOM integration tasks start. [VERIFIED: codebase grep] [VERIFIED: .planning/phases/ANN10/ANN10-02-PLAN.md]

**Primary recommendation:** Split ANN11 into two plans: pure card view-model/layout contracts first, then DOM/CSS/render integration after confirming ANN10 runtime canvas wiring is present. [VERIFIED: codebase grep] [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Annotation card model projection | Browser / Client | API / Backend | Plugin JS consumes normalized v0.2 annotation states already returned by the CLI bridge; ANN11 should only project display fields. [VERIFIED: paperforge/plugin/src/testable.js] |
| Explicit canvas/card states | Browser / Client | API / Backend | State names originate from v0.2 loader results, but canvas state rendering and stale/refresh presentation live in plugin JS. [VERIFIED: paperforge/plugin/src/testable.js] [VERIFIED: paperforge/plugin/src/canvas/render.js] |
| Deterministic lane assignment | Browser / Client | - | Lane placement is a pure view/layout concern and must not persist layout state. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] |
| Long/CJK card layout | Browser / Client | - | Wrapping, line clamps, card dimensions, and DOM class hooks belong to plugin CSS/jsdom tests. [VERIFIED: paperforge/plugin/styles.css] [VERIFIED: paperforge/plugin/tests/annotation-section-dom.test.mjs] |
| Read-only/provenance safety | Browser / Client | API / Backend | Existing normalized rows carry provenance/read-only fields; ANN11 must display them and forbid mutating controls in DOM. [VERIFIED: paperforge/plugin/src/testable.js] [VERIFIED: paperforge/plugin/tests/annotation-main-runtime.test.mjs] |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CANVAS-03 | The canvas presents a central PaperForge-owned reading surface with left/right annotation card lanes. | Use ANN10 shell render as the central placeholder/status area and add left/right lane DOM only for usable loaded card states. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: paperforge/plugin/src/canvas/render.js] |
| CANVAS-04 | The canvas handles missing paper identity, missing annotation database, empty annotations, missing source content, unsupported anchoring, stale loads, and command failures without crashing. | Preserve ANN10 shell states and add card-state projection for ready/empty/missing-source/refresh/stale/error without collapsing error states into empty. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs] |
| CARD-01 | Cards display selected text, comment, page, color/type, source, attachment/provenance, and read-only status. | Build cards from normalized `display`, `provenance`, and `pdfLocation` sections. [VERIFIED: paperforge/plugin/src/testable.js] |
| CARD-02 | Cards handle long, missing, or CJK-heavy selected text/comment content without broken layout or overlapping controls. | Reuse preview/truncation lessons and DOM/CSS class-hook tests from annotation list; add CJK-specific card tests. [VERIFIED: paperforge/plugin/src/testable.js] [VERIFIED: paperforge/plugin/tests/annotation-section-dom.test.mjs] |
| CARD-03 | Cards use deterministic reading-order placement into left/right lanes. | Use `sortAnnotationsForReadingOrder()` or mirror its page/sortIndex/identity algorithm, then alternate by sorted index. [VERIFIED: paperforge/plugin/src/testable.js] |
| CARD-04 | Card models preserve enough source identity for later evidence workflows without exposing edit/write-back controls. | Include source, sourceAttachmentKey, sourceAnnotationKey, row id, page index/label, sync/read-only state, and anchor placeholder status; assert forbidden verbs absent. [VERIFIED: paperforge/plugin/src/testable.js] [VERIFIED: paperforge/plugin/tests/annotation-main-runtime.test.mjs] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- PaperForge uses a contract-driven architecture where plugin consumers should respect existing PFResult-style contracts and avoid circular dependency expansion. [VERIFIED: AGENTS.md]
- Plugin UI text should use `paperforge/plugin/i18n.js` when adding translatable runtime UI strings; new strings should be added to both `zh` and `en` when applicable. [VERIFIED: AGENTS.md]
- Development should keep the Obsidian plugin as a thin shell over CLI/canonical state and avoid duplicating worker/business logic in JS UI. [VERIFIED: .planning/PROJECT.md] [VERIFIED: AGENTS.md]
- Existing pre-commit guidance includes lint/format for Python and unit tests, but ANN11 itself is a JS plugin phase and should use focused plugin Vitest gates plus `node --check main.js`. [VERIFIED: AGENTS.md] [VERIFIED: paperforge/plugin/package.json]
- API keys/secrets must not be committed; ANN11 should not touch `.env` or credential surfaces. [VERIFIED: AGENTS.md]

## Standard Stack

### Core

| Library / Runtime | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| Obsidian plugin CommonJS runtime | `obsidian` dev dependency `^1.12.0` | Runtime ItemView/plugin API surface | Existing plugin stack and tests already target this dependency. [VERIFIED: paperforge/plugin/package.json] |
| Plain JavaScript CommonJS modules | package `"type": "commonjs"` | Canvas helper modules under `src/canvas/*` | Existing plugin package and ANN10 canvas modules use CommonJS. [VERIFIED: paperforge/plugin/package.json] [VERIFIED: paperforge/plugin/src/canvas/index.js] |
| Plain DOM/CSS | existing `main.js` + `styles.css` | Render card lanes, cards, badges, and state text | Existing annotation UI and ANN10 canvas render use DOM helpers and textContent, not a UI framework. [VERIFIED: paperforge/plugin/src/canvas/render.js] |

### Supporting

| Library / Runtime | Version | Purpose | When to Use |
|-------------------|---------|---------|-------------|
| Vitest | `^2.1.0` | Pure helper and DOM tests | Add `canvas-viewmodel.test.mjs`, `canvas-layout.test.mjs`, and card DOM tests. [VERIFIED: paperforge/plugin/package.json] |
| jsdom | `^25.0.0` | DOM rendering tests | Assert class hooks, safe text insertion, forbidden controls, CJK/long text DOM structure. [VERIFIED: paperforge/plugin/package.json] |
| `obsidian-test-mocks` | `^2.0.0` | Obsidian runtime test harness | Use only when testing `main.js` / ItemView integration after ANN10 runtime wiring exists. [VERIFIED: paperforge/plugin/package.json] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain DOM/CSS | React/Svelte/Vue | Out of scope because the roadmap forbids a new frontend framework/build system for MVP. [VERIFIED: .planning/REQUIREMENTS.md] |
| Deterministic alternating lanes | D3/Cytoscape/physics layout | Out of scope because ANN11 needs stable side lanes, not a graph/physics layout. [VERIFIED: .planning/REQUIREMENTS.md] |
| Session-local deterministic layout | localStorage/plugin settings/`.canvas` persistence | Forbidden by ANN11 decisions and SAFE scope. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] |

**Installation:**

No new package installation is recommended for ANN11. [VERIFIED: paperforge/plugin/package.json]

## Package Legitimacy Audit

No external packages are recommended or installed in this phase. [VERIFIED: .planning/REQUIREMENTS.md] Existing dev packages are already present in `paperforge/plugin/package.json`; no package-legitimacy gate is required for a no-install phase. [VERIFIED: paperforge/plugin/package.json]

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
Existing v0.2 annotation loader/state
  -> src/canvas/annotations.js wrapper
  -> src/canvas/controller.js fixed-paper session
  -> ANN11 src/canvas/view-model.js
       - maps shell states
       - builds read-only card models
       - preserves provenance/source identity
  -> ANN11 src/canvas/layout.js
       - reading-order sort
       - left/right alternation
  -> src/canvas/render.js extensions
       - central status/surface area
       - left/right card lanes
       - safe text-only card DOM
  -> paperforge/plugin/styles.css namespaced card/lane constraints
```

### Recommended Project Structure

```text
paperforge/plugin/src/canvas/
├── context.js        # ANN10 explicit paper context
├── annotations.js    # ANN10 wrapper around v0.2 annotation loader
├── controller.js     # ANN10 fixed-paper load/refresh/teardown lifecycle
├── render.js         # ANN10 shell states; ANN11 should extend for lanes/cards
├── view-model.js     # ANN11 card/state projection
├── layout.js         # ANN11 deterministic lane assignment
└── index.js          # Export narrow public helper surface

paperforge/plugin/tests/
├── canvas-viewmodel.test.mjs
├── canvas-layout.test.mjs
├── canvas-render.test.mjs
├── canvas-card-dom.test.mjs or canvas-section-dom.test.mjs
└── existing annotation focused tests
```

### Pattern 1: Canvas Card View-Model Over Normalized Rows

**What:** Convert each normalized row into a card object with display, provenance, source identity, read-only marker, and future anchor placeholder fields. [VERIFIED: paperforge/plugin/src/testable.js]

**When to use:** Only when annotation state is `ready` and rows are usable; non-ready states should produce explicit canvas state models, not empty card arrays with hidden error semantics. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]

**Example:**

```javascript
// Source: paperforge/plugin/src/testable.js normalized row shape.
function buildCanvasCard(row) {
  var display = row.display || {};
  var provenance = row.provenance || {};
  var loc = row.pdfLocation || {};
  return {
    id: getAnnotationIdentity(row),
    selectedText: display.selectedText || '',
    comment: display.comment || '',
    pageLabel: display.pageLabel || '',
    pageIndex: loc.pageIndex != null ? loc.pageIndex : null,
    type: display.type || 'annotation',
    color: display.color || null,
    source: provenance.source || 'unknown',
    sourceAttachmentKey: provenance.sourceAttachmentKey || '',
    sourceAnnotationKey: provenance.sourceAnnotationKey || '',
    readOnly: provenance.isReadonly !== false,
    anchor: { status: 'unresolved', reason: 'Source anchors are implemented in ANN12.' }
  };
}
```

### Pattern 2: Reading-Order Then Alternating Lanes

**What:** Sort rows using the existing reading-order rules, then assign even sorted indexes to `left` and odd sorted indexes to `right`. [VERIFIED: paperforge/plugin/src/testable.js] [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]

**When to use:** All loaded card arrays in ANN11; do not use random, persisted, draggable, or viewport-dependent placement. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]

**Example:**

```javascript
// Source: paperforge/plugin/src/testable.js sortAnnotationsForReadingOrder().
function assignCardsToLanes(cardsOrRows) {
  var sorted = sortAnnotationsForReadingOrder(cardsOrRows);
  var lanes = { left: [], right: [] };
  sorted.forEach(function (row, index) {
    var card = buildCanvasCard(row);
    card.lane = index % 2 === 0 ? 'left' : 'right';
    lanes[card.lane].push(card);
  });
  return lanes;
}
```

### Pattern 3: DOM Renderer Extends Shell, Not Loader

**What:** Extend `renderCanvasView()` or add `renderCanvasCards()` so DOM receives an already-built view-model and only renders safe elements. [VERIFIED: paperforge/plugin/src/canvas/render.js]

**When to use:** In DOM integration plan after pure `view-model.js` and `layout.js` tests pass. [VERIFIED: .planning/phases/ANN10/ANN10-01-PLAN.md]

### Anti-Patterns to Avoid

- **Re-querying annotations from card modules:** Cards must consume the controller's single annotation state snapshot, not call CLI/db/Zotero. [VERIFIED: .planning/research/PITFALLS.md]
- **Using list rows directly as DOM cards:** Build a canvas-specific card model so later anchors/navigation/connectors have stable identity fields. [VERIFIED: .planning/research/ARCHITECTURE.md]
- **Treating stale/error states as empty lanes:** Empty means no annotations; stale/error means data confidence changed and must be visible. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]
- **Adding card edit affordances:** `edit`, `delete`, `create`, `save`, `import`, `apply`, `write-back`, `evidence`, and `concept-card` controls are forbidden in ANN11. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] [VERIFIED: paperforge/plugin/tests/annotation-main-runtime.test.mjs]
- **Adding connectors or anchors now:** ANN12 owns source anchors and ANN14 owns connectors. [VERIFIED: .planning/ROADMAP.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Annotation loading | New SQL/Zotero/CLI loader | Existing v0.2 loader via `src/canvas/annotations.js` | Prevents source-of-truth drift and preserves missing DB/CLI error states. [VERIFIED: paperforge/plugin/src/canvas/annotations.js] |
| Reading-order sort | New comparator with different tie-breakers | Existing `sortAnnotationsForReadingOrder()` algorithm | It already sorts page, sortIndex, then stable identity without mutating input. [VERIFIED: paperforge/plugin/src/testable.js] |
| Stable card identity | Array index or random ids | `getAnnotationIdentity()` | Existing identity uses source annotation key, row id, or deterministic fallback. [VERIFIED: paperforge/plugin/src/testable.js] |
| Text preview truncation | DOM measurement-dependent truncation | Existing preview limits plus CSS line clamps | Existing tests cover preview metadata and DOM class hooks. [VERIFIED: paperforge/plugin/src/testable.js] [VERIFIED: paperforge/plugin/tests/annotation-section-dom.test.mjs] |
| PDF/source resolution | New attachment matching | `resolveAnnotationPdfTarget()` later in ANN13 | Existing resolver handles multi-PDF fail-closed behavior. [VERIFIED: paperforge/plugin/src/testable.js] |

**Key insight:** ANN11 is a projection/layout phase; every backend-ish concern already has a local contract and should remain outside card/lane modules. [VERIFIED: .planning/research/SUMMARY.md]

## Common Pitfalls

### Pitfall 1: Duplicating the v0.2 Annotation Runtime

**What goes wrong:** Card modules call new CLI commands or parse raw export rows instead of consuming normalized rows. [VERIFIED: .planning/research/PITFALLS.md]
**Why it happens:** The canvas feels like a new surface, but its annotation data source is already settled. [VERIFIED: .planning/research/SUMMARY.md]
**How to avoid:** Keep `view-model.js` pure over annotation state and import/reuse existing helper algorithms. [VERIFIED: paperforge/plugin/src/testable.js]
**Warning signs:** `annotations.db`, `sqlite`, `annotation import`, `--apply`, or `runSubprocess` appear under `src/canvas/view-model.js` or `layout.js`. [VERIFIED: .planning/research/PITFALLS.md]

### Pitfall 2: ANN10 Runtime Not Completed Before ANN11 DOM Integration

**What goes wrong:** ANN11 tries to compensate for missing `PaperForgeReadingCanvasView` wiring inside `main.js`, duplicating ANN10 Plan 02. [VERIFIED: codebase grep] [VERIFIED: .planning/phases/ANN10/ANN10-02-PLAN.md]
**Why it happens:** Current tree has canvas pure modules but no `VIEW_TYPE_PAPERFORGE_READING_CANVAS`/runtime view references in `main.js`. [VERIFIED: codebase grep]
**How to avoid:** Make Plan 02 depend on an explicit preflight: ANN10 runtime view/command/button exists, or ANN11 pauses DOM integration and only completes pure helper work. [VERIFIED: codebase grep]
**Warning signs:** ANN11 plan modifies paper panel open commands or view registration beyond narrowly calling existing canvas render hooks. [VERIFIED: .planning/phases/ANN10/ANN10-02-PLAN.md]

### Pitfall 3: Long Text and CJK Break Lane Geometry

**What goes wrong:** Cards expand indefinitely, overlap badges/status rows, or use `word-break: break-all` globally. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]
**Why it happens:** jsdom cannot prove visual wrapping, so CSS hooks and bounded dimensions must be explicit. [VERIFIED: paperforge/plugin/tests/annotation-section-dom.test.mjs]
**How to avoid:** Add max card height, internal preview clamps, `overflow-wrap: anywhere`, `word-break: break-word` or CJK-safe equivalent on preview blocks, and stable lane widths. [VERIFIED: paperforge/plugin/styles.css]
**Warning signs:** Viewport-scaled font sizes, negative spacing, generic `.card` selectors, or no CJK test fixtures. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]

### Pitfall 4: Read-Only Boundary Breach

**What goes wrong:** Cards expose mutation verbs or future evidence/concept controls in ANN11. [VERIFIED: .planning/REQUIREMENTS.md]
**Why it happens:** Card UI invites richer object actions, but v0.3 is read-only. [VERIFIED: .planning/PROJECT.md]
**How to avoid:** Reuse the forbidden-control assertion pattern from annotation DOM/popover tests and run it against the whole canvas root. [VERIFIED: paperforge/plugin/tests/annotation-main-runtime.test.mjs]
**Warning signs:** Buttons or aria labels include edit/delete/create/save/import/apply/write-back/database/evidence/concept. [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs]

### Pitfall 5: Test Output Can Show Startup Error With Exit Code 0

**What goes wrong:** A test command appears successful by exit code while Vitest reports config startup errors. [VERIFIED: command run]
**Why it happens:** In this sandbox, `npm.cmd test -- ...` printed a Vitest startup error involving access to an ancestor directory and config resolution, but the shell tool reported exit code 0. [VERIFIED: command run]
**How to avoid:** Planner verification should require output inspection for `Startup Error`, `failed to load config`, and `FAIL`, not just process exit code. [VERIFIED: command run]
**Warning signs:** Output contains `Cannot read directory`, `Could not resolve ... vitest.config.ts`, or `Startup Error`. [VERIFIED: command run]

## Code Examples

### Required Card Fields From Normalized Rows

```javascript
// Source: paperforge/plugin/src/testable.js normalizeAnnotationExportRow().
const card = {
  id: getAnnotationIdentity(row),
  selectedText: row.display && row.display.selectedText || '',
  comment: row.display && row.display.comment || '',
  pageLabel: row.display && row.display.pageLabel || '',
  pageIndex: row.pdfLocation && row.pdfLocation.pageIndex != null ? row.pdfLocation.pageIndex : null,
  type: row.display && row.display.type || 'annotation',
  color: row.display && row.display.color || null,
  source: row.provenance && row.provenance.source || 'unknown',
  sourceAttachmentKey: row.provenance && row.provenance.sourceAttachmentKey || '',
  sourceAnnotationKey: row.provenance && row.provenance.sourceAnnotationKey || '',
  readOnly: !(row.provenance && row.provenance.isReadonly === false)
};
```

### Explicit Canvas State Mapping

```javascript
// Source: paperforge/plugin/src/canvas/render.js and src/testable.js load states.
const CARD_RENDER_STATES = [
  'loading',
  'ready',
  'empty',
  'missing-paper',
  'missing-db',
  'cli-error',
  'invalid-json',
  'missing-source',
  'unsupported'
];
```

### Forbidden Control Test Helper

```javascript
// Source: paperforge/plugin/tests/canvas-render.test.mjs pattern.
const FORBIDDEN_WORDS = [
  'edit', 'delete', 'create', 'save', 'import', 'apply',
  'write back', 'write-back', 'database', 'evidence', 'concept card'
];

function assertNoForbiddenControls(rootEl) {
  const text = rootEl.textContent.toLowerCase();
  const html = rootEl.innerHTML.toLowerCase();
  for (const word of FORBIDDEN_WORDS) {
    expect(text).not.toContain(word);
    expect(html).not.toContain(word);
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Native PDF overlay/list as primary display | PaperForge-owned Reading Canvas with v0.2 fallback | v0.3 roadmap, 2026-07-03 | Cards/lanes must be additive and must not claim native PDF overlay reliability. [VERIFIED: .planning/ROADMAP.md] |
| Sidebar annotation rows only | Canvas card models preserving provenance and read-only status | ANN11 scope | Card model should be deeper than list row DOM but consume the same normalized source. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] |
| Direct visual connector ambition | Anchors/navigation/connectors deferred | ANN12-ANN14 roadmap | ANN11 should include only anchor placeholder metadata, no connector drawing. [VERIFIED: .planning/ROADMAP.md] |

**Deprecated/outdated:**
- Native Obsidian PDF viewer DOM as v0.3 foundation: explicitly avoided by v0.3 architecture. [VERIFIED: .planning/research/ARCHITECTURE.md]
- Persistent/freeform card layout in ANN11: deferred future scope. [VERIFIED: .planning/REQUIREMENTS.md]
- Any write-back/editing controls in the canvas: out of scope and security-sensitive. [VERIFIED: .planning/REQUIREMENTS.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | None. All actionable recommendations are derived from checked-in project files, source code, tests, or command outputs in this session. | All | No user confirmation needed for assumed technical facts. |

## Open Questions (RESOLVED)

1. **Has ANN10 Plan 02 been fully executed in the active worktree?**
   - What we know: `src/canvas/controller.js` and `render.js` exist, but `main.js` search found no Reading Canvas runtime view/command references. [VERIFIED: codebase grep]
   - What's unclear: Whether runtime wiring is pending, in another branch, or intentionally deferred. [VERIFIED: codebase grep]
   - Resolution: Treat ANN10-02 runtime wiring as a hard dependency for ANN11 DOM/runtime integration. ANN11-01 pure helper work may proceed after ANN10-01, but ANN11-02 must include a pre-flight gate that stops with `CHECKPOINT: ANN10-02 incomplete` before any `main.js` work if the Reading Canvas ItemView/button/runtime delegation is absent. [VERIFIED: .planning/phases/ANN10/ANN10-02-PLAN.md] [VERIFIED: .planning/phases/ANN11/ANN11-02-PLAN.md]

2. **Should card copy be routed through i18n now or kept internal/test-only first?**
   - What we know: AGENTS.md says plugin UI uses `i18n.js` for bilingual UI text. [VERIFIED: AGENTS.md]
   - What's unclear: ANN10 render shell currently uses hard-coded English text in `src/canvas/render.js`. [VERIFIED: paperforge/plugin/src/canvas/render.js]
   - Resolution: ANN11 should add scoped `zh`/`en` `i18n.js` keys for visible card labels, placeholders, provenance/read-only badges, and state copy introduced by card lane rendering. Existing ANN10 shell copy can remain as-is until its own cleanup, but new ANN11 visible copy should follow the project i18n directive. [VERIFIED: AGENTS.md] [VERIFIED: .planning/phases/ANN11/ANN11-02-PLAN.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | `node --check main.js`, Vitest runtime | yes | v24.16.0 | none needed. [VERIFIED: command run] |
| `npm.cmd` | Plugin test command on Windows | yes | 11.13.0 | Use `npm.cmd`, not `npm` PowerShell script. [VERIFIED: command run] |
| `npm` PowerShell shim | Direct `npm --version` | no | blocked by execution policy | Use `npm.cmd`. [VERIFIED: command run] |
| Python / `py` launcher | Existing annotation CLI runtime, not ANN11 pure tests | no | not found | ANN11 should not require direct Python for JS card tests; CLI integration remains v0.2/ANN10 dependency. [VERIFIED: command run] |
| Vitest config | Plugin focused tests | present | `vitest.config.ts` uses jsdom | Current sandbox test run printed Vitest startup errors despite shell exit code 0; inspect output. [VERIFIED: paperforge/plugin/vitest.config.ts] [VERIFIED: command run] |
| Graphify | Optional graph context | no | disabled | Continue with direct file/code research. [VERIFIED: command run] |

**Missing dependencies with no fallback:**
- None blocking ANN11 research. [VERIFIED: command run]

**Missing dependencies with fallback:**
- `npm` PowerShell shim blocked; use `npm.cmd`. [VERIFIED: command run]
- Python unavailable; ANN11 should remain JS-only and not add Python validation steps. [VERIFIED: command run]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest `^2.1.0` with jsdom `^25.0.0`. [VERIFIED: paperforge/plugin/package.json] |
| Config file | `paperforge/plugin/vitest.config.ts`. [VERIFIED: paperforge/plugin/vitest.config.ts] |
| Quick run command | `Push-Location paperforge/plugin; npm.cmd test -- canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-render.test.mjs; Pop-Location` [VERIFIED: paperforge/plugin/package.json] |
| Full focused command | `Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-render.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs; Pop-Location` [VERIFIED: paperforge/plugin/package.json] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CANVAS-03 | Central shell/status area plus left/right card lanes | DOM | `npm.cmd test -- canvas-card-dom.test.mjs canvas-render.test.mjs` | no - Wave 0/Plan 02 |
| CANVAS-04 | Explicit loaded/empty/missing/error/refresh/stale states | unit + DOM | `npm.cmd test -- canvas-viewmodel.test.mjs canvas-render.test.mjs canvas-controller.test.mjs` | partial - render/controller exist, viewmodel missing |
| CARD-01 | Card fields include selected text, comment, page, color/type, source, provenance, read-only | unit + DOM | `npm.cmd test -- canvas-viewmodel.test.mjs canvas-card-dom.test.mjs` | no - Wave 0/Plan 01 |
| CARD-02 | Long/missing/CJK previews do not break layout hooks | unit + DOM | `npm.cmd test -- canvas-viewmodel.test.mjs canvas-card-dom.test.mjs` | no - Wave 0/Plan 01/02 |
| CARD-03 | Deterministic sorted left/right lanes | unit | `npm.cmd test -- canvas-layout.test.mjs annotation-list-viewmodel.test.mjs` | no - Wave 0/Plan 01 |
| CARD-04 | Source identity preserved and forbidden controls absent | unit + DOM | `npm.cmd test -- canvas-viewmodel.test.mjs canvas-card-dom.test.mjs annotation-main-runtime.test.mjs` | no - Wave 0/Plan 01/02 |

### Sampling Rate

- **Per task commit:** `Push-Location paperforge/plugin; npm.cmd test -- {new focused test file}; Pop-Location` and inspect output for startup errors. [VERIFIED: command run]
- **Per wave merge:** focused canvas + v0.2 annotation gate. [VERIFIED: .planning/phases/ANN10/ANN10-02-PLAN.md]
- **Phase gate:** `node --check main.js` plus all new ANN11 canvas tests and existing v0.2 annotation list/runtime DOM tests. [VERIFIED: .planning/REQUIREMENTS.md]

### Wave 0 Gaps

- [ ] `paperforge/plugin/src/canvas/view-model.js` - card/state projection for CANVAS-04 and CARD-01/CARD-02/CARD-04. [VERIFIED: codebase grep]
- [ ] `paperforge/plugin/src/canvas/layout.js` - deterministic left/right lanes for CARD-03. [VERIFIED: codebase grep]
- [ ] `paperforge/plugin/tests/canvas-viewmodel.test.mjs` - explicit states and card fields. [VERIFIED: codebase grep]
- [ ] `paperforge/plugin/tests/canvas-layout.test.mjs` - ordering/lane tests. [VERIFIED: codebase grep]
- [ ] Card DOM test file - rendered lanes/cards, long/CJK hooks, and forbidden controls. [VERIFIED: codebase grep]
- [ ] Confirm ANN10 runtime view/command/button before DOM integration in `main.js`. [VERIFIED: codebase grep]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth/session feature in ANN11. [VERIFIED: .planning/REQUIREMENTS.md] |
| V3 Session Management | yes | Canvas UI state remains session-local; no persistent layout state. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] |
| V4 Access Control | yes | Read-only boundary; no write/import/apply/edit controls. [VERIFIED: .planning/REQUIREMENTS.md] |
| V5 Input Validation | yes | Normalize annotation rows through existing contracts; safely handle missing fields. [VERIFIED: paperforge/plugin/src/testable.js] |
| V6 Cryptography | no | No cryptographic operations in ANN11. [VERIFIED: .planning/REQUIREMENTS.md] |

### Known Threat Patterns for Obsidian Plugin Canvas

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via selected text/comment/source fields | Tampering / Information Disclosure | Use `textContent`, `setText`, or safe element creation; test HTML-like fixtures. [VERIFIED: paperforge/plugin/src/canvas/render.js] [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs] |
| Wrong-paper stale cards after refresh | Spoofing | Fixed paperKey controller and stale sequence guard. [VERIFIED: paperforge/plugin/src/canvas/controller.js] |
| Mutation controls in read-only Zotero cards | Elevation of Privilege | Forbidden-control DOM tests and no calls to import/apply/write APIs. [VERIFIED: paperforge/plugin/tests/annotation-main-runtime.test.mjs] |
| Multi-PDF provenance confusion | Spoofing | Preserve sourceAttachmentKey/sourceAnnotationKey for later navigation; do not enable source claims beyond available identity. [VERIFIED: paperforge/plugin/src/testable.js] |
| Persistent layout side effects | Tampering | No localStorage/settings/`.canvas` persistence in ANN11. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md] |

## Concrete Recommended Plan Split

### Plan ANN11-01: Card View-Models and Deterministic Layout

**Files likely modified:**
- `paperforge/plugin/src/canvas/view-model.js`
- `paperforge/plugin/src/canvas/layout.js`
- `paperforge/plugin/src/canvas/index.js`
- `paperforge/plugin/tests/canvas-viewmodel.test.mjs`
- `paperforge/plugin/tests/canvas-layout.test.mjs`

**Scope:**
- Build explicit canvas/card view-model states for `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, `invalid-json`, `missing-source`, `unsupported`, `refreshing`, and stale/previous-data cases. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]
- Build card models from normalized rows with selected text, comment, page, color/type, source, attachment/provenance, read-only, identity, and future anchor placeholder fields. [VERIFIED: paperforge/plugin/src/testable.js]
- Assign lanes using existing reading-order sort semantics, then left/right alternation. [VERIFIED: paperforge/plugin/src/testable.js]
- Preserve no-mutation behavior for inputs and no persistent layout fields. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]

**Verification:**
- `npm.cmd test -- canvas-viewmodel.test.mjs canvas-layout.test.mjs annotation-list-viewmodel.test.mjs`
- Include missing fields, CJK-heavy strings, long strings, same-page same-sort tie-breakers, missing page/sortIndex, empty annotations, stale refresh, and source/provenance preservation. [VERIFIED: paperforge/plugin/tests/annotation-list-viewmodel.test.mjs]

### Plan ANN11-02: Card Lane DOM, CSS Resilience, and Runtime Gate

**Files likely modified:**
- `paperforge/plugin/src/canvas/render.js`
- `paperforge/plugin/styles.css`
- `paperforge/plugin/main.js` only if ANN10 runtime view is present and needs narrow render delegation update
- `paperforge/plugin/tests/canvas-render.test.mjs`
- `paperforge/plugin/tests/canvas-card-dom.test.mjs` or `canvas-section-dom.test.mjs`
- `paperforge/plugin/tests/annotation-section-dom.test.mjs`
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs`

**Scope:**
- Render central status/surface placeholder plus left/right lanes only for usable loaded card states. [VERIFIED: .planning/phases/ANN11/ANN11-CONTEXT.md]
- Add namespaced card/lane CSS: `.paperforge-canvas-lanes`, `.paperforge-canvas-lane-left`, `.paperforge-canvas-lane-right`, `.paperforge-canvas-card`, `.paperforge-canvas-card-selected-text`, `.paperforge-canvas-card-comment`, `.paperforge-canvas-readonly-badge`, `.paperforge-canvas-provenance`. [VERIFIED: .planning/research/ARCHITECTURE.md]
- Use safe text insertion and test HTML-like annotation strings. [VERIFIED: paperforge/plugin/src/canvas/render.js]
- Assert no forbidden controls/verbs in card lanes, card buttons, aria labels, or text. [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs]
- Preserve v0.2 annotation list/runtime tests. [VERIFIED: .planning/REQUIREMENTS.md]

**Verification:**
- `node --check main.js`
- `npm.cmd test -- canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs annotation-bridge.test.mjs annotation-list-viewmodel.test.mjs annotation-section-dom.test.mjs annotation-main-runtime.test.mjs`
- Inspect output for Vitest startup errors even if shell exit code is 0. [VERIFIED: command run]

## Sources

### Primary (local verified)

- `.planning/ROADMAP.md` - ANN11 phase goal, requirements, success criteria, and phase ordering. [VERIFIED: file read]
- `.planning/REQUIREMENTS.md` - CANVAS-03/CANVAS-04/CARD-01..04 and safe/out-of-scope constraints. [VERIFIED: file read]
- `.planning/phases/ANN11/ANN11-CONTEXT.md` - locked user decisions and phase scope. [VERIFIED: file read]
- `.planning/phases/ANN10/annotation-10-CONTEXT.md` and `ANN10-01/02-PLAN.md` - upstream canvas seams and dependency expectations. [VERIFIED: file read]
- `.planning/research/SUMMARY.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `STACK.md` - milestone architecture/stack/pitfall research. [VERIFIED: file read]
- `paperforge/plugin/src/testable.js` - normalized row shape, state names, sorting, identity, preview, PDF target helpers. [VERIFIED: codebase grep]
- `paperforge/plugin/src/canvas/*.js` - current ANN10 canvas modules. [VERIFIED: codebase grep]
- `paperforge/plugin/tests/*.mjs` - existing focused annotation and canvas test patterns. [VERIFIED: codebase grep]
- `paperforge/plugin/package.json`, `vitest.config.ts`, `styles.css`, `main.js` - stack, config, CSS, runtime integration evidence. [VERIFIED: codebase grep]
- `AGENTS.md` - project-specific directives for architecture, i18n, command/test guidance, and credential safety. [VERIFIED: file read]

### Secondary

- None used. External web/package research was unnecessary because ANN11 adds no dependencies and is constrained by local contracts. [VERIFIED: .planning/REQUIREMENTS.md]

### Tertiary

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - package/config files and milestone research agree no new dependencies are needed. [VERIFIED: paperforge/plugin/package.json]
- Architecture: MEDIUM-HIGH - local seams are clear, but current runtime view registration appears incomplete in `main.js`, so DOM integration must gate on ANN10 completion. [VERIFIED: codebase grep]
- Pitfalls: HIGH - risks are repeated across requirements, context, prior research, and existing tests. [VERIFIED: .planning/research/PITFALLS.md]

**Research date:** 2026-07-05
**Valid until:** 2026-08-04 for ANN11 local code contracts; re-check immediately if ANN10 runtime wiring changes before planning. [VERIFIED: codebase grep]
