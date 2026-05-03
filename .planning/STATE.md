---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: AI-Ready Literature Asset Foundation
status: Ready to execute
stopped_at: Completed 23-01-PLAN.md
last_updated: "2026-05-03T16:37:51.602Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 7
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-03)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Phase 23 — canonical-asset-index-safe-rebuilds

## Current Position

Phase: 23 (canonical-asset-index-safe-rebuilds) — EXECUTING
Plan: 2 of 3

## Performance Metrics

**Velocity:**

- Total plans completed: 41
- Average duration: Not yet tracked consistently
- Total execution time: Not yet tracked consistently

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 20. Plugin Settings Shell & Persistence | 1/1 | Not tracked | Not tracked |
| 21. One-Click Install & Polished UX | 2/2 | Not tracked | Not tracked |
| 22-26. v1.6 roadmap | 0/TBD | - | - |

**Recent Trend:**

- Last 5 plans: Not normalized in historical records
- Trend: Stable

| Phase 22-configuration-truth-compatibility P01 | 4 min | 3 tasks | 3 files |
| Phase 22-configuration-truth-compatibility P02 | 6 min | 3 tasks | 1 files |
| Phase 22-configuration-truth-compatibility P03 | 8 min | 3 tasks | 3 files |
| Phase 23-canonical-asset-index-safe-rebuilds P01 | 7 min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v1.6 stays Python-first: config, lifecycle, health, maturity, and context-pack rules remain Python-owned.
- `formal-library.json` evolves into the canonical derived asset index rather than introducing a parallel index.
- Plugin remains a thin shell over CLI logic and canonical index outputs.
- [Phase 22-configuration-truth-compatibility]: schema_version is metadata excluded from load_vault_config() path config output; use get_paperforge_schema_version() instead
- [Phase 22-configuration-truth-compatibility]: Added paddleocr_api_key and zotero_data_dir to DEFAULT_SETTINGS to prevent data loss from saveSettings() key filtering — Plan omitted these keys from DEFAULT_SETTINGS, but saveSettings() now filters persisted keys to only DEFAULT_SETTINGS entries - would have permanently deleted user API keys and Zotero paths
- [Phase 22-configuration-truth-compatibility]: Clean dict replace replaces existing_config.update() to avoid accumulating stale top-level keys in setup wizard paperforge.json output
- [Phase 23-canonical-asset-index-safe-rebuilds]: Lazy imports inside build_index avoid circular import between sync.py and asset_index.py
- [Phase 23-canonical-asset-index-safe-rebuilds]: Orphaned-record cleanup stays in sync.py; only the core build loop moves to asset_index

### Pending Todos

None yet.

### Blockers/Concerns

- Brownfield rollout must protect existing vaults, old Base templates, partial OCR assets, and legacy config shapes.
- AI context entry points should ship only after provenance and readiness are trustworthy.

## Session Continuity

Last session: 2026-05-03T16:37:42.753Z
Stopped at: Completed 23-01-PLAN.md
Resume file: None
