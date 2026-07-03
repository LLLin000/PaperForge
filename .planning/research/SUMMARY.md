# Project Research Summary

**Project:** PaperForge annotation v0.3 Visual Reading Canvas
**Domain:** Local-first Obsidian PDF/text annotation reading canvas
**Researched:** 2026-07-03
**Confidence:** HIGH for PaperForge-owned canvas architecture and feature boundaries; MEDIUM for live Obsidian PDF-viewer behavior until the v0.2 harness is recorded.

## Executive Summary

PaperForge v0.3 should build a read-only visual reading canvas for one active paper: central reading content, left/right annotation cards, source anchors, bidirectional navigation, and a guarded connector foundation. This is not a generic Obsidian Canvas clone, not an annotation editor, and not a Zotero write-back milestone. Mature tools such as Zotero Reader, Readwise Reader, MarginNote, and Obsidian Canvas point toward annotation-first cards, page/source grounding, color semantics, and visual links, but PaperForge should adopt only the parts that preserve evidence traceability.

The recommended implementation is conservative: add a new PaperForge-owned Obsidian `ItemView`, keep `main.js` changes thin, place canvas logic under `paperforge/plugin/src/canvas/`, use existing v0.2 annotation bridge/list/navigation/overlay contracts as the data source, and render the MVP with plain DOM plus SVG. Do not add React/Svelte, D3/Cytoscape, PDF.js, Obsidian Canvas persistence, new Python APIs, or persistent layout state for the MVP.

The main risks are coupling the canvas to unstable native Obsidian PDF internals, duplicating annotation loading/state, drifting tested helpers away from shipped `main.js`, and drawing connector lines that imply stronger grounding than the data supports. Mitigate by starting with data/view-model contracts, using a PaperForge-owned text/page-level reading surface first, treating connectors as guarded evidence claims, preserving v0.2 fallback paths, and making the pending live Obsidian PDF harness an explicit confidence note rather than a hidden assumption.

## Key Findings

### Stack Additions / Non-Additions

Use the existing plugin stack. v0.3 needs new modules and tests, not a new framework.

**Core technologies:**
- Obsidian `ItemView`: separate PaperForge Reading Canvas pane with explicit `paperKey` state.
- CommonJS modules under `paperforge/plugin/src/canvas/`: deep module boundary for context, controller, view-model, layout, surface, and rendering.
- Plain DOM + SVG: cards, lanes, anchors, and focused connector paths without graph/canvas libraries.
- Existing Vitest/jsdom/Obsidian mocks: pure helper, controller, and DOM coverage alongside existing annotation tests.
- Obsidian CSS variables and namespaced PaperForge classes: `.paperforge-reading-canvas-*` / `.paperforge-canvas-*`.

**Do not add for MVP:**
- React, Svelte, Vue, or a new build system.
- D3, Cytoscape, freeform graph libraries, or physics layout.
- PDF.js or a bundled PDF renderer before the canvas shape is proven.
- Obsidian `.canvas` file persistence or localStorage/settings persistence.
- New Python annotation APIs, direct SQLite reads, or new subprocess commands.

### Expected Canvas MVP Features

**Must have (table stakes):**
- Open a PaperForge Reading Canvas for an explicit active paper.
- Load paper-scoped annotations through existing v0.2 contracts.
- Show central reading content with clear text/page fallback when PDF embedding is unavailable.
- Render left/right annotation card lanes using deterministic reading-order layout.
- Cards display selected text, comment, page, color/type, source, attachment/provenance, and read-only state.
- Render colored source anchors where supported, with page-level/unresolved fallback states.
- Support card-to-source and source-to-card navigation.
- Draw focused connector lines only for selected/hovered card-anchor pairs with confirmed geometry.
- Preserve safe fallback to the v0.2 annotation list, PDF page jump, and overlay path.
- Handle refresh, stale loads, teardown, empty/error states, and keyboard/accessibility basics.
- Enforce read-only behavior: no create/edit/delete/save/import/apply/write-back controls.

**Should have if table stakes are stable:**
- Evidence-grade metadata in compact card details.
- Deterministic lane placement by reading/source order.
- Focused connector mode rather than always-on connector webs.
- Optional compact/expanded card density.
- Annotation color/type legend.
- Source-aware unsupported-position messages.
- Future-rich card schema for later figures, tables, evidence cards, and AI notes.

**Defer / out of scope:**
- Local annotation creation/editing/deletion.
- Zotero write-back or direct Zotero SQLite mutation.
- Freeform draggable cards and persistent user-authored layouts.
- Multi-paper boards, literature-review synthesis, cross-document search.
- AI summaries, clustering, QA cards, concept/evidence mutation.
- Mind maps, flashcards, spaced repetition.
- Rich media/figure/table cards.
- Mobile/touch optimization and full infinite-canvas pan/zoom.
- Re-researching annotation import/storage already settled by v0.1/v0.2.

### Architecture Recommendation

Build v0.3 as a new PaperForge-owned `ItemView`, not as another branch inside `PaperForgeStatusView._renderPaperMode()` and not as an overlay on the native Obsidian PDF viewer. The existing dashboard remains the entry point/fallback; the canvas owns its central surface, side lanes, anchors, connector SVG, and session state.

**Module seams:**
1. `main.js`: register `VIEW_TYPE_PAPERFORGE_READING_CANVAS`, add command/button, expose minimal runtime test hook.
2. `src/canvas/context.js`: resolve explicit paper key, index entry, and fallback reason.
3. `src/canvas/annotations.js`: wrap existing annotation loader with stale guards and refresh reasons.
4. `src/canvas/view-model.js`: build paper, card, lane, anchor, connector-intent, empty/error/fallback states.
5. `src/canvas/layout.js`: deterministic left/right lane assignment and connector planning.
6. `src/canvas/surface.js`: PaperForge-owned text/page-level reading surface contract; future PDF surface hides behind this seam.
7. `src/canvas/render.js`: DOM rendering for shell, lanes, cards, anchors, connector SVG, banners.
8. `src/canvas/controller.js`: session lifecycle, selection, refresh, scroll/resize, navigation, teardown.
9. `styles.css`: namespaced canvas styles only; do not mutate existing annotation list styles.

**Important architectural rule:** connector geometry may measure only PaperForge-owned anchors/cards. Native PDF DOM selectors such as `.pdf-embed`, `.pdf-viewer`, page-layer canvases, or `[data-page-number]` are not the v0.3 canvas foundation.

### Critical Pitfalls

1. **Duplicating annotation runtime**: build the canvas view-model over existing normalized v0.2 annotation state; no new DB reads or subprocess contracts.
2. **Helper drift between `main.js` and `src/testable.js`**: prefer real imports from `src/canvas/*`; if manual inlining remains, add `main.js.__test` parity/runtime coverage.
3. **Native PDF internals as foundation**: use a PaperForge-owned text/page-level surface first and keep native overlay as risk-gated fallback.
4. **Read-only boundary breach**: test for forbidden verbs/controls and no writes/import/apply/write-back from every card interaction.
5. **Misleading connectors**: draw lines only for exact measured anchors in the current canvas coordinate system; page-only/unresolved anchors get no connector.
6. **Wrong-paper stale async renders**: key all loads and transient UI state by paper/source identity; discard stale results and clear selection/connectors on paper changes.
7. **Regressing v0.2 fallback**: keep the existing annotation list/page jump/overlay behavior intact and run the v0.2 focused gate after each canvas phase.

## Implications for Roadmap

### Phase 1: Canvas Data Contract and Module Skeleton

**Rationale:** Data identity and shipped/tested helper boundaries must be correct before visual work.
**Delivers:** new canvas view type, `src/canvas/*` skeletons, explicit `paperKey` state, open command/button, blank canvas lifecycle, test exports.
**Addresses:** canvas entry point, v0.2 data reuse, missing-paper/error states.
**Avoids:** duplicate annotation runtime, helper drift, `main.js` bloat.
**Research flag:** standard patterns; no extra research needed unless the current CommonJS import path cannot load `src/canvas/*` from shipped Obsidian.

### Phase 2: Annotation Controller and Card View-Models

**Rationale:** Cards should be a projection of the existing annotation source of truth, not a second annotation model.
**Delivers:** stale-guarded annotation controller, card models, read-only provenance, source/page/attachment identity, empty/missing-db/CLI-error states, lane assignment.
**Addresses:** card view-model, deterministic side lanes, read-only safety, multi-PDF identity.
**Avoids:** wrong-paper cards, provenance loss, direct DB or Zotero access.
**Research flag:** standard patterns; verify against existing v0.2 bridge/list tests.

### Phase 3: Controlled Reading Surface and Anchors

**Rationale:** Navigation and connectors need a PaperForge-owned source surface before geometry can be trusted.
**Delivers:** central text/formal-note/page-level reading surface, exact text anchors only when unambiguous, page/unresolved fallback anchors, responsive layout.
**Addresses:** central reading content, colored source anchors, unsupported-position handling.
**Avoids:** native PDF DOM dependency, XSS via annotation text, unbounded layout cost.
**Research flag:** may need focused phase research if fulltext/formal-note path shapes vary more than current docs imply.

### Phase 4: Bidirectional Navigation and Safe Fallback

**Rationale:** The canvas becomes useful when users can move between card and source while retaining v0.2 fallbacks.
**Delivers:** card selection, card-to-source focus/scroll, source-to-card focus, PDF page open fallback via existing navigation helpers, dashboard/list fallback buttons, keyboard basics.
**Addresses:** card/source navigation, fallback path, accessibility basics.
**Avoids:** layout mutation loops, read-only breach, fallback regression.
**Research flag:** standard patterns; manual Obsidian check recommended because navigation crosses workspace panes.

### Phase 5: Focused Connector Layer

**Rationale:** Connectors are the highest-risk visual evidence claim and should come after cards, anchors, and navigation are stable.
**Delivers:** SVG connector layer for selected/hovered exact measured card-anchor pairs; scroll/resize redraw; hide/remove on stale geometry, refresh, teardown, page-only/unresolved anchors.
**Addresses:** connector foundation and target visual linkage.
**Avoids:** misleading grounding, scroll/resize geometry bugs, performance issues.
**Research flag:** needs deeper planning/research during phase planning if exact connector behavior expands beyond owned text/page anchors into PDF-aware geometry.

### Phase 6: Verification Gate and Live Harness Record

**Rationale:** jsdom confidence is not live Obsidian confidence, and v0.2 live PDF harness remains pending.
**Delivers:** full canvas test suite, existing v0.2 focused annotation gate, `node --check main.js`, live Obsidian canvas harness notes, explicit statement separating canvas MVP status from native PDF overlay status.
**Addresses:** refresh/teardown, read-only gate, fallback preservation, layout resilience, pending harness documentation.
**Avoids:** claiming PDF overlay reliability from automated tests alone.
**Research flag:** needs manual/live validation; do not skip.

### Phase Ordering Rationale

- View registration and data contracts come first because every later surface depends on stable paper identity and annotation snapshots.
- Cards and lanes come before central anchors/connectors because visual geometry should be derived from a tested view-model.
- Reading surface and anchors come before connector lines because connectors must not be drawn against unowned or ambiguous coordinates.
- Navigation comes before connector polish because the core user value is round-tripping between evidence card and source.
- The verification gate is separate because v0.2 already showed automated tests can pass while live Obsidian PDF behavior remains unrecorded.

### Research Flags

**Needs deeper phase research / live validation:**
- Phase 3 if central fulltext/formal-note rendering must support more source formats than documented.
- Phase 5 if connector geometry expands into PDF-aware anchors or any non-owned DOM.
- Phase 6 for live Obsidian pane behavior, resize/scroll measurement, and the pending v0.2 PDF viewer harness status.

**Standard patterns / skip research-phase:**
- Phase 1: Obsidian view registration and module skeletons follow existing plugin patterns.
- Phase 2: annotation loading and stale guards reuse v0.2 contracts.
- Phase 4: selection state, fallback buttons, and `openLinkText()` navigation use known local patterns, though still need manual verification.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing CommonJS Obsidian plugin stack is sufficient; research strongly argues against new dependencies for MVP. |
| Features | HIGH | Table stakes and out-of-scope boundaries are repeated across project docs and feature research. Exact target visual is not attached, so visual polish priorities are MEDIUM. |
| Architecture | HIGH | Recommendation follows current codebase contracts and avoids known `main.js`/PDF-internal risks. |
| Pitfalls | HIGH | Most risks are directly evidenced by v0.2 implementation, verification notes, and codebase concerns. Live PDF behavior remains MEDIUM. |

**Overall confidence:** HIGH for roadmap shape and MVP boundaries; MEDIUM for live Obsidian/PDF runtime details.

### Gaps to Address

- **v0.2 live Obsidian PDF harness pending:** v0.3 can proceed only if it does not claim native PDF overlay reliability; record this explicitly in final verification.
- **Shipped-source boundary:** confirm whether `main.js` can require/import `src/canvas/*`; if not, add parity tests and document temporary inlining debt.
- **Fulltext-to-annotation anchoring:** exact text anchors may be unreliable; accept page-level anchors unless matching is unambiguous.
- **Connector performance and geometry:** validate scroll/resize/teardown manually and synthetically before enabling visible connector lines beyond focused mode.
- **Encoding corruption:** keep new v0.3 strings ASCII/English unless deliberately repairing known text from a trusted source.

## Sources

### Primary
- `.planning/PROJECT.md` - current v0.3 goal, target features, read-only scope, pending v0.2 live harness.
- `.planning/research/STACK.md` - stack additions/non-additions and test strategy.
- `.planning/research/FEATURES.md` - table-stakes canvas features, differentiators, deferred scope, anti-features.
- `.planning/research/ARCHITECTURE.md` - ItemView recommendation, module boundaries, data flow, fallback architecture.
- `.planning/research/PITFALLS.md` - critical/moderate/minor risks and phase-specific warnings.
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/STRUCTURE.md` - local codebase integration evidence cited by researchers.
- `paperforge/plugin/main.js`, `paperforge/plugin/src/testable.js`, `paperforge/plugin/styles.css`, `paperforge/plugin/tests/*.test.mjs` - shipped plugin and test boundary evidence cited by researchers.

### External / Product References
- Zotero PDF Reader documentation - annotation colors, notes, page links, show-on-page behavior.
- Readwise Reader product page - annotation-first reading, PDF support, keyboard reading, Obsidian export.
- MarginNote product page - highlights as cards, bidirectional source links, broader study-system scope to defer.
- Obsidian Canvas documentation - visual language reference for cards, connectors, colors, pan/zoom, and `.canvas` persistence to avoid in MVP.

---
*Research completed: 2026-07-03*
*Ready for roadmap: yes*
