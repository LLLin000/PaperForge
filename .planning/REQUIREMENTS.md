# Requirements: PaperForge Lite

> **Defined:** 2026-04-25
> **Core Value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

---

## v1.3 Requirements (Validated)

All 19 v1.3 requirements shipped and validated. See `.planning/milestones/v1.3.md` and `MILESTONES.md` for completion details.

---

## v1.4 Requirements

### Code Health (CH)

**Goal:** Eliminate all code duplication and dead code across the 7 worker modules.

- [ ] **CH-01**: Create `paperforge/worker/_utils.py` as a pure leaf module (zero imports from sibling workers) containing all duplicated utility functions: `read_json`, `write_json`, `read_jsonl`, `write_jsonl`, `yaml_quote`, `yaml_block`, `yaml_list`, `slugify_filename`, `_extract_year`, `load_journal_db`, `lookup_impact_factor`, `_STANDARD_VIEW_NAMES`, and the `_JOURNAL_DB` cache.
- [ ] **CH-02**: Update all 7 worker modules (`sync.py`, `ocr.py`, `deep_reading.py`, `repair.py`, `status.py`, `update.py`, `base_views.py`) to import shared functions from `paperforge.worker._utils` instead of defining local copies. Approximately 1,610 lines of duplication removed.
- [x] **CH-03**: Merge the two duplicate deep-reading queue scanning implementations — consolidate `worker/deep_reading.py::run_deep_reading()` (scanner logic) and `skills/ld_deep.py::scan_deep_reading_queue()` into a single `scan_library_records()` function in `_utils.py`. Both original call sites import the shared function with no behavioral change.
- [ ] **CH-04**: Remove dead code: (a) `UPDATE_*` constants from `status.py` lines 620-625 (duplicated in `update.py`), (b) unused imports from each worker module (`csv`, `hashlib`, `shutil`, `subprocess`, `zipfile`, `ElementTree`, `fitz`, `PIL` where not used), (c) unnecessary delegation wrappers (`load_vault_config` / `pipeline_paths`) that merely call `paperforge.config` equivalents — direct `config.*` imports replace these.
- [ ] **CH-05**: All 205 existing tests continue to pass after shared utility extraction. No regression in CLI dispatch, OCR state machine, path normalization, repair, or base view generation.

### Observability (OBS)

**Goal:** Replace ad-hoc `print()` calls with a structured, configurable logging system.

- [x] **OBS-01**: Create `paperforge/logging_config.py` that configures a `logging.Logger` hierarchy using stdlib `logging`. Log level controllable via `PAPERFORGE_LOG_LEVEL` environment variable (accepts `DEBUG`/`INFO`/`WARNING`/`ERROR` string names). All workers and CLI commands use `logger = logging.getLogger(__name__)`.
- [x] **OBS-02**: Implement dual-output strategy: `print()` preserved for user-facing formatted output on stdout; `logging` used for diagnostic/trace/error output to stderr. Existing piped commands and Agent scripts that parse stdout continue to work unmodified.
- [x] **OBS-03**: Add `--verbose`/`-v` flag to `paperforge sync`, `paperforge ocr`, and `paperforge deep-reading` that enables `DEBUG` log level. All existing commands accept the flag.
- [ ] **OBS-04**: Add `tqdm`-based progress bars to OCR upload (per-PDF) and batch polling loops. Progress output goes to stderr. Auto-detects non-TTY mode (CI, pipe) — silently falls back to no progress output when stdout is not an interactive terminal. A `--no-progress` flag suppresses output explicitly.
- [ ] **OBS-05**: Make OCR error messages actionable: on failure/timeout/blocked, the error includes the specific HTTP status code or exception type, the library-record name for context, and a suggestion (e.g., "Run `paperforge ocr --diagnose` to test API connectivity" or "Run `paperforge repair --fix` to recover state"). Error pattern follows `ocr_diagnostics.classify_error()` format.

### Reliability (REL)

**Goal:** Make the OCR pipeline resilient to transient network failures.

- [ ] **REL-01**: Add `tenacity`-based retry decorator to PaddleOCR API calls (upload and poll functions) with exponential backoff (1s → 2s → 4s → 8s → max 30s), jitter, and selective exception retry (`requests.ConnectionError`, `requests.Timeout`, `HTTPError` with status 429/503). Configurable via `PAPERFORGE_RETRY_MAX` and `PAPERFORGE_RETRY_BACKOFF` environment variables.
- [ ] **REL-02**: Extend OCR `meta.json` schema with `retry_count` (int, default 0), `last_error` (str | null), `last_attempt_at` (ISO-8601 str | null). These fields are written atomically after each attempt and read during polling to inform retry decisions.
- [ ] **REL-03**: Prevent zombie OCR state: on worker restart, all `processing` jobs older than configurable threshold (default: 30 minutes) are reset to `pending` with `retry_count` incremented. Blocked jobs (`blocked` terminal state) are never retried unless user manually resets `do_ocr`.
- [ ] **REL-04**: The `paperforge ocr` command gracefully handles partial failures: a single upload failure does not abort the entire batch. Failed items are logged, their state updated, and processing continues with remaining items.

### Developer Experience (DX)

**Goal:** Establish standard open-source project infrastructure for maintainers and contributors.

- [ ] **DX-01**: Create `.pre-commit-config.yaml` with hooks: `ruff` (lint + format), `check-yaml`, `check-toml`, `end-of-file-fixer`, `trailing-whitespace`, and a custom `consistency-audit` hook that runs `scripts/consistency_audit.py` and blocks commits if duplicate utility functions are detected in any worker module.
- [ ] **DX-02**: Add `[tool.ruff]` section to `pyproject.toml` targeting Python 3.10+, enabling rules `E`, `F`, `I`, `UP`, `B`, `SIM`. Run `ruff check --fix` and `ruff format` across the entire codebase as part of the pre-commit activation phase.
- [x] **DX-03**: Create `CHANGELOG.md` following the Keep a Changelog format with sections for each version (v1.0 through v1.4). Include the changelog URL in `paperforge.json` update metadata.
- [x] **DX-04**: Create `CONTRIBUTING.md` documenting: development setup (`pip install -e ".[test]"`), pre-commit hook installation, test execution workflow, architecture overview, and code conventions (no new print() calls, import shared utilities from `_utils.py`, REQ-ID linking in commit messages).

### Testing (TEST)

**Goal:** Close testing gaps identified in the codebase audit.

- [ ] **TEST-01**: Add E2E integration tests in `tests/test_e2e_pipeline.py` covering the full Zotero JSON → selection-sync → index-refresh → OCR queue → formal notes pipeline using the sandbox fixture vault. Tests validate frontmatter completeness, wikilink correctness, and state transitions.
- [ ] **TEST-02**: Add setup wizard tests in `tests/test_setup_wizard.py` validating: agent platform detection, vault path resolution, environment checks, and configuration file generation. Tests use the Textual testing harness if available or validate standalone functions independently.
- [ ] **TEST-03**: All existing 205 tests continue to pass with zero failures. No test regression from shared utility extraction, logging changes, or dead code removal. Minimum bar: 205+ tests passing, 0 failures, 0 errors.
- [ ] **TEST-04**: Add dedicated unit tests for `paperforge/worker/_utils.py` functions: `test_utils_json.py` (read/write JSON + JSONL), `test_utils_yaml.py` (yaml_quote/yaml_block/yaml_list), `test_utils_slugify.py` (slugify_filename, _extract_year), `test_utils_journal.py` (load_journal_db, lookup_impact_factor).

### User Experience (UX)

**Goal:** Smooth user-facing friction points identified in the codebase audit.

- [x] **UX-01**: Add workflow streamlining options to `paperforge.json`: `auto_analyze_after_ocr` (bool, default `false`) — when enabled, after OCR completes for a paper, the library-record's `analyze` flag is automatically set to `true`. This is opt-in to preserve the two-layer Worker/Agent separation and user agency.
- [x] **UX-02**: Fix README.md rendering artifact: remove the orphaned legacy code snippet lines (`python <resolved_worker_script> --vault . ocr`, `python <resolved_worker_script> --vault . status`) at lines 102-104 that appear outside any code fence. Audit all user-facing docs (AGENTS.md, docs/*.md, command/*.md) for similar rendering issues.
- [x] **UX-03**: Generate a chart-reading guide cross-reference index (`chart-reading/INDEX.md`) that maps the 19 chart types to their reading guides, ordered by commonness in biomedical literature. The agent prompt (`prompt_deep_subagent.md`) references this index so AI agents can discover and cite relevant guides during Pass 2 figure-by-figure analysis.
- [x] **UX-04**: Audit the command naming boundary: ensure all user-facing documentation consistently maps `/pf-*` Agent commands to `paperforge *` CLI commands. Add a quick-reference table showing "What to type where" in AGENTS.md section 1.

### Documentation (DOCS)

**Goal:** Document the v1.4 changes for existing users and future maintainers.

- [x] **DOCS-01**: Create `docs/MIGRATION-v1.4.md` following the established v1.2 migration document pattern. Document behavioral changes (dual-output logging, retry behavior, opt-in workflow streamlining), environment variable additions (`PAPERFORGE_LOG_LEVEL`, `PAPERFORGE_RETRY_MAX`, `PAPERFORGE_RETRY_BACKOFF`), and new developer workflow requirements (pre-commit hooks, ruff).
- [x] **DOCS-02**: Update `AGENTS.md` to reflect: new `--verbose` flag on CLI commands, new `paperforge.json` workflow options, new environment variables page, and the chart-reading INDEX.md cross-reference.
- [x] **DOCS-03**: Add ADR-012 (Shared Utilities Extraction) and ADR-013 (Dual-Output Logging Strategy) to `docs/ARCHITECTURE.md`, documenting the `_utils.py` leaf-module constraint and the print/logging boundary decision.
- [x] **DOCS-04**: Update `ROADMAP.md` to reflect v1.4 phase structure and mark all requirements as mapped after roadmap creation.

---

## v1.5 Requirements (Deferred)

Deferred from v1.4 scope to keep the milestone focused and manageable.

### Workflow

- **WF-01**: One-click `paperforge process` command — triggers sync + OCR + auto-analyze in a single command. Deferred: requires research on optimal default behavior vs opt-out model.
- **WF-02**: Obsidian Base bulk-action integration — inline "Run OCR" / "Start Deep Reading" buttons in Base views. Deferred: requires Obsidian plugin architecture research.

### Testing

- **TEST-V2-01**: Performance benchmarks for OCR processing (large PDF timing). Deferred: need baseline measurements first.
- **TEST-V2-02**: Cross-platform CI (Windows + macOS + Linux) via GitHub Actions. Deferred: pre-commit hooks are the priority for v1.4.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-triggering deep-reading from workers | Lite architecture keeps Worker and Agent layers separate (ADR-002) |
| Cloud-hosted multi-user service | Local-first scope |
| Replacing Zotero or Better BibTeX | Core dependency |
| OCR provider abstraction (beyond PaddleOCR) | Requires API research, deferred to v1.5+ |
| TypeScript Obsidian plugin architecture | Major new stack, needs dedicated milestone |
| Real-time Zotero sync (daemon) | Conflicts with Lite two-layer design |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CH-01 | Phase 14 | Pending |
| CH-02 | Phase 14 | Pending |
| CH-03 | Phase 15 | Complete |
| CH-04 | Phase 17 | Pending |
| CH-05 | Phase 14 | Pending |
| OBS-01 | Phase 13 | Complete |
| OBS-02 | Phase 13 | Complete |
| OBS-03 | Phase 13 | Complete |
| OBS-04 | Phase 16 | Pending |
| OBS-05 | Phase 17 | Pending |
| REL-01 | Phase 16 | Pending |
| REL-02 | Phase 16 | Pending |
| REL-03 | Phase 16 | Pending |
| REL-04 | Phase 16 | Pending |
| DX-01 | Phase 17 | Pending |
| DX-02 | Phase 17 | Pending |
| DX-03 | Phase 18 | Complete |
| DX-04 | Phase 18 | Complete |
| TEST-01 | Phase 19 | Pending |
| TEST-02 | Phase 19 | Pending |
| TEST-03 | Phase 14 | Pending |
| TEST-04 | Phase 19 | Pending |
| UX-01 | Phase 18 | Complete |
| UX-02 | Phase 18 | Complete |
| UX-03 | Phase 18 | Complete |
| UX-04 | Phase 18 | Complete |
| DOCS-01 | Phase 18 | Complete |
| DOCS-02 | Phase 18 | Complete |
| DOCS-03 | Phase 18 | Complete |
| DOCS-04 | Phase 18 | Complete |

**Coverage:**
- v1.4 requirements: 30 total
- Mapped to phases: 30 (100%)
- Unmapped: 0

---

*Requirements defined: 2026-04-25*
*Last updated: 2026-04-26 — traceability populated with v1.4 phase mappings (30/30 requirements, 100% coverage)*
