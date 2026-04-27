# Roadmap: PaperForge Lite v1.4 — Code Health & UX Hardening

**Milestone:** v1.4
**Goal:** Eliminate all code duplication (~1,610 lines), add structured observability, automate code-health guardrails, and smooth user-facing workflow friction.
**Started:** 2026-04-25
**Phase numbering:** Continues from v1.3 Phase 12 → v1.4 starts at Phase 13

---

## Phases

- [ ] **Phase 13: Logging Foundation** — Structured logging, `--verbose` flag, zero behavioral change to user-facing output
- [ ] **Phase 14: Shared Utilities Extraction** — Extract `_utils.py` leaf module, eliminate ~1,610 lines of duplication across 7 workers
- [ ] **Phase 15: Deep-Reading Queue Merge** — Single canonical `scan_library_records()` for both CLI and Agent consumers
- [ ] **Phase 16: Retry + Progress Bars** — Resilient OCR with exponential backoff and user-visible progress indication
- [ ] **Phase 17: Dead Code Removal + Pre-Commit** — Clean codebase validated by automated git hooks
- [ ] **Phase 18: Documentation + CHANGELOG + UX Polish** — Complete user/maintainer docs, README fix, command naming audit (2 plans)
- [ ] **Phase 19: Testing** — E2E pipeline tests, setup wizard tests, `_utils.py` unit tests

---

## Phase Details

### Phase 13: Logging Foundation
**Goal**: Structured, level-based logging infrastructure with zero behavioral change to user-facing output — sets the stage for all subsequent observability work.
**Depends on**: Nothing (first phase of v1.4)
**Requirements**: OBS-01, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):
  1. All worker modules use `logging.getLogger(__name__)` instead of bare `print()` for diagnostic/trace/error output
  2. `--verbose`/`-v` flag on `paperforge sync`, `paperforge ocr`, and `paperforge deep-reading` enables DEBUG-level output on stderr
  3. User-facing status messages continue to appear on stdout unchanged — piped commands (`paperforge status | grep ocr`) remain unbroken
  4. `PAPERFORGE_LOG_LEVEL` environment variable (accepting `DEBUG`/`INFO`/`WARNING`/`ERROR`) controls default log level
  5. `paperforge/logging_config.py` exists as the single `configure_logging(verbose)` call point; no scattered `basicConfig()` calls
**Plans**: 3 plans (2 waves)

Plans:
- [x] 13-01-PLAN.md — Logging Core: logging_config.py + global --verbose flag
- [x] 13-02-PLAN.md — Module Loggers: logger instances + diagnostic print migration
- [x] 13-03-PLAN.md — Verbose Wiring: verbose params + command dispatch passthrough

---

### Phase 14: Shared Utilities Extraction
**Goal**: Eliminate ~1,610 lines of copy-pasted utility code by creating `paperforge/worker/_utils.py` as a pure leaf module — THE critical path all subsequent code-health work depends on.
**Depends on**: Phase 13 (logging infrastructure available for diagnostic output)
**Requirements**: CH-01, CH-02, CH-05, TEST-03
**Success Criteria** (what must be TRUE):
  1. `paperforge/worker/_utils.py` exists containing all shared utility functions: `read_json`, `write_json`, `read_jsonl`, `write_jsonl`, `yaml_quote`, `yaml_block`, `yaml_list`, `slugify_filename`, `_extract_year`, `load_journal_db`, `lookup_impact_factor`, `_STANDARD_VIEW_NAMES`, and the `_JOURNAL_DB` cache
  2. All 7 worker modules (`sync.py`, `ocr.py`, `deep_reading.py`, `repair.py`, `status.py`, `update.py`, `base_views.py`) import shared functions from `paperforge.worker._utils` — no local copy of any utility function remains
  3. No circular imports: `_utils.py` imports only from stdlib and `paperforge.config` — never from any sibling worker module
  4. All 205 existing tests pass with zero failures after extraction (verified by `pytest tests/ -x`)
  5. Re-exports with `# Re-exported from _utils.py for backward compatibility` comments preserved in original modules where callers may still reference them
**Plans**: 2 plans (1 wave)

Plans:
- [x] 18-01-PLAN.md — Core Config & Foundation Docs (auto_analyze_after_ocr, CHANGELOG, CONTRIBUTING)
- [ ] 18-02-PLAN.md — Migration, Architecture & Doc Polish (MIGRATION, ADRs, AGENTS, INDEX, README)

---

### Phase 19: Testing
**Goal**: Validate the entire v1.4 codebase with expanded test coverage — E2E pipeline tests, setup wizard tests, and dedicated `_utils.py` unit tests.
**Depends on**: All previous phases (tests validate the final v1.4 state)
**Requirements**: TEST-01, TEST-02, TEST-04
**Success Criteria** (what must be TRUE):
  1. E2E integration tests pass covering full Zotero JSON → selection-sync → index-refresh → OCR queue → formal notes pipeline using the sandbox fixture vault
  2. Setup wizard tests pass validating agent platform detection, vault path resolution, environment checks, and configuration file generation
  3. Dedicated unit tests for `_utils.py` cover JSON I/O, YAML helpers, slugify, and journal DB functions — `test_utils_json.py`, `test_utils_yaml.py`, `test_utils_slugify.py`, `test_utils_journal.py`
  4. All 205 existing tests continue to pass with zero failures — minimum bar: 205+ tests passing, 0 failures, 0 errors
**Plans**: TBD

---

## Progress

**Execution Order:** Phases 13-14-15-16 are strictly sequential (hard dependency chain). Phase 18 can overlap partially with Phases 14-17. Phase 19 must be last.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 13. Logging Foundation | v1.4 | 3/3 | Complete    | 2026-04-27 |
| 14. Shared Utils Extraction | v1.4 | 0/0 | Not started | — |
| 15. Queue Merge | v1.4 | 1/1 | Complete   | 2026-04-27 |
| 16. Retry + Progress | v1.4 | 2/2 | Complete | 2026-04-27 |
| 17. Dead Code + Pre-Commit | v1.4 | 1/1 | Complete | 2026-04-27 |
| 18. Docs + CHANGELOG + UX | v1.4 | 2/1 | In progress | — |
| 19. Testing | v1.4 | 0/0 | Not started | — |

### Historical Milestones

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-04-23</summary>

- Phase 1: Config And Command Foundation (3/3 plans)
- Phase 2: PaddleOCR And PDF Path Hardening (2/2 plans)
- Phase 3: Config-Aware Obsidian Bases (2/2 plans)
- Phase 4: End-To-End Onboarding And Validation (2/2 plans)
- Phase 5: Release Verification (2/2 plans)

_Archived: `.planning/milestones/v1.0.md`_

</details>

<details>
<summary>✅ v1.1 Sandbox Onboarding (Phases 6-8) — SHIPPED 2026-04-24</summary>

- Phase 6: Setup, CLI, And Diagnostics Consistency (3/3 plans)
- Phase 7: Zotero PDF, Metadata, And State Repair (2/2 plans)
- Phase 8: Deep Helper Deployment And Sandbox Regression Gate (2/2 plans)

_Archived: `.planning/milestones/v1.1.md`_

</details>

<details>
<summary>✅ v1.2 Systematization & Cohesion (Phases 9-10) — SHIPPED 2026-04-24</summary>

- Phase 9: Command Unification & CLI Simplification (2/2 plans)
- Phase 10: Documentation & Cohesion (2/2 plans)

_Archived: `.planning/milestones/v1.2-ROADMAP.md`_

</details>

<details>
<summary>✅ v1.3 Path Normalization & Architecture Hardening (Phases 11-12) — SHIPPED 2026-04-24</summary>

- Phase 11: Zotero Path Normalization (1/1 plan)
- Phase 12: Architecture Cleanup (1/1 plan)

_Archived: `.planning/milestones/v1.3.md`_

</details>

---

*Roadmap created: 2026-04-26 — Milestone v1.4 Code Health & UX Hardening*
*Phase numbering continues from v1.3 Phase 12*
