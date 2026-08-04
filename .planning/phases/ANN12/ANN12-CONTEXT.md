# Phase ANN12: Controlled Reading Surface and Source Anchors - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase ANN12 creates the PaperForge-owned central reading surface and source anchor model for the Visual Reading Canvas.

In plain terms: this phase makes the middle of the canvas render readable source content when available and marks where annotation evidence can honestly be grounded. It introduces anchor identity and anchor status, but it does not make cards and source anchors interactive yet.

This phase does not implement card-to-source navigation, source-to-card navigation, selection synchronization, connector lines, native PDF DOM anchoring, local annotation editing, Zotero write-back, persistent layout, or new annotation import/apply flows.

</domain>

<decisions>
## Implementation Decisions

### Source Surface Priority
- **D-01:** The central reading surface should prefer the paper entry's `fulltext_path` and render `fulltext.md` content inside the PaperForge-owned canvas when that file is available.
- **D-02:** If `fulltext_path` content is unavailable, the surface may fall back to readable formal note body or summary content from `entry.note_path`.
- **D-03:** If neither fulltext nor usable note content is available, the central surface must render an explicit page-level/source-unavailable placeholder instead of a blank surface.
- **D-04:** The surface must be PaperForge-owned DOM. It must not depend on Obsidian native PDF viewer selectors, PDF page canvases, `.pdf-viewer`, `.pdf-embed`, `[data-page-number]`, or other native PDF internals.
- **D-05:** Source rendering should use safe text insertion and bounded rendering. Annotation-selected text, source text, and note text must not be inserted through `innerHTML`.

### Anchor Precision Levels
- **D-06:** Source anchors have three explicit precision statuses: `exact`, `page-level`, and `unresolved`.
- **D-07:** `exact` means PaperForge can locate the annotation's selected text uniquely inside the PaperForge-owned source text. Only this status may render inline source highlighting.
- **D-08:** `page-level` means the annotation has usable page/source metadata but no trustworthy unique text span. It may render a page or block marker, but it must not highlight a specific sentence or paragraph as if exact.
- **D-09:** `unresolved` means source content, page metadata, selected text, or matching confidence is insufficient. It must render a clear explanation and no inline source marker.
- **D-10:** The UI must make the precision difference visible enough that users do not confuse page-level or unresolved anchors with exact evidence grounding.

### Exact Text Matching
- **D-11:** Exact text anchors should be generated only when normalized selected text has exactly one match in the PaperForge-owned source text.
- **D-12:** Empty selected text, very short selected text, missing source text, ambiguous multiple matches, unclear CJK/punctuation/whitespace normalization, or source/paper identity mismatch must downgrade to `page-level` or `unresolved`.
- **D-13:** ANN12 must not guess among multiple candidate matches or use fuzzy ranking as if it were exact.
- **D-14:** Matching logic should preserve enough diagnostics for tests and future UI copy, such as `reason`, `matchCount`, `sourceKind`, `pageIndex`, and annotation identity.

### Missing Source Behavior
- **D-15:** Annotation cards remain visible when source content is missing; missing source is an anchoring limitation, not an absence of annotations.
- **D-16:** When annotations exist but no readable source exists, the central surface should show a `source unavailable` state and anchor models should become `unresolved` with an explicit reason.
- **D-17:** Missing `fulltext_path` and missing/unreadable file content should be distinguishable in model/test behavior where practical, but neither should crash the canvas.
- **D-18:** The canvas must avoid implying "no annotations" when the real state is "annotations exist but cannot be grounded to source."

### Anchor Visual Form
- **D-19:** `exact` anchors should render as restrained inline highlights inside the central source text, preferably using the annotation color when available without overwhelming readability.
- **D-20:** `page-level` anchors should render as page/block-level markers or a source strip marker, not as inline text highlights.
- **D-21:** `unresolved` anchors should not draw source highlights or page markers; they should appear as status/explanation text in the surface and/or card metadata.
- **D-22:** ANN12 visual anchor classes must be namespaced under the PaperForge canvas namespace and must not introduce connector-line classes or geometry.

### Safe Deferred Interaction Boundary
- **D-23:** ANN12 should expose and render anchor identity, status, source span/page block, reason, and provenance needed by later phases.
- **D-24:** ANN12 must not implement card click-to-source scrolling, source click-to-card focus, keyboard selection sync, hovered/selected connector geometry, or SVG connector paths.
- **D-25:** ANN12 must preserve the read-only boundary: no create, edit, delete, save, import, apply, write-back, evidence mutation, or concept-card mutation controls.
- **D-26:** Future PDF-aware surfaces should remain behind a separate seam. ANN12 may define the seam, but it must not build directly on native PDF DOM internals.

### the agent's Discretion
The user approved the recommended conservative grounding strategy. The planner may choose exact helper names, source model shapes, normalization thresholds, CSS class names, placeholder copy, and test file names as long as the decisions above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` - Current annotation v0.3 goal, target visual canvas direction, read-only scope, and v0.2 live harness caveat.
- `.planning/REQUIREMENTS.md` - ANCHOR-01, ANCHOR-02, SAFE, and TEST requirements that define ANN12 boundaries.
- `.planning/ROADMAP.md` - ANN12 goal, dependencies, success criteria, and deferred ANN13/ANN14 interaction work.
- `.planning/STATE.md` - Current milestone state and known execution/planning caveats.

### v0.3 Research
- `.planning/research/SUMMARY.md` - Recommends a PaperForge-owned text/page-level reading surface and exact/page/unresolved fallback anchors.
- `.planning/research/ARCHITECTURE.md` - Defines `src/canvas/surface.js` as the likely seam for PaperForge-owned source rendering and warns against native PDF DOM dependency.
- `.planning/research/PITFALLS.md` - Calls out misleading connectors/anchors, native PDF internals, stale async renders, and read-only boundary risks.
- `.planning/research/STACK.md` - Confirms existing CommonJS, DOM, CSS, Vitest/jsdom stack and no new PDF renderer for MVP.

### Prior Canvas Phases
- `.planning/phases/ANN10/annotation-10-CONTEXT.md` - Explicit canvas paper identity, module boundaries, shell states, and deferral of source anchors to ANN12.
- `.planning/phases/ANN11/ANN11-CONTEXT.md` - Card model/lane decisions, card source identity preservation, read-only boundary, and deferral of source anchors to ANN12.
- `.planning/phases/ANN11/ANN11-01-SUMMARY.md` - Implemented card view-model and deterministic layout outputs, including `anchor: unresolved` placeholders.
- `.planning/phases/ANN11/ANN11-02-SUMMARY.md` - Implemented read-only card lane rendering, CSS/i18n, and no-anchor/no-connector class boundary.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` - Existing v0.2 PDF page navigation fallback and attachment identity safety; ANN12 should not replace ANN13 navigation.
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md` - Native PDF overlay risk decisions and strict source identity.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - Automated v0.2 gate status and pending live native PDF harness note.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - Current PaperForge Reading Canvas runtime, paper entry fields such as `note_path` and `fulltext_path`, and existing fulltext open behavior.
- `paperforge/plugin/src/canvas/context.js` - Canvas paper context and explicit paper identity.
- `paperforge/plugin/src/canvas/annotations.js` - v0.2-compatible annotation loader wrapper.
- `paperforge/plugin/src/canvas/view-model.js` - ANN11 card model projection and current unresolved anchor placeholder.
- `paperforge/plugin/src/canvas/layout.js` - Deterministic card reading-order/lane helper.
- `paperforge/plugin/src/canvas/render.js` - Canvas shell/card rendering; ANN12 should extend with surface/anchor rendering while preserving safe text insertion.
- `paperforge/plugin/src/canvas/index.js` - Narrow CommonJS export surface for canvas modules.
- `paperforge/plugin/src/testable.js` - Existing normalized annotation row fields, `pdfLocation.pageIndex`, `positionJson`, `selectorJson`, source attachment identity, and overlay helper precedents.
- `paperforge/plugin/tests/canvas-viewmodel.test.mjs` - Card model tests and anchor placeholder expectations to extend for ANN12.
- `paperforge/plugin/tests/canvas-render.test.mjs` and `canvas-card-dom.test.mjs` - DOM safety patterns, forbidden classes, and card rendering assertions.
- `paperforge/plugin/tests/annotation-overlay.test.mjs` - Prior overlay parsing/page identity helper tests; use as cautionary reference, not as native PDF DOM foundation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Paper entries already expose `fulltext_path`, `note_path`, `pdf_path`, and source metadata in `paperforge/plugin/main.js`.
- `paperforge/plugin/src/canvas/view-model.js` currently gives cards an unresolved anchor placeholder saying source anchors are implemented in ANN12; this is the natural upgrade point.
- `paperforge/plugin/src/testable.js` preserves annotation source fields: `selectedText`, `comment`, `pageIndex`, `pageLabel`, `positionJson`, `selectorJson`, `sourceAttachmentKey`, and `sourceAnnotationKey`.
- Existing overlay helper tests show how to handle page identity and parsed position data conservatively, but ANN12 must not reintroduce native PDF viewer dependency.

### Established Patterns
- Canvas modules are CommonJS under `paperforge/plugin/src/canvas/` and exported through `index.js`.
- UI rendering uses safe DOM/text APIs and namespaced CSS classes.
- Read-only annotation UI must not expose mutation controls or write-back verbs.
- Focused Vitest/jsdom tests are the primary confidence source; live Obsidian/PDF confidence remains separate.

### Integration Points
- `paperforge/plugin/src/canvas/surface.js` is the likely new module for reading source content models, source blocks, and fallback states.
- `paperforge/plugin/src/canvas/view-model.js` should likely merge card models with anchor models/status once source matching exists.
- `paperforge/plugin/src/canvas/render.js` should render the central source surface and anchor markers/highlights using PaperForge-owned DOM.
- `paperforge/plugin/main.js` may need a narrow runtime read path for vault files such as `fulltext_path` or `note_path`, but should remain a thin integration layer.
- `paperforge/plugin/i18n.js` should receive visible ANN12 source/anchor state copy in both `zh` and `en` if new user-facing strings are introduced.

</code_context>

<specifics>
## Specific Ideas

- The target product direction remains the dark visual reading canvas with central reading content, side annotation cards, and eventually relationship lines.
- ANN12 should make the center finally feel like a reading surface, but the source grounding must be honest: exact highlights only when the source text uniquely supports them.
- Page-level and unresolved anchors are first-class states, not failures to hide.
- The UI should explain "source unavailable" separately from "no annotations."

</specifics>

<deferred>
## Deferred Ideas

- Card-to-source and source-to-card navigation belong to ANN13.
- Focus/selection synchronization belongs to ANN13.
- Connector lines, connector geometry, hover/selected relationship drawing, and final visual polish belong to ANN14.
- Full canvas verification and live harness recording belong to ANN15.
- Native PDF DOM anchoring, PDF.js/bundled PDF rendering, fuzzy/ranked exact matching, draggable source/card layout, local annotation editing, Zotero write-back, AI cards, and multi-paper boards remain future scope.

</deferred>

---

*Phase: ANN12-controlled-reading-surface-and-source-anchors*
*Context gathered: 2026-07-06*
