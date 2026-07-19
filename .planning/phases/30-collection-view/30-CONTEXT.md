# Phase 30: Collection View - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Render collection-level aggregated dashboard when user opens a `.base` file. Uses Phase 27 components and Phase 28 domain filtering.

</domain>

<decisions>
## Implementation Decisions

- **D-01:** `_renderCollectionMode(domain, entries)` — called by Phase 28 `_switchMode('collection')`.
- **D-02:** Header: domain name (from `.base` filename) + total paper count.
- **D-03:** Metric cards row: papers count, fulltext-ready count, deep-read count.
- **D-04:** Lifecycle distribution bar chart via `_renderBarChart(view, counts)`.
- **D-05:** Health overview: aggregate PDF/OCR/Note/Asset health across entries.
- **D-06:** CSS Section 17: collection layout, same patterns as per-paper view.

</decisions>

<canonical_refs>
- `.planning/ROADMAP.md` §Phase 30 — Collection View
- `.planning/REQUIREMENTS.md` — COLL-01..03
- `paperforge/plugin/main.js` — PaperForgeStatusView class

</canonical_refs>

<code_context>
- `_filterByDomain(domain)` — Phase 28
- `_renderStats()` — Phase 27 metric cards
- `_renderBarChart()` — Phase 27 lifecycle bars
- `_renderHealthMatrix()` — Phase 27 health grid
- Phase 29 `_renderPaperMode` pattern

</code_context>

<deferred>
None
</deferred>

---

*Phase: 30-collection-view*
*Context gathered: 2026-05-04*
