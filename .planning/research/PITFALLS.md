# Domain Pitfalls

**Domain:** annotation v0.3 Visual Reading Canvas for the PaperForge Obsidian plugin
**Researched:** 2026-07-02
**Overall confidence:** HIGH for repo-specific risks, MEDIUM for live Obsidian/PDF runtime behavior until the pending harness is completed.

## Scope and Evidence

This note is specific to adding a PaperForge-controlled reading canvas with central reading content, side annotation cards, and future connector lines to the existing annotation branch.

Evidence read:
- `.planning/PROJECT.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md`
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md`
- `.planning/MILESTONES.md`
- `.planning/STATE.md`
- `.planning/REQUIREMENTS.md`
- `paperforge/plugin/main.js`
- `paperforge/plugin/src/testable.js`
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs`
- `paperforge/plugin/package.json`

Research seam note: `gsd-tools query classify-confidence` is not available in this shell (`gsd-tools` command not found). Confidence is therefore assigned from direct local source evidence rather than the unavailable classify-confidence seam.

## Critical Pitfalls

### Pitfall 1: Duplicating the Annotation Runtime Instead of Reusing v0.2 Contracts

**What goes wrong:** The canvas introduces a second annotation loader, direct database reads, or a card-specific JSON shape instead of consuming the existing `paperforge annotation status/export --json` bridge and normalized state.

**Why it happens:** Canvas UI feels like a new product surface, but the branch already has a tested annotation source of truth: `loadAnnotationsForPaper()`, `makeAnnotationState()`, `normalizeAnnotationExportRow()`, `buildAnnotationListViewModel()`, `resolveAnnotationPdfTarget()`, and overlay/popover view-model helpers in `src/testable.js` and copied into `main.js`.

**Consequences:** Missing DB, missing paper, invalid JSON, CLI failures, stale refresh behavior, attachment identity, and read-only provenance diverge between list/overlay/canvas. The canvas may show different rows from the existing annotation list or regress PFResult parsing.

**Prevention:** Make the first v0.3 phase a canvas data contract phase. Build `buildAnnotationCanvasViewModel()` as a pure helper over the existing normalized annotation state. It should not call Python, SQLite, Zotero, or Obsidian APIs directly. It should preserve `display`, `provenance`, `pdfLocation`, `raw`, read-only status, source, source attachment key, annotation key, page, color/type, selected text, and comment.

**Detection:** Tests should fail if the canvas loads annotations without `getAnnotationState()` or if it calls new `paperforge annotation` commands outside the existing bridge. Add grep-style review checks for direct `annotations.db`, `sqlite`, `annotation import --apply`, or new subprocess commands in canvas code.

**Roadmap phase:** Phase 10, "Canvas Data Contract and Card View-Models." Do this before any DOM layout work.

**Confidence:** HIGH. The current v0.2 bridge and tests are explicit, and `.planning/PROJECT.md` says v0.3 reuses v0.2 contracts.

### Pitfall 2: Helper Drift Between `main.js` and `src/testable.js`

**What goes wrong:** Canvas helpers get added to `src/testable.js` for Vitest but are manually copied, partially copied, or not copied into shipped `main.js`. Tests pass against helper code while Obsidian runs stale or different logic.

**Why it happens:** `main.js` is 6,779 lines and contains an "Inlined from src/testable.js" block. `.planning/codebase/CONCERNS.md` already flags helper drift between `main.js` and `src/testable.js` as a maintenance risk. v0.3 canvas helpers will likely increase this copied surface unless the build/import contract is fixed.

**Consequences:** Card ordering, anchor resolution, connector eligibility, safety filtering, or text escaping can pass in Node tests and fail in the actual plugin.

**Prevention:** Before the canvas DOM phase, choose one contract: either establish a real bundle/build path from `src/` into `main.js`, or keep every canvas helper tested through `main.js.__test` in addition to direct helper tests. Avoid large unreviewed manual copy blocks. If manual inlining remains, add an explicit parity test for exported helper behavior.

**Detection:** Add a runtime harness test that imports `main.js`, obtains `PaperForgeStatusView` and any canvas helpers from `module.exports.__test`, and verifies the exact canvas VM used by the real view. Add a CI/review checklist item: "canvas helper changed in one file only?".

**Roadmap phase:** Phase 10. Treat this as a hard preflight gate before canvas layout.

**Confidence:** HIGH. Existing code and concerns document the drift risk directly.

### Pitfall 3: Building the Canvas on Live Obsidian PDF Internals

**What goes wrong:** The "PaperForge-controlled" canvas still depends on `.pdf-embed`, `.pdf-viewer`, `.pdf-container`, `[data-page-number]`, or canvas ancestry as its primary surface. Obsidian changes the PDF DOM and the entire canvas breaks.

**Why it happens:** v0.2 overlay code necessarily probes Obsidian PDF viewer internals in `_findPdfViewerRoot()` and `_tryAttachAnnotationOverlay()`. v0.3's target UI has connectors and source/card geometry, which tempts reuse of overlay internals even though `.planning/PROJECT.md` says native PDF internals cannot reliably own the target UI.

**Consequences:** Canvas availability becomes tied to an unverified live PDF overlay harness. Users lose side cards and reading flow when only overlay support should degrade. v0.3 may falsely claim live PDF robustness while v0.2 TEST-04 is still pending.

**Prevention:** The MVP central surface should be PaperForge-owned. Prefer a controlled text/OCR reading surface for MVP grounding, with "open PDF/page" and existing overlay as secondary affordances. If a PDF pane is unavailable, the canvas should still render cards and source snippets from annotation selected text/comments. Connector lines should be gated behind measured PaperForge-owned anchors, not raw Obsidian PDF DOM assumptions.

**Detection:** Add tests where no active PDF leaf exists and the canvas still renders card lanes plus source snippets. Add a separate manual harness item that explicitly says live native PDF overlay status is independent of canvas MVP status.

**Roadmap phase:** Phase 11, "Controlled Reading Canvas Layout." Phase 13, "Connector Geometry Spike," may revisit PDF-aware connectors only after controlled anchors work.

**Confidence:** HIGH for risk, MEDIUM for live behavior. The DOM dependency is visible in `main.js`; the live viewer harness is still pending.

### Pitfall 4: Breaking the Read-Only Safety Boundary Through Rich Cards

**What goes wrong:** Annotation cards gain edit/delete/save/import/apply/write-back/evidence/concept-card actions because cards look like objects rather than read-only imported Zotero evidence.

**Why it happens:** v0.3 asks for richer cards and future media. Existing future requirements mention local editing, evidence integration, and Zotero write-back, but v0.3 boundaries explicitly defer them. The v0.2 tests already guard absence of forbidden controls in list and popover surfaces.

**Consequences:** Users may mutate `annotations.db`, Zotero-derived records, paper metadata, or future evidence state from a milestone whose purpose is visual reading only. This would invalidate the established safety story from annotation v0.1 and v0.2.

**Prevention:** Canvas cards are read-only by contract. Allowed actions: select card, focus source anchor, open PDF/page, refresh annotations, collapse/expand details, and copy/display local text if explicitly scoped as non-mutating. Disallowed actions: create, edit, delete, save, remove, import, apply, write back, sync to Zotero, database mutation, concept-card/evidence mutation.

**Detection:** Add DOM tests for `.paperforge-reading-canvas` that search all buttons, menu labels, accessible names, and text for forbidden verbs. Add runtime spies proving canvas interactions do not call `fileManager.processFrontMatter`, vault writes, annotation import/apply commands, Zotero writes, or direct DB mutation.

**Roadmap phase:** Phase 11 and every subsequent canvas UI phase. Repeat the safety test suite whenever card controls are added.

**Confidence:** HIGH. This boundary is repeated in project decisions, requirements, v0.2 verification, and current tests.

### Pitfall 5: Drawing Connector Lines That Lie About Grounding

**What goes wrong:** Connector lines appear between cards and approximate source locations even when the anchor rectangle is missing, stale, measured in the wrong coordinate space, hidden by scroll, or attached to the wrong page/PDF.

**Why it happens:** Current overlay helpers only accept finite non-negative PDF rects and render one rectangle per mark. A multi-lane canvas introduces new coordinate spaces: central surface scroll, side lanes, card height, zoom, collapsed cards, sorted rows, and future PDF/text alternatives.

**Consequences:** The UI visually asserts evidence grounding that the data cannot support. This is worse than no connector because it misleads the researcher about where an annotation came from.

**Prevention:** Treat connector rendering as a separate later phase, not part of the first canvas layout. Define `anchorStatus` values such as `exact`, `source-snippet-only`, `page-only`, `unresolved`, and draw connectors only for `exact` anchors measured in the current canvas coordinate system. If coordinates are unavailable, show a card/source association without a line.

**Detection:** Synthetic layout tests must cover scroll offsets, resized lanes, collapsed cards, missing rects, invalid `positionJson`, multiple pages, multiple PDFs, and filtered cards. Tests should assert "no connector" for unresolved anchors. Manual gate should check scroll/resize and not just initial render.

**Roadmap phase:** Phase 13, "Connector Geometry Spike and Guarded Rendering." Do not include connector lines in the Phase 11 layout acceptance gate except as placeholders disabled by default.

**Confidence:** HIGH. Existing overlay code already validates position JSON and skips invalid marks; connectors add more coordinate risk.

### Pitfall 6: Showing the Wrong Paper's Cards After Async Navigation or Refresh

**What goes wrong:** The user changes active file/pane/paper while annotation loading or canvas refresh is in progress, and stale rows render into the new paper's canvas.

**Why it happens:** v0.2 already needed `_annotationLoadSeq` and captured paper keys to discard stale loader results. A new canvas surface may rerender independently, preserve selected card state, or trigger refreshes without using the same guard.

**Consequences:** A card lane can display annotations from Paper A beside the central content of Paper B. Connector lines and page jumps then become source-spoofing bugs.

**Prevention:** Canvas state must be keyed by `paperKey`, `pdfPath` or source attachment identity, and active file path where relevant. Every async canvas refresh should capture the paper key and load sequence. On paper, pane, file, annotation, or mode change, clear selected card, measured anchors, connector overlays, and transient canvas DOM.

**Detection:** Add runtime tests that start a canvas load for Paper A, switch `_currentPaperKey` to Paper B, resolve the old promise, and assert Paper A cards do not render. Add teardown tests for close, mode switch, active leaf change, and manual refresh failure.

**Roadmap phase:** Phase 10 for state contract; Phase 11 for DOM lifecycle.

**Confidence:** HIGH. Existing code has stale-result guards because this risk already occurred in the display layer design.

### Pitfall 7: Regressing the Existing List/Overlay Fallback While Adding Canvas

**What goes wrong:** The canvas replaces or rewires `_renderPaperMode()` so the existing annotation section, page badge navigation, overlay fallback, and refresh states stop working.

**Why it happens:** `_renderPaperMode()` currently owns paper header, status strip, overview, annotation section, overlay refresh, next step, discussion, and technical details in one method. Canvas work will naturally target this method.

**Consequences:** v0.3 makes the plugin less reliable than v0.2. If canvas prerequisites fail, users lose the proven list/jump fallback that the milestone explicitly promises to preserve.

**Prevention:** Make the canvas additive behind a clear mode/section gate. Keep the existing annotation list as fallback and preferably as a collapsible secondary surface until canvas is stable. Do not delete `_renderAnnotationSection()`, `_openAnnotationPdf()`, or overlay fallback behavior in the MVP.

**Detection:** The v0.2 focused gate remains mandatory after every canvas phase: `node --check main.js` and the five annotation suites recorded in Phase 9. Add a canvas-specific test where canvas prerequisites are unavailable and `.paperforge-annotations-section` still renders with refresh/filter/group/page badge behavior.

**Roadmap phase:** Phase 11 and final Phase 14 verification gate.

**Confidence:** HIGH. The Phase 9 gate and project docs explicitly require fallback preservation.

## Moderate Pitfalls

### Pitfall 8: Letting `main.js` Grow Instead of Creating a Reviewable Canvas Boundary

**What goes wrong:** v0.3 adds another large UI subsystem directly into the already huge plugin entrypoint.

**Prevention:** Keep pure logic in testable helpers and keep runtime wiring thin. Define component boundaries even if the plugin still ships a single bundled `main.js`: canvas VM builder, card lane renderer, central reading surface renderer, connector renderer, and canvas lifecycle controller. If a build system is deferred, at least group the inlined runtime code under one clearly delimited section and expose test hooks through `main.js.__test`.

**Roadmap phase:** Phase 10 preflight and Phase 11 implementation.

**Confidence:** HIGH. `CONCERNS.md` flags `main.js` as 6,090 lines at audit time; current file is 6,779 lines.

### Pitfall 9: Losing Provenance in Card Presentation

**What goes wrong:** Cards optimize for selected text/comment but hide source, page, read-only state, attachment identity, annotation identity, or sync state.

**Prevention:** Card view-models should have a compact visible layer and a details layer, but provenance must be available. At minimum, each card needs source, read-only status, page label/number, source attachment key, annotation key, type/color, and a stable identity. The default view can be concise; expansion must preserve traceability.

**Roadmap phase:** Phase 10 and Phase 12, "Card Interaction and Navigation."

**Confidence:** HIGH. v0.2 normalized rows already preserve these fields and tests assert their display in list/popover paths.

### Pitfall 10: Multi-PDF and Supplementary Attachment Confusion

**What goes wrong:** A card or central surface resolves an annotation to the main PDF when the annotation belongs to a supplementary PDF, or enables a page jump without matching `sourceAttachmentKey`.

**Prevention:** Reuse `resolveAnnotationPdfTarget()` exactly. The only permitted identity-free fallback is the existing single-candidate case. When multiple PDF candidates exist and no attachment identity is present, disable source-specific navigation/connectors and show a stable non-sensitive reason.

**Roadmap phase:** Phase 10 for VM contract; Phase 12 for card-to-source navigation.

**Confidence:** HIGH. Existing resolver and tests already encode this fail-closed policy.

### Pitfall 11: Canvas Text Injection and XSS Through Annotation Content

**What goes wrong:** Selected text, comments, titles, page labels, or source fields are rendered with `innerHTML` in cards or central snippets.

**Prevention:** Use Obsidian `createEl(..., { text })`, `setText()`, or `textContent` for all user-provided annotation fields. Reserve `innerHTML` only for hard-coded SVG/icon markup. Canvas tests should inject `<script>` and `<b>` strings into selected text and comments.

**Roadmap phase:** Phase 11 and Phase 12.

**Confidence:** HIGH. Existing annotation popover tests already enforce textContent for malicious-looking annotation text; `CONCERNS.md` flags broader plugin `innerHTML` usage.

### Pitfall 12: Unbounded DOM and Layout Cost for Large Annotation Sets

**What goes wrong:** A paper with hundreds of annotations renders every source snippet, card, connector, resize observer, and event handler at once.

**Prevention:** The MVP should bound card lanes with internal scrolling, render only the current paper, avoid continuous polling, and avoid per-card global listeners. Connector rendering should be opt-in by viewport/visible card set, not all rows. Preserve the v0.2 pattern of bounded UI state and no persistent localStorage/settings writes.

**Roadmap phase:** Phase 11 layout; Phase 13 connector rendering.

**Confidence:** MEDIUM-HIGH. Existing list uses bounded compact styling; canvas/connector scale has not been implemented yet.

### Pitfall 13: Encoding Corruption Gets Cemented Into New Canvas Strings

**What goes wrong:** New visible labels are added near existing mojibake, copied from corrupted strings, or saved with the wrong encoding.

**Prevention:** Keep new v0.3 strings ASCII/English unless deliberately repairing UTF-8 Chinese strings from a trusted source. Do not edit unrelated corrupted labels while adding canvas code. Add an encoding grep/check for common mojibake sequences before the verification gate.

**Roadmap phase:** Every implementation phase; final Phase 14 verification.

**Confidence:** HIGH. `CONCERNS.md`, `PROJECT.md`, and visible `main.js` excerpts show mojibake in docs and user-facing strings.

### Pitfall 14: Treating jsdom Success as Live Obsidian Success

**What goes wrong:** The roadmap declares the visual canvas complete because Vitest passes, while Obsidian pane behavior, theme CSS, scroll measurement, PDF opening, or resize behavior fails in the actual app.

**Prevention:** Keep automated gates for pure logic and runtime wiring, but add a manual/live harness for the canvas MVP: open a paper with annotations, render the canvas, select cards, jump to source PDF/page, verify fallback when no PDF pane is active, resize panes, switch files, and confirm teardown.

**Roadmap phase:** Phase 14, "Canvas Verification Gate." If connectors are included, Phase 13 also needs a geometry-specific manual checkpoint.

**Confidence:** HIGH. v0.2 already has an automated gate passed while live Obsidian PDF verification remains pending.

## Minor Pitfalls

### Pitfall 15: Persisting Ephemeral Canvas UI State

**What goes wrong:** Selected card, search query, lane side, collapsed groups, or connector visibility are written to plugin settings or localStorage.

**Prevention:** Keep canvas UI state session-local unless a later explicit settings phase exists. Tests should assert no `saveData` or localStorage writes from card selection, filtering, lane switching, or source focus.

**Roadmap phase:** Phase 10 state contract and Phase 11 DOM tests.

**Confidence:** HIGH. Existing annotation UI state is intentionally session-only.

### Pitfall 16: CSS Collisions With Existing PaperForge and Obsidian UI

**What goes wrong:** Generic class names like `.card`, `.canvas`, `.lane`, `.connector`, or broad CSS rules affect dashboard cards, next-step cards, Obsidian panes, or existing annotation rows.

**Prevention:** Namespace every canvas selector with `paperforge-reading-canvas` or `paperforge-canvas-*`. Avoid global element selectors. Keep the existing list selectors untouched.

**Roadmap phase:** Phase 11 layout.

**Confidence:** MEDIUM-HIGH. The plugin has many existing card-like components and no component CSS isolation.

### Pitfall 17: Card Navigation Mutates Layout State Indirectly

**What goes wrong:** Clicking a card to open a page also rerenders the whole paper mode, resets filters, collapses rows, or triggers overlay refresh in a loop.

**Prevention:** Separate "focus source/card" from "open Obsidian PDF page." Source focus should be local canvas state. PDF opening should reuse `_openAnnotationPdf()` and must not call `_renderPaperMode()` or mutate annotation state.

**Roadmap phase:** Phase 12 card interactions.

**Confidence:** HIGH. v0.2 tests already assert page-badge navigation does not mutate `_annotationUiState`.

## Phase-Specific Warnings

| Suggested v0.3 Phase | Likely Pitfall | Required Mitigation / Gate |
|----------------------|----------------|-----------------------------|
| Phase 10: Canvas Data Contract and Card View-Models | Duplicate loaders, helper drift, provenance loss, wrong PDF identity | Pure helper tests plus `main.js.__test` runtime harness; no direct DB access; card VM preserves provenance and uses `resolveAnnotationPdfTarget()` |
| Phase 11: Controlled Reading Canvas Layout | Obsidian PDF dependency, fallback regression, XSS, unbounded DOM, CSS collision | Canvas renders without active PDF viewer; existing annotation list still renders; textContent tests with HTML-like annotation text; namespaced CSS; bounded lanes |
| Phase 12: Card Selection and Source Navigation | Read-only boundary breach, wrong-paper state, UI state mutation | Forbidden-control DOM tests; spies for no writes/import/apply; stale async key tests; card/page navigation does not mutate annotation state |
| Phase 13: Connector Geometry Spike and Guarded Rendering | Misleading connector lines, scroll/resize geometry bugs, performance | Draw connectors only for exact measured anchors; no connector for unresolved/page-only anchors; synthetic scroll/resize tests; manual geometry checkpoint |
| Phase 14: Canvas Verification Gate | jsdom-only confidence, v0.2 fallback regression, pending live overlay confusion | Re-run v0.2 focused gate; run canvas suites; record live Obsidian canvas harness; explicitly keep v0.2 live PDF overlay status separate |

## Roadmap Guardrails

1. Start with data and identity, not visuals. The first phase should prove that canvas cards are a view over the existing annotation state and not a new backend.
2. Make the controlled reading surface useful before connector lines. Connector lines are evidence claims; they need stricter gates than cards.
3. Keep the existing annotation list/page jump/overlay fallback alive until the final verification gate says the canvas is reliable.
4. Treat read-only as a recurring gate, not a one-time decision. Every new button/menu/card interaction must pass the forbidden-control and no-write tests.
5. Do not claim live PDF overlay completion as part of v0.3 unless the pending v0.2 Obsidian PDF harness has been completed and recorded.

## Sources

- `.planning/PROJECT.md` (HIGH): v0.3 goal, target features, read-only scope, safe fallback, pending live overlay harness.
- `.planning/codebase/CONCERNS.md` (HIGH): large `main.js`, helper drift, fragile Obsidian runtime, encoding corruption, annotation contract fragility.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` (HIGH): automated gate passed, live Obsidian PDF viewer check pending, exact focused test set.
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-OBSIDIAN-OVERLAY-HARNESS.md` (HIGH): live overlay/fallback/read-only checklist still pending.
- `.planning/MILESTONES.md` and `.planning/STATE.md` (HIGH): v0.3 boundaries, v0.2 decisions, helper inlining decision, known baseline failures.
- `.planning/REQUIREMENTS.md` (HIGH): v0.2 completed requirements and deferred future editing/evidence/write-back requirements.
- `paperforge/plugin/main.js` (HIGH): current shipped runtime shape, annotation state, `_renderPaperMode()`, `_renderAnnotationSection()`, `_openAnnotationPdf()`, overlay lifecycle, popover rendering, copied helper block.
- `paperforge/plugin/src/testable.js` (HIGH): pure annotation bridge/list/navigation/overlay/popover helpers.
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` (HIGH): runtime harness for real `main.js`, stale/UI/read-only/navigation/overlay/popover tests.
- `paperforge/plugin/package.json` (MEDIUM): current test stack is Vitest/jsdom/obsidian mocks, not a live Obsidian harness.
