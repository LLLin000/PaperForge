---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: AI-Ready Literature Asset Foundation
status: Phase complete — ready for verification
stopped_at: Completed 26-03-PLAN.md
last_updated: "2026-05-04T04:52:03.084Z"
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 15
  completed_plans: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-03)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Phase 23 — canonical-asset-index-safe-rebuilds

## Current Position

Phase: 23 (canonical-asset-index-safe-rebuilds) — EXECUTING
Plan: 3 of 3

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
| Phase 23-canonical-asset-index-safe-rebuilds P02 | 5 min | 3 tasks | 4 files |
| Phase 23-canonical-asset-index-safe-rebuilds P03 | 8 min | 4 tasks | 5 files |
| Phase 24-derived-lifecycle-health-maturity P02 | 25min | 3 tasks | 2 files |
| Phase 25-surface-convergence-doctor-repair P02 | 2min | 2 tasks | 1 files |
| Phase 25-surface-convergence-doctor-repair P01 | 5 min | 3 tasks | 4 files |
| Phase 25-surface-convergence-doctor-repair P03 | 13min | 2 tasks | 5 files |
| Phase 26-traceable-ai-context-packs P02 | 60 min | 3 tasks | 5 files |
| Phase 26-traceable-ai-context-packs P01 | 4 min | 2 tasks | 3 files |
| Phase 26-traceable-ai-context-packs P03 | 2 min | 3 tasks | 1 files |

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
- [Phase 23-canonical-asset-index-safe-rebuilds]: OCR captures done keys before queue filter to pass to incremental refresh; deep-reading refreshes ALL records; repair triggers refresh for path and divergence fixes; run_index_refresh keeps full-rebuild default; incremental is opt-in from single-paper workers
- [Phase 24-derived-lifecycle-health-maturity]: Lazy import of asset_state functions inside _build_entry() follows existing pattern — avoids circular dependency risk with sync.py — Same pattern already used for ocr.py and sync.py imports in _build_entry()
- [Phase 24-derived-lifecycle-health-maturity]: Derived fields inserted after entry dict construction but before formal note write — keeps machine-only fields out of user-visible Obsidian note frontmatter — Lifecycle/health/maturity/next_step are machine-derived and should not appear in user-editable markdown frontmatter
- [Phase 25-surface-convergence-doctor-repair]: Plugin dashboard reads formal-library.json directly via readFileSync instead of spawning Python CLI — SURF-03 per D-05, D-06, D-07: plugin consumes same canonical semantics from canonical index
- [Phase 25-surface-convergence-doctor-repair]: Use English column display names (Lifecycle, Maturity, Next Step) in Base view properties — The agent's discretion — Base is a technical view, English labels suffice
- [Phase 25-surface-convergence-doctor-repair]: Double-quote YAML wrapping for filters containing single-quoted lifecycle values — Prevents YAML parse errors when filter values contain single quotes like lifecycle = 'fulltext_ready'
- [Phase 25-surface-convergence-doctor-repair]: Lazy import build_index inside fix conditional block to avoid circular dependency with asset_index — Follows existing lazy import pattern established in Phase 23
- [Phase 26-traceable-ai-context-packs]: context command wraps canonical index entries with _provenance (9 path keys) and _ai_readiness (blocking explanation) — D-01, D-06, D-09, D-10
- [Phase 26-traceable-ai-context-packs]: Migration runs before build_index() — ensures _build_entry sees workspace dir
- [Phase 26-traceable-ai-context-packs]: Collection context defaults to --all filter (no Base view filter reading yet in initial implementation)
- [Phase 26-traceable-ai-context-packs]: Context actions use variable timeout: 30s for single paper, 60s for collection, 600s for existing sync/ocr/doctor/repair

### Pending Todos

None yet.

### Blockers/Concerns

- Brownfield rollout must protect existing vaults, old Base templates, partial OCR assets, and legacy config shapes.
- AI context entry points should ship only after provenance and readiness are trustworthy.

## Session Continuity

Last session: 2026-05-04T04:52:03.081Z
Stopped at: Completed 26-03-PLAN.md
Resume file: None
