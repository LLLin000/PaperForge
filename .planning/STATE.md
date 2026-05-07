---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Frontmatter Rationalization & Library-Record Deprecation
status: planning
stopped_at: Roadmap creation complete — Phase 37 ready for `/gsd-plan-phase 37`
last_updated: "2026-05-07T02:06:56.248Z"
last_activity: 2026-05-07
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 2
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Milestone v1.9 — Phase 37 ready to plan

## Current Position

Phase: 37 of 41 (Frontmatter Rationalization)
Plan: None yet
Status: Ready to plan
Last activity: 2026-05-07

Progress: [░░░░░░░░░░] 0% (0/5 phases complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 42 (across v1.0-v1.8)
- Average duration: Not yet tracked consistently

**Recent Trend:**

- Last milestone (v1.7): 4 phases, 6 plans, ~3 days
- Current milestone: 5 phases planned, TBD plans

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 37 (FM):** Frontmatter must slim first — everything else depends on knowing the final frontmatter field list. Workspace path fields and OCR infra fields move to paper-meta.json; formal notes only carry identity + workflow flags + pdf_path.
- **Phase 38 (WS):** Workspace creation and fulltext bridging are path-construction fixes independent of the UI surface. Can follow immediately after FM since the data shape is settled.
- **Phase 39 (BASE):** Base views depend on Phase 37 — they need to know which fields exist in frontmatter before declaring properties. Folder filter repoints from LiteratureControl/ to Literature/.
- **Phase 40 (LRD):** Library-record removal depends on Base views pointing to Literature/ first — removing library-records before Base views are fixed breaks the workflow surface.
- **Phase 41 (PLG):** Plugin verification comes last because it reads from the canonical index produced by FM+WS. Version badge fix (PLG-04) and lifecycle key alignment (PLG-05) are technically independent but grouped for cohesive verification.

### Pending Todos

None yet.

### Blockers/Concerns

- **v1.8 partial state:** Phases 34-35 completed on the feature branch; Phases 31-33, 36 incomplete. v1.9 structural cleanup must not regress the v1.8 deliverables (deep-reading mode detection, dashboard rendering, Jump to Deep Reading button, AI discussion recorder).
- **Feature branch divergence:** The milestone/v1.6-ai-ready-asset-foundation branch has 117 commits. v1.9 work must reconcile against master.
- **Reference vault ground truth:** Plugin dashboard behavior in `D:\L\Med\Research_LitControl_Sandbox` is authoritative — deviations in the current branch must be intentional and documented, not accidental regressions.
- **fulltext_path gap:** Workspace entries declare the path but no existing code copies OCR output there — this is a known hole that WS-02 must fill.
- **Legacy upgrade path:** Users with old flat notes need lossless migration of both frontmatter (LRD-02) and workspace structure (WS-04).

## Session Continuity

Last session: 2026-05-07 00:19
Stopped at: Roadmap creation complete — Phase 37 ready for `/gsd-plan-phase 37`
Resume file: None
