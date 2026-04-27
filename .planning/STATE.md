---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: milestone
status: In progress
stopped_at: Completed 18-01-PLAN.md (auto_analyze_after_ocr, CHANGELOG, CONTRIBUTING)
last_updated: "2026-04-27T10:01:03.126Z"
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 9
  completed_plans: 8
---

# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-25)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Phase 13 — logging-foundation

## Current Position

Phase: 18
Plans: 18-01 complete, 18-02 ready to execute

## Performance Metrics

**Velocity:**

- Total phases completed (cumulative): 14
- v1.4 phases: 2/7 complete

**By Milestone:**

| Milestone | Phases | Status |
|-----------|--------|--------|
| v1.0 MVP | 1-5 | Shipped 2026-04-23 |
| v1.1 Sandbox | 6-8 | Shipped 2026-04-24 |
| v1.2 Systematization | 9-10 | Shipped 2026-04-24 |
| v1.3 Architecture | 11-12 | Shipped 2026-04-24 |
| v1.4 Code Health | 13-19 | In progress |

*Updated after each plan completion*
| Phase 13-logging-foundation P01 | 18min | 2 tasks | 2 files |
| Phase 13-logging-foundation P02 | 12min | 2 tasks | 12 files |
| Phase 13-logging-foundation P03 | 8min | 2 tasks | 6 files |
| Phase 15-deep-reading-queue-merge P01 | 4min | 2 tasks | 3 files |
| Phase 15-deep-reading-queue-merge P01 | 4min | 2 tasks | 3 files |
| Phase 17-dead-code-precommit P01 | 25min | 2 tasks | 11 files |
| Phase 18-documentation-ux-polish P01 | 12min | 3 tasks | 4 files |
| Phase 18-documentation-ux-polish P01 | 12min | 3 tasks | 4 files |

## Accumulated Context

### v1.4 Critical Path

- **Phase 13:** Logging Foundation (enables all observability work)
- **Phase 14:** Shared Utils Extraction (critical path — all code-health work depends on `_utils.py`)
- **Phases 13-14-15-16:** Strictly sequential (hard dependency chain)
- **Phase 18:** Can partially overlap with Phases 14-17
- **Phase 19:** Must be last (validates final state)

### v1.4 Key Decisions (from research)

- **Dual-output logging:** `print()` stays for user-facing stdout; `logging` for diagnostic stderr — NOT a wholesale replacement
- **`_utils.py` leaf module:** Must never import from `paperforge.worker.*` or `paperforge.commands.*` — circular import firebreak
- **Re-exports preserved:** Moved functions get `# Re-exported from _utils.py` comments in original modules for backward compatibility
- **No new user-facing features:** v1.4 is pure infrastructure hardening — `auto_analyze_after_ocr` is the only opt-in workflow option

### v1.4 Environment Variables (new)

- `PAPERFORGE_LOG_LEVEL` — `DEBUG`/`INFO`/`WARNING`/`ERROR`
- `PAPERFORGE_RETRY_MAX` — max retry attempts
- `PAPERFORGE_RETRY_BACKOFF` — backoff multiplier

### Phase 11 Decisions (Locked)

- D-01 through D-08: Documented in ADR-011
- `storage:` prefix as unified internal representation for Zotero storage paths
- Hybrid main PDF selection (title → size → shortest title)
- Forward slashes exclusively in wikilinks (`Path.as_posix()`)
- `path_error` frontmatter field for explicit error tracking

### Phase 17 Decisions (Locked)

- `from paperforge.config import load_vault_config, paperforge_paths` replaces all per-module delegation wrappers
- Pre-commit hooks configured but NOT auto-installed (DX-04 deferred to Phase 18)
- `ruff check --fix` + `ruff format` are sufficient for automated code cleanup
- `E501` (line-too-long) and pre-existing simplifications suppressed via `per-file-ignores` — not a blocker for code quality

### Phase 12 Decisions (Locked)

- Migrated 4041-line `literature_pipeline.py` into 7 focused modules under `paperforge/worker/`
- Function-level imports used to break circular dependencies between sync.py and ocr.py
- Module-reference imports (`_sync.run_selection_sync`) used in ocr.py for test patch compatibility
- Old `pipeline/` and `skills/` directories removed after confirming zero import references

### Pending Todos

None yet.

### Blockers/Concerns

- **Circular import risk in Phase 14:** `_utils.py` must be pure leaf module — verify with `pytest --collect-only` after each worker migration
- **Windows TTY detection (Phase 16):** `sys.stdout.reconfigure(encoding='utf-8')` may not work on all PowerShell configs — test on actual Windows 10/11
- **Backward compatibility:** Users relying on `from paperforge.worker.sync import read_json` — mitigation: re-exports with deprecation comments
- **Pre-commit hooks not installed:** CONTRIBUTING.md documents `pre-commit install` (DX-04 docs complete). Hooks must be manually installed by each developer.

## Session Continuity

Last session: 2026-04-27T10:01:03.122Z
Stopped at: Completed 18-01-PLAN.md (auto_analyze_after_ocr, CHANGELOG, CONTRIBUTING)
Resume file: None

---\n*Initialized: 2026-04-23*\n*Last updated: 2026-04-26 (v1.4 roadmap created — Phase 13 ready to plan)*
