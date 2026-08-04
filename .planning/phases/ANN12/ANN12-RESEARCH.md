# Phase ANN12: Controlled Reading Surface and Source Anchors - Research

**Researched:** 2026-07-06  
**Domain:** PaperForge Obsidian plugin controlled reading surface and source anchoring  
**Confidence:** HIGH

## User Constraints (from ANN12-CONTEXT.md)

### Locked Decisions

- The central reading surface should prefer the paper entry's `fulltext_path` and render `fulltext.md` content inside the PaperForge-owned canvas when that file is available. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- If `fulltext_path` content is unavailable, the surface may fall back to readable formal note body or summary content from `entry.note_path`. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- If neither fulltext nor usable note content is available, the central surface must render an explicit page-level/source-unavailable placeholder instead of a blank surface. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- The surface must be PaperForge-owned DOM and must not depend on Obsidian native PDF viewer selectors, PDF page canvases, `.pdf-viewer`, `.pdf-embed`, `[data-page-number]`, or other native PDF internals. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Source rendering must use safe text insertion and bounded rendering; annotation-selected text, source text, and note text must not be inserted through `innerHTML`. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Source anchors have exactly three precision statuses: `exact`, `page-level`, and `unresolved`. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- `exact` anchors are allowed only when PaperForge can locate the normalized annotation selected text uniquely inside PaperForge-owned source text; only `exact` may render inline highlighting. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- `page-level` means usable page/source metadata exists but no trustworthy unique span exists; it may render a page or block marker but must not highlight a sentence or paragraph as exact. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- `unresolved` means source content, page metadata, selected text, or matching confidence is insufficient; it must render a clear explanation and no inline source marker. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Exact text anchors should be generated only when normalized selected text has exactly one match in the PaperForge-owned source text. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Empty selected text, very short selected text, missing source text, ambiguous multiple matches, unclear CJK/punctuation/whitespace normalization, or source/paper identity mismatch must downgrade to `page-level` or `unresolved`. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Matching logic must not guess among multiple candidates or use fuzzy ranking as if it were exact. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Matching logic should preserve diagnostics for tests and future UI copy, including `reason`, `matchCount`, `sourceKind`, `pageIndex`, and annotation identity. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Missing source is an anchoring limitation, not an absence of annotations; annotation cards remain visible. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- `exact` anchors should render restrained inline highlights; `page-level` anchors should render page/block-level markers or a source strip marker; `unresolved` anchors should render explanation only. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- ANN12 must expose anchor identity, status, source span/page block, reason, and provenance needed by later phases, but must not implement navigation, selection sync, connector geometry, or SVG connector paths. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- ANN12 must preserve the read-only boundary: no create, edit, delete, save, import, apply, write-back, evidence mutation, or concept-card mutation controls. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

### the agent's Discretion

The user approved the recommended conservative grounding strategy. The planner may choose exact helper names, source model shapes, normalization thresholds, CSS class names, placeholder copy, and test file names as long as the decisions above are preserved. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)

- Card-to-source and source-to-card navigation belong to ANN13. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Focus/selection synchronization belongs to ANN13. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Connector lines, connector geometry, hover/selected relationship drawing, and final visual polish belong to ANN14. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Full canvas verification and live harness recording belong to ANN15. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Native PDF DOM anchoring, PDF.js/bundled PDF rendering, fuzzy/ranked exact matching, draggable source/card layout, local annotation editing, Zotero write-back, AI cards, and multi-paper boards remain future scope. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

## Summary

ANN12 should add a PaperForge-owned central source surface and first-class source anchor model, not a navigation or connector system. [VERIFIED: .planning/ROADMAP.md] The milestone already has read-only cards, deterministic lanes, safe DOM insertion patterns, and runtime view delegation in place from ANN11. [VERIFIED: .planning/phases/ANN11/ANN11-01-SUMMARY.md; .planning/phases/ANN11/ANN11-02-SUMMARY.md; paperforge/plugin/src/canvas/render.js]

The recommended approach is to implement source-content modeling and anchor resolution as pure CommonJS helpers first, then extend DOM/runtime rendering. [VERIFIED: paperforge/plugin/src/canvas/view-model.js; paperforge/plugin/src/canvas/render.js] Source content priority is `fulltext_path` first, `note_path` fallback second, then an unavailable placeholder; anchor precision must be `exact`, `page-level`, or `unresolved`, with `exact` allowed only for exactly one normalized match. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

**Primary recommendation:** Split ANN12 into two plans: pure source/anchor model tests first, then DOM/runtime integration and CSS, with no new packages and no PDF DOM dependency. [VERIFIED: .planning/phases/ANN11/ANN11-02-SUMMARY.md; paperforge/plugin/src/canvas/index.js]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANCHOR-01 | Source anchors render for annotations with supported PaperForge-owned position, text, or page data. | Implement pure anchor resolution over selected text and page metadata, then render owned DOM markers. [VERIFIED: .planning/REQUIREMENTS.md; .planning/phases/ANN12/ANN12-CONTEXT.md] |
| ANCHOR-02 | Page-level or unresolved fallback anchors render when exact text/geometry anchoring is unavailable. | Treat page-level and unresolved as first-class states with visible copy and diagnostics. [VERIFIED: .planning/REQUIREMENTS.md; .planning/phases/ANN12/ANN12-CONTEXT.md] |
| SAFE-01/S-02/S-03 | Canvas remains read-only, avoids persistent mutations, and does not depend on native PDF internals. | Keep helper modules pure, use text APIs, and test forbidden controls/classes. [VERIFIED: .planning/REQUIREMENTS.md; paperforge/plugin/tests/canvas-render.test.mjs; paperforge/plugin/tests/canvas-main-runtime.test.mjs] |

## Current State Summary

- `view-model.js` builds card models and currently assigns every card `anchor: { status: 'unresolved', reason: 'Source anchors are implemented in ANN12.' }`; this is the natural upgrade point for ANN12. [VERIFIED: paperforge/plugin/src/canvas/view-model.js]
- `buildCanvasCardViewModel()` already preserves cards through `ready`, `refreshing`, and `stale` states and assigns deterministic lanes, so source grounding should attach to cards without replacing lane behavior. [VERIFIED: paperforge/plugin/src/canvas/view-model.js]
- `render.js` provides the safe DOM helper `createEl()` and uses `textContent` for user-facing text; ANN12 should keep all source, note, and selected-text insertion on this path. [VERIFIED: paperforge/plugin/src/canvas/render.js]
- `renderCanvasView()` currently renders identity, shell states, and card lanes; it has no central source surface, anchor classes, or connector classes yet. [VERIFIED: paperforge/plugin/src/canvas/render.js; paperforge/plugin/tests/canvas-main-runtime.test.mjs]
- `index.js` exports a narrow CommonJS canvas surface; ANN12 should add source/anchor helpers and render helpers there, following the existing export pattern. [VERIFIED: paperforge/plugin/src/canvas/index.js]
- `PaperForgeReadingCanvasView` captures explicit paper context and delegates rendering to `./src/canvas`; it currently builds only an idle or missing-paper VM from that context. [VERIFIED: paperforge/plugin/main.js around PaperForgeReadingCanvasView]
- Existing tests already assert safe text rendering, no forbidden write controls, no anchor/connector classes before ANN12, and runtime delegation. ANN12 should update those expectations intentionally. [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs; paperforge/plugin/tests/canvas-main-runtime.test.mjs]

## Recommended Implementation Approach

### 1. Add a Pure Source Surface Model

Create `paperforge/plugin/src/canvas/surface.js` for source-content selection, source block shaping, text normalization, and anchor resolution. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] Keep it pure: no Obsidian imports, no fs imports, no database calls, and no native PDF DOM selectors. [VERIFIED: paperforge/plugin/src/canvas/view-model.js; .planning/phases/ANN12/ANN12-CONTEXT.md]

Recommended source model:

```js
{
  state: 'ready' | 'source-unavailable',
  sourceKind: 'fulltext' | 'note' | 'unavailable',
  paperKey,
  text,
  blocks: [{ id, kind: 'text' | 'page-placeholder', pageIndex, text }],
  diagnostics: { reason, fulltextPath, notePath }
}
```

Source priority must be: usable `entry.fulltext_path` content first, usable `entry.note_path` content second, explicit unavailable placeholder third. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] Runtime file reading should stay in `main.js` or a narrow injected adapter, then pass text into pure canvas helpers; pure helper tests can inject strings directly. [VERIFIED: paperforge/plugin/main.js around PaperForgeReadingCanvasView; paperforge/plugin/src/canvas/view-model.js]

### 2. Resolve Anchors Conservatively

Add anchor helpers that convert each card/annotation into exactly one of:

```js
{ status: 'exact', anchorId, cardId, sourceKind, matchStart, matchEnd, matchCount: 1, reason: 'unique-normalized-text-match' }
{ status: 'page-level', anchorId, cardId, sourceKind, pageIndex, matchCount, reason }
{ status: 'unresolved', anchorId, cardId, sourceKind, pageIndex: null, matchCount, reason }
```

`exact` is valid only when normalized selected text is non-empty, not below the chosen minimum threshold, and has exactly one normalized match in the PaperForge-owned source text. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] Multiple matches, zero matches with page metadata, overly short text, CJK/punctuation uncertainty, or missing source must downgrade without guessing. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

Use page metadata for `page-level` only when the annotation has usable page identity and the source model can honestly represent a page/block marker. [VERIFIED: .planning/REQUIREMENTS.md; .planning/phases/ANN12/ANN12-CONTEXT.md] Use `unresolved` when source content, selected text, page metadata, or confidence is insufficient. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

Diagnostics must be preserved on every anchor, including at least `reason`, `matchCount`, `sourceKind`, `pageIndex`, `cardId`, and source/provenance identity. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

### 3. Merge Anchors Into Card View-Models

Extend `buildCanvasCardViewModel()` to accept a source model or anchor options and replace the ANN11 unresolved placeholder with computed anchors. [VERIFIED: paperforge/plugin/src/canvas/view-model.js] Cards must remain visible when source is missing; missing source changes anchor status to `unresolved`, not canvas state to empty. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md; paperforge/plugin/src/canvas/view-model.js]

### 4. Render the Owned Source Surface

Extend `renderCanvasView()` so `ready`, `refreshing`, and `stale` states can render a central `.paperforge-canvas-source-surface` between/alongside existing lanes. [VERIFIED: paperforge/plugin/src/canvas/render.js] Use namespaced classes such as `.paperforge-canvas-source`, `.paperforge-canvas-anchor--exact`, `.paperforge-canvas-anchor--page-level`, and `.paperforge-canvas-anchor--unresolved`; do not add connector or navigation classes in ANN12. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md; paperforge/plugin/tests/canvas-main-runtime.test.mjs]

Exact anchors may render inline highlights only around the unique owned source span. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] Page-level anchors should render page/block markers or a source strip marker, not text highlights. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] Unresolved anchors should render explanation/status copy only, with no marker implying a grounded span. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

## Plan Split Recommendation

### ANN12-01: Pure Source Surface and Anchor Contracts

Scope:
- Add `surface.js` with source selection, text normalization, block creation, and anchor resolution helpers. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- Extend `view-model.js` so cards can carry computed `exact`, `page-level`, and `unresolved` anchors. [VERIFIED: paperforge/plugin/src/canvas/view-model.js]
- Add/extend `canvas-viewmodel.test.mjs` for `fulltext_path` source, `note_path` fallback, source-unavailable placeholder, exact-only-one-match, ambiguous downgrade, page-level fallback, unresolved fallback, CJK/short-text downgrade, and diagnostics preservation. [VERIFIED: paperforge/plugin/tests/canvas-viewmodel.test.mjs]
- Export pure helpers through `index.js`. [VERIFIED: paperforge/plugin/src/canvas/index.js]

Exit gate:
- Pure tests prove exact/page-level/unresolved semantics and no model-level action controls. [VERIFIED: paperforge/plugin/tests/canvas-viewmodel.test.mjs]

### ANN12-02: Source Surface DOM, Runtime Adapter, and Styling

Scope:
- Add the narrow runtime file-read/adaptation path needed for `fulltext_path` first and `note_path` fallback, while keeping `PaperForgeReadingCanvasView` as a thin integration point. [VERIFIED: paperforge/plugin/main.js around PaperForgeReadingCanvasView]
- Extend `render.js` with source surface and anchor render helpers using `textContent`/text nodes only. [VERIFIED: paperforge/plugin/src/canvas/render.js]
- Add namespaced CSS for the central reading surface and anchor statuses. [VERIFIED: .planning/phases/ANN11/ANN11-02-SUMMARY.md]
- Extend `canvas-render.test.mjs` and `canvas-main-runtime.test.mjs` for safe insertion, placeholder rendering, anchor status classes, forbidden controls, absence of native PDF selectors, absence of connector/navigation classes, and runtime delegation. [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs; paperforge/plugin/tests/canvas-main-runtime.test.mjs]

Exit gate:
- DOM/runtime tests prove source content is rendered safely, source unavailable is explicit, and ANN12 did not add navigation, editing/writeback, connector, or native PDF DOM dependency. [VERIFIED: .planning/REQUIREMENTS.md; paperforge/plugin/tests/canvas-render.test.mjs]

## Architecture Patterns

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Source content loading | Obsidian runtime adapter | Pure canvas helpers | Runtime may read vault files, but helpers should receive plain text and remain testable. [VERIFIED: paperforge/plugin/main.js around PaperForgeReadingCanvasView; paperforge/plugin/src/canvas/view-model.js] |
| Anchor resolution | Pure canvas model | DOM renderer | Resolution is deterministic data logic and should be tested before rendering. [VERIFIED: paperforge/plugin/src/canvas/view-model.js; paperforge/plugin/tests/canvas-viewmodel.test.mjs] |
| Source surface rendering | DOM renderer | CSS | Rendering belongs in `render.js`, using the existing safe `createEl()` pattern. [VERIFIED: paperforge/plugin/src/canvas/render.js] |
| Styling | Plugin CSS | DOM class names | ANN11 established namespaced CSS for card/lane presentation. [VERIFIED: .planning/phases/ANN11/ANN11-02-SUMMARY.md] |
| Navigation/connectors | Out of scope | ANN13/ANN14 | ANN12 only exposes anchor identity/status for later phases. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Native PDF anchoring | PDF DOM scraping, PDF page canvas selectors, `.pdf-viewer` probing | PaperForge-owned text/page surface | Native PDF internals are explicitly out of scope and risk-gated. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Exact matching confidence | Fuzzy scorer, ranking heuristic, guessed best match | Exact one normalized match or downgrade | Ambiguity must not be represented as exact evidence. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Source DOM insertion | `innerHTML` markdown/source rendering | `textContent`, text nodes, bounded DOM blocks | Existing tests enforce safe insertion patterns. [VERIFIED: paperforge/plugin/src/canvas/render.js; paperforge/plugin/tests/canvas-render.test.mjs] |
| Interactions | Card click scrolling, source click focus, keyboard selection sync | Defer to ANN13 | ANN12 must expose anchors, not implement navigation. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Connectors | SVG paths, hover/selected line geometry | Defer to ANN14 | Connector geometry requires later focus/measurement work. [VERIFIED: .planning/ROADMAP.md; .planning/phases/ANN12/ANN12-CONTEXT.md] |

## Common Pitfalls

### Blank Surface When Source Is Missing

**What goes wrong:** The central surface appears empty and users cannot tell whether annotations are absent or source grounding failed. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]  
**Avoid by:** Render an explicit source-unavailable placeholder and keep annotation cards visible with `unresolved` anchors. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

### Overstating Precision

**What goes wrong:** Page-level or ambiguous text matches look like exact highlights. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]  
**Avoid by:** Only inline-highlight `exact`; render page-level markers separately and unresolved as explanation copy only. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

### Unsafe Source Rendering

**What goes wrong:** Fulltext, note content, selected text, or comments are inserted through `innerHTML`. [VERIFIED: paperforge/plugin/src/canvas/render.js; paperforge/plugin/tests/canvas-render.test.mjs]  
**Avoid by:** Use `createEl()` with `text`, `textContent`, and text nodes; add tests using HTML-like strings in source and selected text. [VERIFIED: paperforge/plugin/src/canvas/render.js; paperforge/plugin/tests/canvas-render.test.mjs]

### Runtime Ownership Creep

**What goes wrong:** `PaperForgeReadingCanvasView` grows into the source parser, matcher, and renderer. [VERIFIED: paperforge/plugin/main.js around PaperForgeReadingCanvasView]  
**Avoid by:** Keep runtime file reading/adaptation narrow and route matching/rendering through `src/canvas` modules. [VERIFIED: paperforge/plugin/src/canvas/index.js]

### Diagnostics Loss

**What goes wrong:** Tests and later UI cannot explain why an anchor downgraded. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]  
**Avoid by:** Preserve `reason`, `matchCount`, `sourceKind`, `pageIndex`, `cardId`, and source identity on every anchor. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

## Risks and Verification Strategy

| Risk | Verification |
|------|--------------|
| Exact anchors appear on ambiguous repeated text. | Unit test repeated normalized source text produces `page-level` or `unresolved`, never `exact`, with `matchCount > 1`. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Missing fulltext hides existing annotations. | Unit/runtime test annotations remain visible with source-unavailable surface and `unresolved` anchors. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Note fallback masks fulltext priority. | Unit test fulltext wins when both fulltext and note content are available; note is used only when fulltext is unavailable/unusable. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Unsafe rendering permits HTML injection. | DOM tests assert raw `<script>` strings appear in `textContent` and not as live tags in `innerHTML`. [VERIFIED: paperforge/plugin/tests/canvas-render.test.mjs] |
| ANN12 accidentally implements deferred interaction. | Runtime/DOM tests assert no navigation handlers/classes, no connector classes, no SVG connector paths, no draggable attributes, and no write controls. [VERIFIED: paperforge/plugin/tests/canvas-main-runtime.test.mjs; .planning/phases/ANN12/ANN12-CONTEXT.md] |
| Native PDF internals leak into implementation. | Static/runtime tests scan for forbidden selectors: `.pdf-viewer`, `.pdf-embed`, `[data-page-number]`, PDF canvas probing, and native PDF DOM anchor code. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md] |

Recommended automated gate:

```bash
cd paperforge/plugin
npx vitest run tests/canvas-viewmodel.test.mjs tests/canvas-render.test.mjs tests/canvas-main-runtime.test.mjs
node --check main.js
```

[VERIFIED: paperforge/plugin/tests/canvas-viewmodel.test.mjs; paperforge/plugin/tests/canvas-render.test.mjs; paperforge/plugin/tests/canvas-main-runtime.test.mjs]

## Explicit Scope Exclusions

- No native PDF DOM dependency: no `.pdf-viewer`, `.pdf-embed`, PDF canvas selectors, `[data-page-number]`, or native Obsidian PDF internals as the foundation. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- No connectors: no connector-line classes, SVG paths, hover/selected line geometry, or offscreen measurement. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- No navigation: no card-to-source scrolling, source-to-card focus, keyboard selection sync, or fallback page-jump behavior in ANN12. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]
- No editing/writeback: no create, edit, delete, save, import, apply, write-back, evidence mutation, concept-card mutation, Zotero mutation, vault-note mutation, localStorage, settings, or persistent layout writes. [VERIFIED: .planning/REQUIREMENTS.md; .planning/phases/ANN12/ANN12-CONTEXT.md]
- No fuzzy/ranked exact matching: ambiguous or uncertain text must downgrade. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]

## Code Examples

Recommended exact-match contract:

```js
function resolveTextAnchor(card, sourceModel) {
  const selected = normalizeAnchorText(card.selectedText);
  if (!selected || selected.length < MIN_EXACT_TEXT_LENGTH) {
    return unresolved(card, sourceModel, 'selected-text-too-short');
  }

  const matches = findNormalizedMatches(sourceModel.text, selected);
  if (matches.length === 1) {
    return exact(card, sourceModel, matches[0], matches.length);
  }
  if (card.pageIndex != null) {
    return pageLevel(card, sourceModel, 'text-match-not-unique', matches.length);
  }
  return unresolved(card, sourceModel, 'text-match-not-unique', matches.length);
}
```

This example is a planning sketch, not existing code. [ASSUMED]

Recommended safe rendering shape:

```js
const span = createEl('span', {
  cls: 'paperforge-canvas-anchor paperforge-canvas-anchor--exact',
  text: sourceSlice
});
```

This follows the existing `createEl()`/`textContent` pattern in `render.js`. [VERIFIED: paperforge/plugin/src/canvas/render.js]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact helper names and model object names can be chosen by the planner. | Code Examples / Implementation Approach | Low; ANN12-CONTEXT explicitly leaves helper names and model shapes to agent discretion. |
| A2 | A minimum exact-match text length should exist, but the threshold value is not specified here. | Recommended Implementation Approach | Medium; planner must choose a conservative threshold and test downgrade behavior. |

## Open Questions (RESOLVED)

1. **RESOLVED: Where should vault file reading live?**  
   What we know: `PaperForgeReadingCanvasView` currently delegates rendering to `src/canvas` and stores the explicit paper entry. [VERIFIED: paperforge/plugin/main.js around PaperForgeReadingCanvasView]  
   What's unclear: The exact existing vault-read helper for `fulltext_path`/`note_path` was outside this narrow read set. [ASSUMED]  
   Resolution: ANN12-02 assigns vault file reading to a narrow `main.js` runtime adapter (`_loadCanvasSourceInputs` / `_readVaultText` style helpers) that reads `entry.fulltext_path` before `entry.note_path`, preserves structured read diagnostics, and passes already-read source inputs into pure ANN12-01 helpers. [VERIFIED: .planning/phases/ANN12/ANN12-02-PLAN.md]

2. **RESOLVED: What text normalization threshold is safest for CJK-heavy text?**  
   What we know: CJK-heavy card text is already tested for safe preservation. [VERIFIED: paperforge/plugin/tests/canvas-viewmodel.test.mjs]  
   What's unclear: ANN12 does not specify the exact threshold or CJK normalization algorithm. [VERIFIED: .planning/phases/ANN12/ANN12-CONTEXT.md]  
   Resolution: ANN12-01 requires a documented `MIN_EXACT_TEXT_CHARS` threshold and conservative offset mapping tests. Exact anchors are produced only for one confidently mappable normalized match; short, ambiguous, source-mismatched, or CJK/punctuation/whitespace-uncertain cases downgrade to `page-level` or `unresolved` with diagnostics. [VERIFIED: .planning/phases/ANN12/ANN12-01-PLAN.md]

## Sources

### Primary (HIGH confidence)

- `.planning/ROADMAP.md` - ANN12 goal, dependencies, success criteria, and scope boundaries.
- `.planning/REQUIREMENTS.md` - ANCHOR, SAFE, and TEST requirements.
- `.planning/phases/ANN12/ANN12-CONTEXT.md` - Locked implementation decisions, precision semantics, and deferred scope.
- `.planning/phases/ANN11/ANN11-01-SUMMARY.md` - Existing card model and lane contracts.
- `.planning/phases/ANN11/ANN11-02-SUMMARY.md` - Existing card DOM, CSS, i18n, and runtime regression state.
- `paperforge/plugin/src/canvas/view-model.js` - Current card view-model and ANN12 anchor placeholder.
- `paperforge/plugin/src/canvas/render.js` - Current safe DOM rendering and card lane renderer.
- `paperforge/plugin/src/canvas/index.js` - Current CommonJS export surface.
- `paperforge/plugin/main.js` around `PaperForgeReadingCanvasView` - Runtime canvas integration point.
- `paperforge/plugin/tests/canvas-viewmodel.test.mjs` - Current model tests.
- `paperforge/plugin/tests/canvas-render.test.mjs` - Current DOM safety/render tests.
- `paperforge/plugin/tests/canvas-main-runtime.test.mjs` - Current runtime wiring and no-anchor/no-connector tests.

### Secondary (MEDIUM confidence)

- None used.

### Tertiary (LOW confidence)

- None used beyond explicitly logged planning sketches.

## Metadata

**Confidence breakdown:**
- Current state: HIGH - verified against the requested code and ANN11 summaries.
- Implementation approach: HIGH - constrained by ANN12 locked decisions and existing module structure.
- Plan split: HIGH - follows the ANN11 pure-model then DOM/runtime pattern.
- Risks and verification: HIGH - mapped to existing test files and explicit phase exclusions.

**Research date:** 2026-07-06  
**Valid until:** 2026-08-05
