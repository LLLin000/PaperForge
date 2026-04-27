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
- [ ] **Phase 18: Documentation + CHANGELOG + UX Polish** — Complete user/maintainer docs, README fix, command naming audit
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
**Plans**: TBD

---

### Phase 15: Deep-Reading Queue Merge
**Goal**: Merge two divergent queue-scanning implementations into a single canonical `scan_library_records()` in `_utils.py` — CLI and Agent consumers see identical results.
**Depends on**: Phase 14 (`_utils.py` must exist for the shared function)
**Requirements**: CH-03
**Success Criteria** (what must be TRUE):
  1. `scan_library_records()` in `_utils.py` returns identical results whether called from `worker/deep_reading.py` or `skills/ld_deep.py`
  2. `paperforge deep-reading` CLI output matches Agent queue scan output exactly
  3. ~50 lines of duplicate queue-scanning logic removed from `ld_deep.py`
  4. No behavioral change to queue filtering: ready/waiting/blocked categories preserved
**Plans**: 1 plan

Plans:
- [x] 15-01-PLAN.md — Canonical scan_library_records() in _utils.py; refactor both callers

---

### Phase 16: Retry + Progress Bars
**Goal**: Make the OCR pipeline resilient to transient network failures and provide user-visible progress indication for long-running operations.
**Depends on**: Phase 13 (logging) and Phase 14 (`_utils.py` for retry decorator + progress bar wrapper)
**Requirements**: REL-01, REL-02, REL-03, REL-04, OBS-04
**Success Criteria** (what must be TRUE):
  1. Transient PaddleOCR API failures (HTTP 429, 502, 503, timeouts) trigger automatic retry with exponential backoff (1s → 2s → 4s → 8s → max 30s) and jitter
  2. OCR `meta.json` records `retry_count`, `last_error`, and `last_attempt_at` fields — atomically written after each attempt
  3. Zombie `processing` jobs older than 30 minutes are reset to `pending` on worker restart (configurable via `PAPERFORGE_RETRY_MAX` and `PAPERFORGE_RETRY_BACKOFF` env vars)
  4. A single OCR upload failure does not abort the entire batch — failed items are logged, state updated, and processing continues with remaining items
  5. `tqdm` progress bar appears during OCR uploads in interactive terminals; auto-disables in CI/pipe contexts; `--no-progress` flag suppresses explicitly
**Plans**: TBD

---

### Phase 17: Dead Code Removal + Pre-Commit
**Goal**: Remove all dead code, slim import blocks, and install automated pre-commit safety nets that prevent future duplication — LAST code phase, validates the cleaned codebase.
**Depends on**: Phase 14 (`_utils.py` provides canonical locations for previously duplicated code) and Phase 15 (deep-reading cleanup complete)
**Requirements**: CH-04, DX-01, DX-02, OBS-05
**Success Criteria** (what must be TRUE):
  1. No unused imports remain in any worker module — verified by `ruff check`
  2. UPDATE_* constants (lines 620-625 in `status.py`) and unnecessary delegation wrappers (`load_vault_config`, `pipeline_paths`) removed — direct `config.*` imports replace them
  3. `.pre-commit-config.yaml` active with hooks: `ruff` (lint + format), `check-yaml`, `check-toml`, `end-of-file-fixer`, `trailing-whitespace`, and custom `consistency-audit` hook
  4. `git commit` triggers pre-commit hooks — consistency audit blocks commits if duplicate utility functions are detected in any worker module
  5. OCR error messages include HTTP status code, library-record name for context, and actionable suggestion (e.g., "Run `paperforge ocr --diagnose` to test API connectivity")
**Plans**: TBD

---

### Phase 18: Documentation + CHANGELOG + UX Polish
**Goal**: Complete all user-facing and maintainer-facing documentation, fix README rendering artifacts, add workflow streamlining options, and cross-reference chart-reading guides.
**Depends on**: No hard code dependency — can overlap with earlier phases; must ship after Phase 17 to document final state
**Requirements**: DX-03, DX-04, UX-01, UX-02, UX-03, UX-04, DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. `CHANGELOG.md` exists in Keep a Changelog format with sections for v1.0 through v1.4 — changelog URL included in `paperforge.json` update metadata
  2. `CONTRIBUTING.md` documents: development setup (`pip install -e ".[test]"`), pre-commit hook installation, test execution workflow, architecture overview, and code conventions
  3. `docs/MIGRATION-v1.4.md` documents all behavioral changes (dual-output logging, retry behavior, opt-in workflow streamlining), new environment variables, and required developer setup
  4. README.md line 102 orphaned legacy code snippet removed; all user-facing docs (AGENTS.md, docs/*.md, command/*.md) audited for rendering issues
  5. `chart-reading/INDEX.md` cross-references all 19 chart types ordered by biomedical commonness; agent prompt (`prompt_deep_subagent.md`) references this index
  6. AGENTS.md section 1 includes "What to type where" quick-reference table mapping `/pf-*` Agent commands to `paperforge *` CLI commands
  7. `auto_analyze_after_ocr` option available in `paperforge.json` (bool, default `false`) — opt-in to preserve Worker/Agent separation
  8. ADR-012 (Shared Utilities Extraction) and ADR-013 (Dual-Output Logging Strategy) added to `docs/ARCHITECTURE.md`
**Plans**: TBD

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
| 16. Retry + Progress | v1.4 | 0/0 | Not started | — |
| 17. Dead Code + Pre-Commit | v1.4 | 0/0 | Not started | — |
| 18. Docs + CHANGELOG + UX | v1.4 | 0/0 | Not started | — |
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
