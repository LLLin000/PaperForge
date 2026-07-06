# Roadmap: PaperForge annotation v0.3 - Visual Reading Canvas

## Overview

annotation v0.3 builds a PaperForge-controlled visual reading canvas for one active paper. The target experience is a central reading surface with left/right annotation cards, source anchors, bidirectional focus, and guarded connector lines that show evidence relationships without implying unsupported precision.

The milestone deliberately stays read-only. It reuses v0.2 annotation bridge/list/navigation/overlay contracts, avoids native Obsidian PDF viewer internals as the canvas foundation, and preserves v0.2 fallback paths when canvas prerequisites are missing.

## Phases

- [x] **Phase ANN10: Canvas Data Contract and View Registration** - Add a PaperForge Reading Canvas view shell with explicit paper identity and reusable module seams.
- [x] **Phase ANN11: Annotation Card View-Models and Layout** - Project existing annotations into read-only card models and deterministic side lanes.
- [ ] **Phase ANN12: Controlled Reading Surface and Source Anchors** - Render a PaperForge-owned central source surface with exact, page-level, and unresolved anchors.
- [ ] **Phase ANN13: Bidirectional Navigation and Fallback Paths** - Connect cards and source anchors through focus/scroll behavior while preserving v0.2 PDF navigation fallback.
- [ ] **Phase ANN14: Focused Connector Layer and Visual Polish** - Draw guarded focused connectors and harden responsive/readable canvas presentation.
- [ ] **Phase ANN15: Canvas Verification Gate and Live Harness Record** - Prove automated canvas behavior, preserve v0.2 gates, and record live Obsidian confidence.

## Phase Details

### Phase ANN10: Canvas Data Contract and View Registration

**Goal:** Establish a PaperForge-owned Reading Canvas entry point with stable paper identity before visual work begins.

**Depends on:** Annotation Phase 9 automated verification gate

**Requirements:** CANVAS-01, CANVAS-02

**Success Criteria:**

1. Plugin registers a dedicated PaperForge Reading Canvas `ItemView` and an open command/button.
2. The canvas opens with explicit `paperKey`/paper identity and does not infer stale state from unrelated panes.
3. `paperforge/plugin/src/canvas/*` modules define context, annotation loading, view-model, layout, surface, render, and controller seams.
4. Canvas annotation loading reuses v0.2 contracts and has no direct SQLite/Zotero reads or new Python subprocess API.
5. `main.js` remains a thin runtime integration point with parity/runtime coverage if imports require temporary inlining.

**Plans:** 2 plans

- [x] `ANN10-01-PLAN.md` - Canvas contract modules and pure tests (Wave 1).
- [x] `ANN10-02-PLAN.md` - Runtime ItemView, command/button wiring, shell styling, and final gate (Wave 2, depends on Wave 1).

### Phase ANN11: Annotation Card View-Models and Layout

**Goal:** Turn existing annotation state into safe, deterministic side-lane cards.

**Depends on:** Phase ANN10

**Requirements:** CANVAS-03, CANVAS-04, CARD-01, CARD-02, CARD-03, CARD-04

**Success Criteria:**

1. Card view-models display selected text, comment, page, color/type, source, attachment/provenance, and read-only status.
2. Long, missing, and CJK-heavy text/comment values remain readable without overlapping card controls or resizing the canvas unexpectedly.
3. Lane assignment is deterministic by reading/source order and does not depend on random or persisted layout state.
4. Loaded, empty, missing paper, missing DB, missing source, command failure, refresh, and stale-result states are represented explicitly.
5. No card interaction exposes create, edit, delete, save, import, apply, or write-back controls.

**Plans:** 2 plans

- [x] `ANN11-01-PLAN.md` - Card view-models and deterministic layout pure contracts (Wave 1).
- [x] `ANN11-02-PLAN.md` - Card lane DOM, CSS resilience, i18n, and guarded runtime gate (Wave 2, depends on ANN10-02 and ANN11-01).

### Phase ANN12: Controlled Reading Surface and Source Anchors

**Goal:** Provide a PaperForge-owned central reading surface where source grounding can be measured and tested.

**Depends on:** Phase ANN11

**Requirements:** ANCHOR-01, ANCHOR-02

**Success Criteria:**

1. The central surface renders available source text/page content inside the PaperForge canvas, with clear fallback copy when exact source content is unavailable.
2. Supported annotations render source anchors from PaperForge-owned position, text, or page data.
3. Exact text anchors appear only when matching is unambiguous; otherwise the canvas uses page-level or unresolved fallback anchors.
4. Anchor rendering uses safe text insertion and namespaced classes.
5. The implementation avoids native PDF DOM selectors and treats any future PDF-aware surface as a separate hidden seam.

**Plans:** 2 plans

- [x] `ANN12-01-PLAN.md` — Pure source surface and anchor resolver contracts (completed 2026-07-06).
- [ ] `ANN12-02-PLAN.md` — Central source DOM rendering and anchor visual states.

### Phase ANN13: Bidirectional Navigation and Fallback Paths

**Goal:** Make the canvas useful for reading by letting users move between annotation cards and grounded source positions.

**Depends on:** Phase ANN12

**Requirements:** NAV-01, NAV-02, NAV-03

**Success Criteria:**

1. Selecting a card focuses or scrolls to its supported source anchor.
2. Selecting a source anchor focuses the corresponding card.
3. Unsupported or unresolved source navigation presents a safe explanation and can fall back to v0.2 PDF page navigation when a source PDF is available.
4. Selection state clears correctly on paper change, refresh, stale load, and teardown.
5. Keyboard focus order and basic accessibility states work for cards, anchors, and fallback actions.

**Plans:** TBD during phase planning.

### Phase ANN14: Focused Connector Layer and Visual Polish

**Goal:** Add the visual relationship layer from the target UI without overstating evidence precision.

**Depends on:** Phase ANN13

**Requirements:** CANVAS-05, CONN-01, CONN-02, CONN-03

**Success Criteria:**

1. SVG connector lines appear only for selected or hovered card-anchor pairs with confirmed PaperForge-owned geometry.
2. Connectors are hidden for page-only, unresolved, stale, offscreen-unmeasured, or unsupported anchors.
3. Connector geometry updates or clears on scroll, resize, refresh, paper change, and teardown.
4. The canvas remains visually scan-friendly across desktop-sized panes with a dark, restrained reading UI aligned to the reference direction.
5. v0.2 annotation list, page jump, and overlay/fallback paths remain available and unregressed.

**Plans:** TBD during phase planning.

### Phase ANN15: Canvas Verification Gate and Live Harness Record

**Goal:** Verify the full read-only canvas and document exactly what confidence exists in automated tests versus live Obsidian behavior.

**Depends on:** Phase ANN14

**Requirements:** SAFE-01, SAFE-02, SAFE-03, SAFE-04, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05

**Success Criteria:**

1. Canvas helper/controller tests cover loaded, empty, missing, unsupported, command-failure, refresh, stale-result, and teardown states.
2. DOM/runtime tests cover shell rendering, card lane rendering, anchor rendering, selection/focus, fallback actions, connector planning/teardown, and absence of forbidden write controls.
3. Existing v0.2 focused annotation tests still pass.
4. `node --check main.js` passes.
5. A live Obsidian harness note records canvas behavior and explicitly separates v0.3 PaperForge canvas confidence from the still-pending v0.2 native PDF overlay harness if it remains unresolved.

**Plans:** TBD during phase planning.

## Phase Ordering Rationale

1. View registration and data contracts come first because every visual surface depends on explicit paper identity and existing annotation source-of-truth reuse.
2. Cards and lanes come before source anchors/connectors because the visual geometry should be derived from tested view-models.
3. The controlled reading surface comes before connectors because connector claims require owned and measurable anchors.
4. Bidirectional navigation comes before visual connector polish because the core workflow is round-tripping between evidence card and source.
5. Verification is a standalone gate because automated jsdom confidence and live Obsidian pane confidence are different, especially after the v0.2 overlay harness gap.

## Research Flags

- Phase ANN10: Confirm whether shipped Obsidian runtime can require `src/canvas/*` modules directly; otherwise keep temporary inlining debt covered by parity tests.
- Phase ANN12: Re-check source/fulltext shapes if anchor matching needs more than page-level fallback.
- Phase ANN14: Run focused connector geometry review before expanding beyond selected/hovered lines.
- Phase ANN15: Do not skip live Obsidian harness recording.

---
*Roadmap created: 2026-07-03*
*Research basis: .planning/research/SUMMARY.md*
