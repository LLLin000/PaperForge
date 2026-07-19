---
phase: 18-documentation-ux-polish
plan: 02
type: execute
subsystem: documentation
tags: [v1.4, migration, adr, agents, chart-index, README, roadmap]
dependency-graph:
  requires: [Phase 17]
  provides: [docs/MIGRATION-v1.4.md, ADR-012, ADR-013, chart-reading/INDEX.md]
  affects: [AGENTS.md, README.md, ROADMAP.md]
tech-stack:
  added: []
  patterns: [ADR format, migration doc template, chart-reading index]
key-files:
  created:
    - docs/MIGRATION-v1.4.md
    - paperforge/skills/literature-qa/chart-reading/INDEX.md
  modified:
    - docs/ARCHITECTURE.md
    - AGENTS.md
    - README.md
    - .planning/ROADMAP.md
decisions:
  - ADR-012 documents _utils.py leaf module constraint from Phase 14
  - ADR-013 documents dual-output logging strategy from Phase 13
  - AGENTS.md command mapping table follows the v1.2 namespace conventions
  - chart-reading INDEX ordered by biomedical commonness per D-04
metrics:
  duration: TBD
  completed_date: 2026-04-27
---

# Phase 18 Plan 02: Migration, Architecture & Doc Polish Summary

Migration documentation, architecture decision records, AGENTS.md command table, README fix, chart-reading index, and roadmap update for v1.4 release.

**One-liner:** Created MIGRATION-v1.4.md, added ADR-012/013 to ARCHITECTURE.md, updated AGENTS.md with command mapping table and v1.4 features, fixed README orphaned lines, created chart-reading INDEX.md, and updated ROADMAP.md — all while maintaining 203/205 test pass.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create MIGRATION-v1.4.md + fix README orphaned lines | `729ce99` | docs/MIGRATION-v1.4.md, README.md |
| 2 | Add ADR-012/013 to ARCHITECTURE.md + update AGENTS.md | `78bf95b` | docs/ARCHITECTURE.md, AGENTS.md |
| 3 | Create chart-reading INDEX.md + update ROADMAP.md | `4086862` | paperforge/skills/literature-qa/chart-reading/INDEX.md, .planning/ROADMAP.md |

## Implementation Details

### Task 1: MIGRATION-v1.4.md + README Fix

- Created `docs/MIGRATION-v1.4.md` (374 lines) following the v1.2 template structure
- Documented 4 change areas: dual-output logging, retry behavior, pre-commit + Ruff, auto_analyze_after_ocr
- Included breaking changes summary table, detailed sections, migration steps (6 steps), rollback instructions, FAQ, and quick reference card
- Removed orphaned legacy code lines 102-104 from README.md (`python <resolved_worker_script> --vault . ocr/status`)
- Scanned all docs/*.md for rendering issues — none found

### Task 2: ADRs + AGENTS.md Updates

- Added ADR-012 (Shared Utilities Extraction / `_utils.py` leaf module) after ADR-011
- Added ADR-013 (Dual-Output Logging Strategy) after ADR-012
- Both follow existing ADR format (Status, Phase, Context, Decision, Consequences)
- Inserted "操作速查" command mapping table in AGENTS.md Section 1 after the bullet list (7 rows)
- Added `--verbose` flag note and `auto_analyze_after_ocr` note to Section 5
- Added `--verbose` variants to all CLI examples in Section 8 (sync, sync --selection, sync --index, ocr)
- Added `--no-progress` flag to OCR example in Section 8
- Added "Chart-Reading 指南索引" cross-reference in Section 8
- Updated Section 11 migration section with v1.4 feature summary and dual migration links

### Task 3: INDEX.md + ROADMAP.md

- Created `chart-reading/INDEX.md` listing all 19 guides in biomedical commonness order
- Each row includes: number, chart type name, description of handled chart types, and Obsidian wikilink to guide file
- Ordered per D-04 with remaining files appended in logical groups (histology, immunofluorescence, micrograph, Western blot, protein structure)
- Updated ROADMAP.md: Phase 18 details now show "2 plans (1 wave)" with plan list, 18-01 marked complete
- Progress table updated to "2/1 | In progress"

## Verification

| Check | Result |
|-------|--------|
| `docs/MIGRATION-v1.4.md` exists and has content | PASS |
| `ADR-012` in `docs/ARCHITECTURE.md` | PASS |
| `ADR-013` in `docs/ARCHITECTURE.md` (after ADR-012) | PASS |
| `AGENTS.md` has `/pf-sync` command mapping table | PASS |
| `AGENTS.md` references `auto_analyze_after_ocr` | PASS |
| `README.md` orphaned lines removed | PASS |
| `INDEX.md` exists with 21 table rows (header + sep + 19 data) | PASS |
| `ROADMAP.md` has 18-01-PLAN and 18-02-PLAN | PASS |
| `pytest tests/ -x` — 203 passed, 2 skipped | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All verification checks confirmed:
- Created files: `docs/MIGRATION-v1.4.md`, `paperforge/skills/literature-qa/chart-reading/INDEX.md`
- Modified files: `docs/ARCHITECTURE.md`, `AGENTS.md`, `README.md`, `.planning/ROADMAP.md`
- Commits: `729ce99`, `78bf95b`, `4086862`
- All 203 tests pass (2 skipped, pre-existing)
