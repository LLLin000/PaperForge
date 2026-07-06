# Requirements: PaperForge annotation v0.3 Visual Reading Canvas

**Defined:** 2026-07-03
**Core Value:** Researchers can read a paper in a PaperForge-controlled visual canvas where annotations remain visibly grounded to their source text/page without adding editing or write-back risk.

## v0.3 Requirements

annotation v0.3 builds on the v0.2 Obsidian annotation bridge, list, navigation, and risk-gated overlay work. The milestone creates a read-only Visual Reading Canvas: central reading content, side annotation cards, source anchors, bidirectional focus, and a guarded connector foundation.

The milestone continues after Annotation Phase 9, so the roadmap starts at Annotation Phase 10.

### Canvas Shell (CANVAS)

- [ ] **CANVAS-01**: User can open a PaperForge Reading Canvas for an explicit active paper from the plugin UI or command palette.
- [ ] **CANVAS-02**: The canvas loads paper-scoped annotations through existing v0.2 contracts rather than direct database reads or new subprocess APIs.
- [ ] **CANVAS-03**: The canvas presents a central PaperForge-owned reading surface with left/right annotation card lanes.
- [ ] **CANVAS-04**: The canvas handles missing paper identity, missing annotation database, empty annotations, missing source content, unsupported anchoring, stale loads, and command failures without crashing.
- [ ] **CANVAS-05**: The existing v0.2 annotation list, PDF page jump, and overlay/fallback paths remain available when the canvas cannot provide a supported state.

### Annotation Cards (CARD)

- [ ] **CARD-01**: Cards display selected text, comment, page, color/type, source, attachment/provenance, and read-only status.
- [ ] **CARD-02**: Cards handle long, missing, or CJK-heavy selected text/comment content without broken layout or overlapping controls.
- [ ] **CARD-03**: Cards use deterministic reading-order placement into left/right lanes.
- [ ] **CARD-04**: Card models preserve enough source identity for later evidence workflows without exposing edit/write-back controls.

### Source Anchors and Navigation (ANCHOR/NAV)

- [x] **ANCHOR-01**: Source anchors render for annotations with supported PaperForge-owned position, text, or page data.
- [x] **ANCHOR-02**: Page-level or unresolved fallback anchors render when exact text/geometry anchoring is unavailable.
- [ ] **NAV-01**: Selecting a card focuses or scrolls to the corresponding source anchor when supported.
- [ ] **NAV-02**: Selecting a source anchor focuses the corresponding card.
- [ ] **NAV-03**: Unsupported canvas navigation can fall back to the existing v0.2 PDF page navigation path.

### Connector Foundation (CONN)

- [ ] **CONN-01**: Focused connector lines link selected or hovered cards to confirmed PaperForge-owned source anchors.
- [ ] **CONN-02**: Connectors are hidden for page-only, unresolved, stale, or unmeasured anchors so the UI does not imply stronger grounding than the data supports.
- [ ] **CONN-03**: Connectors update or disappear correctly on scroll, resize, refresh, teardown, and paper changes.

### Safety and Scope (SAFE)

- [ ] **SAFE-01**: v0.3 remains read-only for Zotero-sourced annotations and exposes no create, edit, delete, save, import, apply, or write-back controls inside the canvas.
- [ ] **SAFE-02**: Canvas display code does not mutate `annotations.db`, Zotero data, vault notes, Obsidian Canvas files, plugin settings, localStorage, or persistent layout state.
- [ ] **SAFE-03**: Canvas logic does not depend on native Obsidian PDF viewer internals as its foundation.
- [ ] **SAFE-04**: v0.3 verification explicitly distinguishes PaperForge canvas confidence from the pending v0.2 live native-PDF overlay harness.

### Verification (TEST)

- [ ] **TEST-01**: Tests cover canvas context and annotation loading states: loaded, empty, missing paper, missing database, missing source, command failure, stale result, refresh, and teardown.
- [ ] **TEST-02**: Tests cover card view-models, lane placement, source anchors, fallback anchors, and connector planning with representative annotation data.
- [ ] **TEST-03**: DOM/runtime tests cover canvas rendering, card/source focus, unsupported fallbacks, connector teardown, and absence of forbidden write controls.
- [ ] **TEST-04**: The existing annotation v0.2 focused test gate still passes after each v0.3 canvas phase.
- [ ] **TEST-05**: Final verification includes a live Obsidian canvas harness note and records whether native PDF overlay behavior remains pending.

## Future Requirements

### Local Annotation Editing

- **EDIT-01**: User can create a local PaperForge annotation from a source surface.
- **EDIT-02**: User can edit or delete local PaperForge annotations without modifying Zotero annotations.
- **EDIT-03**: User can review conflicts between local annotations and imported Zotero annotations.

### Evidence and AI Integration

- **EVID-01**: User can link an annotation/card as an evidence anchor from deep-reading output.
- **EVID-02**: Concept-card preview/apply can cite annotation anchors as source evidence.
- **AI-01**: User can generate AI summaries, clusters, or question cards that remain traceable to annotation anchors.

### Rich Canvas Workflows

- **LAYOUT-01**: User can drag cards into a persistent layout after a write-safety design exists.
- **LAYOUT-02**: User can build multi-paper boards for literature review synthesis.
- **MEDIA-01**: Figure, table, image, audio, and video evidence cards can appear beside text annotations.
- **MOBILE-01**: Touch/mobile layouts are supported after the desktop canvas proves stable.

### Zotero Write-Back

- **PUSH-01**: User can push selected PaperForge local annotations back to Zotero through a safe API-backed path.
- **PUSH-02**: User can review conflicts before write-back.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct Zotero SQLite mutation | Unsafe; Zotero remains an external source of truth. |
| Zotero Web API write-back | Requires credentials, versioning, conflict handling, and a separate safety design. |
| Local annotation creation/editing/deletion | v0.3 focuses on visual read-only grounding; editing belongs after display and safety are stable. |
| Obsidian `.canvas` file persistence | MVP should not create persistent user-authored canvas state. |
| Generic Obsidian Canvas clone | The target is a paper-grounded reading canvas, not a freeform graph editor. |
| New React/Svelte/Vue build system | Existing CommonJS Obsidian plugin stack is sufficient for the MVP. |
| D3/Cytoscape/physics graph layout | Focused connectors and deterministic lanes avoid unnecessary dependency and performance risk. |
| Full bundled PDF.js renderer | The canvas should first prove PaperForge-owned text/page grounding before adding renderer complexity. |
| Always-on connector web | Too noisy and can imply unsupported evidence strength. v0.3 uses focused connectors only. |
| Native PDF viewer DOM dependency as foundation | Obsidian PDF internals are risk-gated and already pending live harness verification from v0.2. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CANVAS-01 | Annotation Phase 10 | Planned |
| CANVAS-02 | Annotation Phase 10 | Planned |
| CANVAS-03 | Annotation Phase 11 | Planned |
| CANVAS-04 | Annotation Phase 11 | Planned |
| CANVAS-05 | Annotation Phase 14 | Planned |
| CARD-01 | Annotation Phase 11 | Planned |
| CARD-02 | Annotation Phase 11 | Planned |
| CARD-03 | Annotation Phase 11 | Planned |
| CARD-04 | Annotation Phase 11 | Planned |
| ANCHOR-01 | Annotation Phase 12 | Done |
| ANCHOR-02 | Annotation Phase 12 | Done |
| NAV-01 | Annotation Phase 13 | Planned |
| NAV-02 | Annotation Phase 13 | Planned |
| NAV-03 | Annotation Phase 13 | Planned |
| CONN-01 | Annotation Phase 14 | Planned |
| CONN-02 | Annotation Phase 14 | Planned |
| CONN-03 | Annotation Phase 14 | Planned |
| SAFE-01 | Annotation Phase 15 | Planned |
| SAFE-02 | Annotation Phase 15 | Planned |
| SAFE-03 | Annotation Phase 15 | Planned |
| SAFE-04 | Annotation Phase 15 | Planned |
| TEST-01 | Annotation Phase 15 | Planned |
| TEST-02 | Annotation Phase 15 | Planned |
| TEST-03 | Annotation Phase 15 | Planned |
| TEST-04 | Annotation Phase 15 | Planned |
| TEST-05 | Annotation Phase 15 | Planned |

---
*Requirements defined: 2026-07-03*
*Research basis: .planning/research/SUMMARY.md*
