---
gsd_state_version: 1.0
milestone: v1.11
milestone_name: Merge Gate — v1.9 Ripple Remediation
status: completed
stopped_at: Completed 47 - Library-Records Deprecation Cleanup
last_updated: "2026-05-07T11:24:40.290Z"
last_activity: 2026-05-07 — Phase 46 executed (PATH-01 through PATH-06)
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 4
  completed_plans: 6
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.
**Current focus:** Phase 46 — Index Path Resolution (config-resolved paths across 5 workspace fields + 11 consumers)

## Current Position

Phase: 46 of 50 (Index Path Resolution) — COMPLETE
Plan: —
Status: Phase 46 complete (2/2 plans)
Last activity: 2026-05-07 — Phase 46 executed (PATH-01 through PATH-06)

Progress: [████████░░] 20%

## Performance Metrics

**Velocity:**

- Total plans completed: 2
- Average duration: 2.5 min
- Total execution time: 0.08 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 46 | 2 | 5 min | 2.5 min |

**Recent Trend:**

- Last 5 plans: N/A
- Trend: N/A (starting)

*Updated after each plan completion*
| Phase 47-library-records-deprecation-cleanup P001-002 | 18min | 4 tasks | 16 files |

## Accumulated Context

### Previous milestones (v1.9-v1.10)

- v1.9 eliminated library-records, created per-workspace paper-meta.json, slimmed formal note frontmatter
- v1.10 fixed cross-cutting dependency drift left by v1.9 (4 phases, all complete)

### v1.11 phase structure (5 phases, 27 requirements)

| Phase | Goal | Reqs |
|-------|------|------|
| 46 - Index Path Resolution | Config-resolved paths across 5 workspace fields + 11 consumers | PATH 01-06 (6) |
| 47 - Library-Records Deprecation Cleanup | Zero residual traces in production code and documentation | LEGACY 01-07 (7) |
| 48 - Textual TUI Removal | Broken Textual TUI removed; headless-only setup workflow | DEPR 01-03 (3) |
| 49 - Module Hardening | Production-grade safety guards in discussion.py, main.js, asset_state.py | HARDEN 01-07 (7) |
| 50 - Repair Blind Spots | All 6 divergence types detected and handled by fix mode | REPAIR 01-04 (4) |

### Diagnosed v1.9 ripple effects (3 remaining)

1. **[FIXED] Index hardcodes "Literature/" path** — resolved by Phase 46 (PATH-01). Config-resolved paths now in all 5 workspace fields.
2. **Library-records deprecation incomplete**: 15 residual traces across 10 .py files + 5 .md command files. (Phase 47 target)
3. **Setup wizard TUI broken and unreachable**: NameError crash at line 662. Both real install paths (plugin settings tab, AI agents) use `--headless`. Textual TUI is dead code — needs removal, not repair. (Phase 48 target)
4. **New modules lack hardening**: discussion.py (no locking/escaping/timezone), main.js (API key exposure/XSS/sync I/O), asset_state.py (broken next_step/null JSON), repair.py (divergence blind spots). (Phase 49 target)

## Session Continuity

Last session: 2026-05-07T11:24:40.286Z
Stopped at: Completed 47 - Library-Records Deprecation Cleanup
Resume file: None
