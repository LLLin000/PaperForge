# Roadmap: PaperForge

**Current milestone:** v1.7 — Planned
**Phase numbering:** Continuous. v1.6 ended at Phase 26.

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-23)
- ✅ **v1.1 Sandbox Onboarding** — Phases 6-8 (shipped 2026-04-24)
- ✅ **v1.2 Systematization & Cohesion** — Phases 9-10 (shipped 2026-04-24)
- ✅ **v1.3 Path Normalization & Architecture Hardening** — Phases 11-12 (shipped 2026-04-24)
- ✅ **v1.4 Code Health & UX Hardening** — Phases 13-19 (shipped 2026-04-28)
- ✅ **v1.5 Obsidian Plugin Setup Integration** — Phases 20-21 (shipped 2026-04-29)
- ✅ **v1.6 AI-Ready Literature Asset Foundation** — Phases 22-26 (shipped 2026-05-04)
- 📋 **v1.7 Context-Aware Dashboard** — Phases 27-30 (planned)

*Archive: `.planning/milestones/v1.6-ROADMAP.md`*

---

## Phases

<details>
<summary>✅ v1.6 AI-Ready Literature Asset Foundation (Phases 22-26) — SHIPPED 2026-05-04</summary>

- [x] Phase 22: Configuration Truth & Compatibility (3/3 plans) — completed 2026-05-03
- [x] Phase 23: Canonical Asset Index & Safe Rebuilds (3/3 plans) — completed 2026-05-03
- [x] Phase 24: Derived Lifecycle, Health & Maturity (2/2 plans) — completed 2026-05-04
- [x] Phase 25: Surface Convergence, Doctor & Repair (3/3 plans) — completed 2026-05-04
- [x] Phase 26: Traceable AI Context Packs (3/3 plans) — completed 2026-05-04

</details>

### 📋 v1.7 Context-Aware Dashboard (Planned)

**Milestone Goal:** Make PaperForge's plugin dashboard context-aware—showing different views based on the active file (Base, paper card, or global). Uses pure CSS/DOM components: metric cards, lifecycle stepper, health matrix, maturity gauge, bar charts.

- [x] **Phase 27: Component Library** — Pure CSS/DOM visualization building blocks using Obsidian design tokens (2 plans planned)
- [ ] **Phase 28: Dashboard Shell & Context Detection** — Auto-detect active file type and switch to correct dashboard mode
- [ ] **Phase 29: Per-Paper View** — Lifecycle stepper, health matrix, maturity gauge, and next-step guidance for individual papers
- [ ] **Phase 30: Collection View** — Domain-level lifecycle/health aggregation for Base files

---

## Phase Details

### Phase 27: Component Library
**Goal**: All dashboard visualizations render as pure CSS/DOM components using Obsidian CSS variables, with no npm dependencies.
**Depends on**: Phase 26 (canonical index exists, dashboard ItemView exists)
**Requirements**: COMP-01, COMP-02, COMP-03
**Success Criteria** (what must be TRUE):
   1. Metric card component renders key counts (papers, domains, formal notes) using Obsidian CSS variables, adapts to light/dark theme, and shows a loading skeleton while data is pending.
   2. Lifecycle stepper component renders stage markers (imported → fulltext_ready → deep_read_done → ai_context_ready) with the current stage highlighted and completed stages visually marked, responsive across sidebar and full-width breakpoints.
   3. Health matrix component renders a 4-dimension grid (PDF, OCR, Note, Asset) with color-coded cells (green/yellow/red) and dimension labels visible at all breakpoint sizes.
   4. Maturity gauge renders as a segmented progress bar (levels 1-6) with level labels on hover/tap and blocking checks listed when level is below 6.
   5. Bar chart component renders lifecycle distribution from numeric category data as horizontal CSS bars with proportional widths, category labels, and smooth CSS transitions on data change.
**Plans**: 2 plans
Plans:
- [x] 27-01-PLAN.md — Component CSS: all 5 components' styling in styles.css (loading skeleton, enhanced metric card, lifecycle stepper, health matrix, maturity gauge, bar chart)
- [x] 27-02-PLAN.md — Component JS: all 5 render methods on PaperForgeStatusView (skeleton utility, enhanced _renderStats, lifecycle stepper, health matrix, maturity gauge, bar chart)
**UI hint**: yes

### Phase 28: Dashboard Shell & Context Detection
**Goal**: Dashboard auto-detects the active file type and switches to the correct view mode (per-paper, collection, or global) without manual intervention, and auto-refreshes when the canonical index or active file changes.
**Depends on**: Phase 27 (components must exist to render into each mode)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, REFR-01, REFR-02
**Success Criteria** (what must be TRUE):
   1. User opens a `.base` file → dashboard header shows the domain name and the view switches to collection mode, without any manual button click.
   2. User opens a paper card (`.md` with `zotero_key` in frontmatter) → dashboard header shows the paper title and the view switches to per-paper mode, without any manual button click.
   3. User opens any other file or no file → dashboard shows the existing global library overview (metric cards, OCR pipeline, Quick Actions).
   4. User switches active file via tab click or Ctrl+Tab → dashboard transitions to the correct mode within observable time (< 500ms), with the previous mode's data released from memory.
   5. When `formal-library.json` is modified externally (by sync/ocr/repair workers) → dashboard detects the change within 2 seconds and refreshes the current view with updated data, preserving the current mode.
**Plans**: 2 plans
Plans:
- [x] 28-01-PLAN.md — Index utilities (load/cache/lookup) + CSS for mode-aware shell
- [ ] 28-02-PLAN.md — Context detection, mode switching, event subscriptions, auto-refresh, mode-aware header
**UI hint**: yes

### Phase 29: Per-Paper View
**Goal**: User can see the full lifecycle, health, maturity, and next-step guidance for any individual paper by opening its note and viewing the PaperForge dashboard.
**Depends on**: Phase 28 (context detection must route to per-paper mode)
**Requirements**: PAPER-01, PAPER-02, PAPER-03, PAPER-04
**Success Criteria** (what must be TRUE):
  1. Lifecycle stepper shows the paper's current lifecycle stage highlighted (e.g., `fulltext_ready`), all earlier stages marked as completed, and later stages dimmed as pending — stage names use human-readable labels (e.g., "Fulltext Ready" not "fulltext_ready").
  2. Health matrix shows four color-coded cells for this paper: PDF health (present/missing), OCR health (done/pending/failed), Note health (formal note exists/absent), and Asset health (all paths valid/drift detected) — hovering any cell shows the specific check that determined its color.
  3. Maturity gauge shows the current level (1-6) as filled segments with the numeric level displayed, and below the gauge lists which checks are currently blocking advancement to the next level.
  4. Next-step panel recommends exactly one concrete action with a one-line explanation of why (e.g., "Run OCR — fulltext is missing but PDF is present"). If the paper is already ai_context_ready, the panel shows "Ready" with no action needed.
  5. Next-step panel includes a clickable action trigger that either executes the recommended CLI command (sync/ocr) via the existing action runner, or copies the zotero_key for `/pf-deep`, or confirms readiness with a "Copy Context" shortcut.
**Plans**: TBD
**UI hint**: yes

### Phase 30: Collection View
**Goal**: User can see aggregated domain-level lifecycle and health statistics when viewing any Base file in the PaperForge dashboard.
**Depends on**: Phase 28 (context detection must route to collection mode)
**Requirements**: COLL-01, COLL-02, COLL-03
**Success Criteria** (what must be TRUE):
  1. User opens a domain Base file (e.g., "骨科" or "运动医学") → dashboard shows that domain's paper count and lifecycle distribution numbers sourced from the canonical index.
  2. Aggregated health summary shows four dimension counts (PDF healthy/broken, OCR done/pending/failed, Note present/absent, Asset valid/drifted) aggregated across all papers in the domain, with counts visibly updating when switching to a different domain Base.
  3. Lifecycle distribution bar chart renders the domain's papers across lifecycle stages (imported, indexed, pdf_ready, fulltext_ready, figure_ready, deep_read_done, ai_context_ready) as proportional horizontal bars with count labels, using the bar chart component from Phase 27.
  4. Collection view updates automatically when the canonical index changes and when the user switches between different domain `.base` files, preserving the collection mode throughout.
**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 22. Configuration Truth & Compatibility | v1.6 | 3/3 | Complete | 2026-05-03 |
| 23. Canonical Asset Index & Safe Rebuilds | v1.6 | 3/3 | Complete | 2026-05-03 |
| 24. Derived Lifecycle, Health & Maturity | v1.6 | 2/2 | Complete | 2026-05-04 |
| 25. Surface Convergence, Doctor & Repair | v1.6 | 3/3 | Complete | 2026-05-04 |
| 26. Traceable AI Context Packs | v1.6 | 3/3 | Complete | 2026-05-04 |
| 27. Component Library | v1.7 | 2/2 | Complete   | 2026-05-04 |
| 28. Dashboard Shell & Context Detection | v1.7 | 1/2 | In Progress|  |
| 29. Per-Paper View | v1.7 | 0/TBD | Not started | - |
| 30. Collection View | v1.7 | 0/TBD | Not started | - |

---

*Roadmap updated: 2026-05-04 — v1.7 Context-Aware Dashboard initialized*
