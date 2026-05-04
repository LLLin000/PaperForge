# Requirements: PaperForge

**Defined:** 2026-05-04
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v1 Requirements

Requirements for milestone v1.7: Context-Aware Dashboard.

### Context Detection

- [x] **DASH-01**: User opens a `.base` file — plugin dashboard shows collection-level domain statistics.
- [x] **DASH-02**: User opens a paper card (`.md` with `zotero_key` in frontmatter) — plugin dashboard shows per-paper lifecycle, health, maturity, and next-step.
- [ ] **DASH-03**: User opens any other file or no file — plugin dashboard shows the existing global library overview.
- [ ] **DASH-04**: User switches active file — dashboard auto-refreshes to the correct mode without manual intervention.

### Per-Paper Dashboard

- [ ] **PAPER-01**: User sees a lifecycle stepper showing the current state and which stages are complete.
- [ ] **PAPER-02**: User sees a health matrix (PDF/OCR/Note/Asset dimensions) with color-coded status.
- [ ] **PAPER-03**: User sees maturity level (1-6) as a segmented progress bar with blocking checks listed.
- [ ] **PAPER-04**: User sees a recommended next step (sync/ocr/pf-deep/ready) with an action trigger.

### Collection Dashboard

- [ ] **COLL-01**: User sees domain-level paper count and lifecycle distribution from canonical index.
- [ ] **COLL-02**: User sees aggregated health overview for the domain (PDF/OCR/Note/Asset counts).
- [ ] **COLL-03**: User sees a lifecycle distribution bar chart for the domain.

### Component Library

- [x] **COMP-01**: All dashboard visualizations use pure CSS/DOM (metric cards, lifecycle stepper, health matrix, maturity gauge, bar charts). No npm dependencies.
- [x] **COMP-02**: Components use Obsidian CSS variables for consistent theming.
- [x] **COMP-03**: Components have loading states, CSS transitions, and responsive breakpoints.

### Auto-Refresh

- [x] **REFR-01**: Dashboard refreshes when the canonical index file changes.
- [ ] **REFR-02**: Dashboard refreshes when the active file changes.

## v2 Requirements

Deferred to future milestone.

### LLMWiki

- **LLM-01**: User can explore a cross-paper concept network built from AI atoms and canonical index entries.
- **LLM-02**: User can navigate concept pages with source traceability back to originating papers.

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLMWiki concept network | v1.8 — depends on dashboard being stable first |
| External chart libraries (Chart.js, D3) | Pure CSS/DOM keeps plugin self-contained |
| Plugin auto-update | Deferred to Obsidian Community Plugins listing |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-01 | Phase 27 | Complete |
| COMP-02 | Phase 27 | Complete |
| COMP-03 | Phase 27 | Complete |
| DASH-01 | Phase 28 | Complete |
| DASH-02 | Phase 28 | Complete |
| DASH-03 | Phase 28 | Pending |
| DASH-04 | Phase 28 | Pending |
| REFR-01 | Phase 28 | Complete |
| REFR-02 | Phase 28 | Pending |
| PAPER-01 | Phase 29 | Pending |
| PAPER-02 | Phase 29 | Pending |
| PAPER-03 | Phase 29 | Pending |
| PAPER-04 | Phase 29 | Pending |
| COLL-01 | Phase 30 | Pending |
| COLL-02 | Phase 30 | Pending |
| COLL-03 | Phase 30 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 after v1.7 requirements definition*
