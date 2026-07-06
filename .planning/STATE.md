---
gsd_state_version: 1.0
milestone: annotation v0.3
milestone_name: milestone
status: executing
stopped_at: Phase ANN11 complete
last_updated: "2026-07-06T09:17:23.000Z"
last_activity: 2026-07-06 -- Phase ANN11 card lane rendering, CSS, and runtime complete
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-02)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Phase ANN11 — Annotation Card View-Models and Layout (COMPLETE)

## Current Position

Phase: ANN11 (Annotation Card View-Models and Layout) — COMPLETE
Plan: 2 of 2
Status: Phase ANN11 complete — Card view-models, layout, rendering, CSS, i18n, and runtime regression
Last activity: 2026-07-06 -- Phase ANN11 card lane rendering, CSS, and runtime complete

## Performance Metrics

**Velocity:**

- Total plans completed before v0.2: 17
- Total plans planned before v0.2: 18
- v0.2 planned phases: 5
- v0.3 planned phases: 6

**Previous Annotation Milestones:**

| Milestone | Phases | Status | Notes |
|-----------|--------|--------|-------|
| annotation v0.1 | Annotation Phases 1-4 | Complete | Backend/CLI annotation import, storage, and export foundation. |
| annotation v0.2 | Annotation Phases 5-9 | Mostly complete | Automated display-layer gate passed; live Obsidian native PDF overlay harness remains pending. |
| annotation v0.3 | Annotation Phases 10-15 | Planning | Visual Reading Canvas requirements and roadmap defined. |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [annotation v0.1]: Build PDF annotation as a parallel feature line from current upstream/master, not from the stale old branch directly.
- [annotation v0.1]: Import only backend/CLI annotation capabilities first; defer Obsidian PDF overlay to a later annotation milestone.
- [annotation v0.1]: Zotero SQLite is read-only input; PaperForge writes annotation state only to its own `annotations.db`.
- [annotation v0.1]: Paper-scoped imports must not mark unrelated paper annotations as stale/deleted.
- [annotation v0.1]: Annotation CLI commands use a dedicated `paperforge annotation ...` namespace.
- [annotation v0.1]: Annotation import defaults to preview mode; writes require explicit `--apply`.
- [annotation v0.2]: Continue annotation phase numbering after Phase 4; v0.2 starts at Annotation Phase 5.
- [annotation v0.2]: Prioritize Obsidian display/navigation/overlay before local editing or concept-card evidence integration.
- [annotation v0.2]: PDF overlay is risk-gated; the sidebar/list remains the safe fallback.
- [annotation v0.2 Phase 9]: Automated verification gate passed for bridge/list/navigation/overlay-focused tests; live Obsidian native PDF viewer harness remains pending.
- [annotation v0.3]: Build v0.3 as a PaperForge-controlled Visual Reading Canvas instead of a generic Obsidian Canvas clone or native PDF overlay extension.
- [annotation v0.3]: Keep v0.3 MVP read-only: no local annotation editing, Zotero write-back, persistent freeform layout, or AI-generated cards.
- [annotation v0.3]: Use existing Obsidian ItemView/CommonJS/plugin test stack plus plain DOM/SVG; do not add React/Svelte, D3/Cytoscape, PDF.js, Obsidian `.canvas` persistence, or new Python APIs for MVP.
- [annotation v0.3]: Connector lines are evidence claims and must appear only for focused card-anchor pairs with confirmed PaperForge-owned geometry.
- [ANN10-01 executed]: Canvas context resolution uses `entry.key` as authoritative paper identity — no live global `_currentPaperKey` drift.
- [ANN10-01 executed]: Annotation wrapper delegates to v0.2 `loadAnnotationsForPaper` — no new CLI/subprocess/DB contract in `src/canvas/*`.
- [ANN10-01 executed]: Session controller owns fixed paperKey at construction; stale-guard uses monotonic load sequence.
- [ANN10-01 executed]: Shell render dispatch explicitly lists all 10 handled states; default renders idle placeholder for unrecognized states.
- [ANN10-01 executed]: All user-facing canvas text uses `textContent` — verified with XSS payload test.
- [ANN10-01 executed]: Controller test helpers use `makeV02Loader()` + `createCanvasAnnotationLoader` wrapper pattern — avoids raw `{ loadForPaper }` mock bypass.
- [ANN11-02 executed]: Card DOM rendering uses textContent for all annotation-derived fields — verified with XSS payload strings
- [ANN11-02 executed]: Missing selected text and comment values render explicit quiet placeholders with CSS `--empty` modifier classes
- [ANN11-02 executed]: Refreshing state preserves existing visible cards; stale state shows a warning banner alongside stale cards
- [ANN11-02 executed]: CSS uses max-height + overflow: hidden + gradient fade pseudo-element for long text truncation (not line-clamp which has inconsistent CJK support)
- [ANN11-02 executed]: All user-facing canvas text uses scoped i18n zh/en keys via the `t()` helper
- [ANN11-02 executed]: Card lane CSS uses `word-break: break-word` for CJK-safe wrapping in card previews
- [ANN11-02 executed]: Read-only badge uses `--true`/`--false` CSS modifier pattern for style-driven display

### Research Summary

Research files live under `.planning/research/`:

- `FEATURES.md`: table-stakes and deferred Visual Reading Canvas features.
- `PITFALLS.md`: risks around duplicate annotation runtime, helper drift, native PDF internals, read-only safety, stale async loads, and misleading connectors.
- `ARCHITECTURE.md`: PaperForge-owned `ItemView` recommendation and `src/canvas/*` module seams.
- `STACK.md`: stack additions/non-additions and test strategy.
- `SUMMARY.md`: synthesized milestone direction and six-phase roadmap basis.

### Pending Todos

None yet.

### Blockers/Concerns

- **v0.2 live Obsidian native PDF overlay harness pending**: v0.3 can proceed because it does not depend on native PDF internals as the canvas foundation, but final verification must not claim native overlay reliability without the harness.
- ~~**Shipped-source module boundary**: Phase 10 must confirm whether `main.js` can require `src/canvas/*` modules in the Obsidian runtime; if not, temporary inlining requires parity/runtime tests.~~ **RESOLVED**: `node --check main.js` passes and runtime tests using `require('./src/canvas')` prove the full module delegation works. No inlining debt.
- **Fulltext/source anchoring uncertainty**: Phase 12 may need focused research if central fulltext/formal-note source shapes vary more than current docs imply.
- **Connector precision risk**: Phase 14 must hide connectors for page-only, unresolved, stale, or unmeasured anchors.
- **Known baseline failures**: full non-focused test suites may still include unrelated baseline issues; v0.3 verification should keep focused gates explicit.

## Session Continuity

Last session: 2026-07-06T09:17:23.000Z
Stopped at: Phase ANN11 complete
Resume file: .planning/phases/ANN11/ANN11-02-SUMMARY.md
Next phase: Phase ANN12 - Annotation Card Evidence and Connector Rendering

## Next Suggested Command

Begin planning for next phase:

`/gsd-plan-phase ANN12`

---

*Updated: 2026-07-06* — Phase ANN11 complete (both plans executed: view-models/layout + card lane rendering/CSS)
