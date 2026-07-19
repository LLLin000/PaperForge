# Milestones: PaperForge Lite Release Hardening

## v1.8 AI Discussion & Deep-Reading Dashboard (Shipped: 2026-05-07)

**Phases completed:** 6 phases (31-36)

**Key accomplishments:**

- Version display restored, "AI Ready" lifecycle stage removed from dashboard (Phase 31)
- Deep-reading mode detection: `_resolveModeForFile()` prioritises deep-reading.md → zotero_key → global (Phase 32)
- Deep-reading dashboard rendering: status card + Pass 1 extraction + AI Q&A collapsible history (Phase 33)
- "Jump to Deep Reading" button on per-paper dashboard card (Phase 34)
- AI discussion recorder: `discussion.py` writes atomic discussion.md + discussion.json into workspace ai/ (Phase 35)
- Full E2E integration verification with CJK encoding and vault.read API (Phase 36)

---

## v1.9 Frontmatter Rationalization & Library-Record Deprecation (Shipped: 2026-05-07)

**Phases completed:** 5 phases, 28 requirements (all verified)
**Tests:** 188 passing

**Key accomplishments:**

- Slimmed formal note frontmatter from 28 to 16 fields: identity (title/year/journal/first_author/zotero_key/domain/doi/pmid/collection_path/impact_factor/abstract/tags) + workflow (has_pdf/do_ocr/analyze/ocr_status/deep_reading_status) + pdf_path
- Created `paper_meta.py` — per-workspace JSON for internal pipeline state (OCR jobs, health, maturity, version)
- Removed `library_record_markdown()` and all library-record generation from sync — new users never see library-records
- Unconditional workspace creation — new papers get workspace directories on first sync (no flat fallback)
- Fulltext bridge from OCR output to workspace; discussion.py reads from canonical index
- Base views restored to workflow-gate filters (has_pdf/do_ocr/analyze/ocr_status → do_ocr=true, analyze=true+ocr_status=done) pointing to Literature/
- Version badge fixed to read paperforge_version from canonical index envelope
- Doctor detects stale library-records directory and workspace integrity issues

---

## v1.7 Context-Aware Dashboard (Shipped: 2026-05-04)

**Phases completed:** 4 phases, 6 plans, 14 tasks

**Key accomplishments:**

- Pure CSS dashboard components for the PaperForge plugin -- loading skeleton, metric card, lifecycle stepper, health matrix, maturity gauge, and bar chart -- all themed via Obsidian CSS variables
- 5 new DOM render methods on PaperForgeStatusView: loading skeleton utilities, enhanced metric cards, 6-stage lifecycle stepper, 2x2 health matrix, 6-segment maturity gauge, and lifecycle-proportional bar chart -- all using createEl() DOM API with CSS classes from Plan 27-01
- Index loading utilities (_loadIndex, _getCachedIndex, _findEntry, _filterByDomain) on PaperForgeStatusView + CSS Sections 13-14 for mode-aware dashboard content area and header context
- Mode-aware dashboard routing with _detectAndSwitch, _switchMode, debounced event subscriptions, mode header rendering, and lifecycle cleanup in PaperForgeStatusView
- Full per-paper dashboard rendering pipeline: lifecycle stepper, health matrix, maturity gauge, next-step recommendation card, contextual actions, and paper metadata header
- Domain-level aggregated dashboard: metric cards (papers/fulltext-ready/deep-read), lifecycle bar chart, and health overview grid with healthy/unhealthy counts for PDF/OCR/Note/Asset dimensions

---

## v1.6 AI-Ready Literature Asset Foundation (Shipped: 2026-05-04)

**Phases completed:** 6 phases, 15 plans, 40 tasks

**Key accomplishments:**

- schema_version marker, top-level-to-vault_config migration engine, and auto-trigger in sync command
- Refactored Obsidian plugin to read path configuration from `paperforge.json` (vault_config block), eliminating the second runtime truth problem where plugin DEFAULT_SETTINGS had wrong defaults (System/Resources/Notes/Index_Cards/Base instead of Python's 99_System/03_Resources/Literature/LiteratureControl/05_Bases).
- Setup wizard writes canonical vault_config-only paperforge.json with schema_version, doctor detects stale legacy config with migration guidance, and load_vault_config supports optional config source tracing for CONF-03 runtime inspection.
- Extracted index generation from sync.py into asset_index.py with versioned envelope format, atomic writes (tempfile + os.replace + filelock), and 14 passing tests
- Legacy bare-list auto-migration, incremental refresh by Zotero key, workspace path fields in every index entry, and --rebuild-index CLI flag for the canonical asset index
- Wire incremental index refresh into OCR, deep-reading, and repair workers; document sync.py default convention; add integration tests
- Four pure derivation functions (lifecycle, health, maturity, next-step) consuming canonical index entry dicts with full test coverage via TDD
- All four compute functions from asset_state.py wired into _build_entry() — every canonical index entry now carries embedded lifecycle, health, maturity, and next_step fields derived from source artifacts
- status --json reads lifecycle/health/maturity from canonical index; doctor shows Index Health section with per-dimension health counts and brownfield detection
- Plugin dashboard reads formal-library.json directly via readFileSync instead of spawning Python CLI, with doctor and repair as one-click Quick Action buttons
- Base views lifecycle column migration and repair source-first rebuild with build_index() call
- Flat literature notes copied into per-paper workspace directories with ## 🔍 精读 extraction and ai/ directory creation, wired into run_index_refresh() for first-sync migration, with workspace-aware _build_entry() writing and backward-compatible flat fallback
- paperforge context CLI command that reads the canonical index and outputs JSON context entries with provenance traces and AI readiness explanations
- Plugin "Copy Context" and "Copy Collection Context" Quick Actions with zotero_key resolution from active note frontmatter, clipboard copy with JSON validation

---

**Project:** PaperForge Lite — Local Obsidian + Zotero literature workflow for medical researchers

---

## Milestone v1.0: Initial Release (2026-04-23)

**Goal:** Prove the release is robust enough to ship and maintain.

**Completed:** 2026-04-23

### What Shipped

| Phase | Name | Goal |
|-------|------|------|
| 1 | Config And Command Foundation | Stable commands and shared path/env resolution |
| 2 | PaddleOCR And PDF Path Hardening | Diagnosable, retryable OCR |
| 3 | Config-Aware Obsidian Bases | Real workflow Bases without hardcoded paths |
| 4 | End-To-End Onboarding And Validation | User can complete first-paper flow |
| 5 | Release Verification | Tests and docs prove ship readiness |

### Requirements Validated

| ID | Requirement | Phase |
|----|-------------|-------|
| CONF-01 | Env vars override JSON values | Phase 1 |
| CONF-02 | paperforge_paths returns 13-key inventory | Phase 1 |
| CONF-03 | All consumers use same resolver | Phase 1 |
| CONF-04 | Legacy paperforge.json backward compat | Phase 1 |
| CMD-01 | Stable paperforge CLI commands | Phase 1 |
| CMD-02 | Legacy direct worker invocation supported | Phase 1 |
| CMD-03 | Actionable statuses, no placeholders | Phase 1 |
| DEEP-02 | /LD-deep uses same resolver as workers | Phase 1 |
| OCR-01 | ocr doctor L1-L4 diagnostics | Phase 2 |
| OCR-02 | PDF preflight before OCR | Phase 2 |
| OCR-03 | Failure classification (blocked/error/nopdf) | Phase 2 |
| OCR-04 | Retry by re-running ocr | Phase 2 |
| OCR-05 | Defensive API schema handling | Phase 2 |
| ZOT-01 | PDF path resolver (absolute/relative/junction/storage) | Phase 2 |
| ZOT-02 | Selection sync reports missing PDFs | Phase 2 |
| ZOT-03 | BBT export validation | Phase 4 |
| BASE-01 | 8-view domain Bases matching real workflow | Phase 3 |
| BASE-02 | Config-aware path placeholders | Phase 3 |
| BASE-03 | User-edited Bases preserved on refresh | Phase 3 |
| BASE-04 | Literature Hub Base cross-domain overview | Phase 3 |
| ONBD-01 | Registration-to-first-paper guide | Phase 4 |
| ONBD-02 | paperforge doctor validation command | Phase 4 |
| ONBD-03 | Next-step guidance after each command | Phase 4 |
| DEEP-01 | Deep-reading queue shows ready vs blocked | Phase 4 |
| DEEP-03 | /LD-deep failure messages point to fix command | Phase 4 |
| REL-01 | Unit tests for config, OCR, Base, CLI | Phase 5 |
| REL-02 | Fixture smoke test on dummy vault | Phase 5 |
| REL-03 | Docs/AGENTS match commands | Phase 5 |

### Test Coverage

- 145 tests passing, 2 skipped
- Coverage: config resolver, path resolver, OCR state machine, Base rendering, CLI dispatch, command docs

### Key Files Modified

- `paperforge/config.py` — shared resolver
- `paperforge/cli.py` — CLI launcher
- `paperforge/pdf_resolver.py` — PDF path resolution
- `paperforge/ocr_diagnostics.py` — OCR diagnostics
- `pipeline/worker/scripts/literature_pipeline.py` — worker + Base generation
- `tests/` — 15 test files (145 tests)
- `AGENTS.md` — updated to paperforge CLI format
- `docs/` — installation and setup guides

### Deferred to v1.1

| ID | Requirement | Reason |
|----|-------------|--------|
| INT-01 | OCR provider plugin system | PaddleOCR must stabilize first |
| INT-02 | BBT settings auto-detection | Requires BBT plugin API research |
| INT-03 | Scheduled worker automation | Conflicts with Lite two-layer design |
| UX-01 | Setup wizard repair mode | Current install flow sufficient |
| UX-02 | Base file import parameterization | base-refresh covers this |
| UX-03 | Pipeline health dashboard | Not core to v1 value |

---
*Milestone v1.0 completed: 2026-04-23*
*Total phases: 5 | Total requirements: 28 validated*

---

## Milestone v1.1: Sandbox Onboarding Hardening (2026-04-24)

**Goal:** Make the GitHub README + sandbox path behave like a real first-time user flow.

**Completed:** 2026-04-24

### What Shipped

| Phase | Name | Goal |
|-------|------|------|
| 6 | Setup CLI Diagnostics Consistency | Field names, env vars, export validation, HTTP 405 handling, vault prefill |
| 7 | Zotero PDF Metadata State Repair | OCR meta validation, three-way divergence repair command, PDF resolver tests |
| 8 | Deep Helper Deployment And Sandbox Regression Gate | Importability, fixtures, smoke tests, rollback |

### Requirements Validated

| ID | Requirement | Phase |
|----|-------------|-------|
| SETUP-01 | Setup wizard no longer stalls on vault input | Phase 6 |
| SETUP-02 | `paperforge paths --json` matches runtime paths | Phase 6 |
| CLI-01 | `paperforge doctor` validates per-domain JSON exports | Phase 6 |
| CLI-02 | `paperforge doctor` checks `PADDLEOCR_API_TOKEN` env | Phase 6 |
| CLI-03 | `python -m paperforge` fallback documented | Phase 6 |
| REPAIR-01 | Three-way state divergence detection | Phase 7 |
| REPAIR-02 | `paperforge repair` fixes state divergence | Phase 7 |
| DEEP-04 | `/LD-deep` helpers run without manual PYTHONPATH | Phase 8 |
| DEEP-05 | Rollback on prepare_deep_reading failure | Phase 8 |
| TEST-01 | 17 smoke tests catch all audit regressions | Phase 8 |

### Deferred to v1.2

| ID | Requirement | Reason |
|----|-------------|--------|
| ZPATH-01 | BBT bare `KEY/KEY.pdf` auto-normalize | Requires BBT export format research |
| ZPATH-02 | BBT relative path handling | Partial — `storage:` prefix works, bare paths don't |
| ZPATH-03 | Cross-platform PDF path resolution | Windows junctions work, edge cases remain |

---
*Milestone v1.1 completed: 2026-04-24*
*Total phases: 3 (6-8) | Total requirements: 21 validated, 3 partial*

---

## Milestone v1.2: Systematization & Cohesion (In Progress)

**Goal:** Transform PaperForge Lite from a functional-but-scattered prototype into a cohesive, user-centric system.

**Status:** In Progress (2026-04-24)

**Roadmap:** `.planning/ROADMAP-v1.2.md`
**Requirements:** `.planning/REQUIREMENTS-v1.2.md`

### Planned Work

| # | Area | Description | Phase |
|---|------|-------------|-------|
| 1 | Agent Command Unification | Rename `/ld-deep` → `/pf-deep`, `/lp-*` → `/pf-*`, update all docs | 9 |
| 2 | CLI Simplification | Combine `selection-sync` + `index-refresh` into `paperforge sync`, evaluate other mergers | 9 |
| 3 | Architecture Research | Study `get-shit-done-main` and reference projects for patterns | 9 |
| 4 | UX Cohesion | Ensure 1:1 mapping between agent and CLI commands | 10 |
| 5 | Documentation & Migration | Update AGENTS.md, command docs, migration guide | 10 |

### Target Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| SYS-01 | All agent commands use `/pf-*` namespace | Phase 9 |
| SYS-02 | `/LD-*` and `/lp-*` commands deprecated with warnings | Phase 9 |
| SYS-03 | `paperforge sync` combines selection-sync + index-refresh | Phase 9 |
| SYS-04 | CLI command set is user-centric, not worker-centric | Phase 9 |
| SYS-05 | Architecture research documented with recommendations | Phase 9 |
| SYS-06 | Command docs consistent across agent and CLI | Phase 10 |
| SYS-07 | Migration guide for existing users | Phase 10 |

---
*Milestone v1.2 initiated: 2026-04-24*

---

## Milestone v1.3: Path Normalization & Architecture Hardening (2026-04-24)

**Goal:** Fix real-world Zotero path handling, clean up module architecture, and close gaps discovered during v1.2 execution.

**Completed:** 2026-04-24

### What Shipped

| Phase | Name | Goal |
|-------|------|------|
| 11 | Zotero Path Normalization | Parse 3 BBT formats, generate wikilinks, multi-attachment support |
| 12 | Architecture Cleanup | Eliminate module boundary leaks (pipeline/ → paperforge/worker/) |

### Key Deliverables

- `_normalize_attachment_path()` — unified BBT path parsing (absolute Windows, storage: prefix, bare relative)
- `_identify_main_pdf()` — hybrid strategy for main PDF vs supplementary
- `obsidian_wikilink_for_pdf()` — standard `[[relative/path]]` wikilink generation
- `path_error` frontmatter field — granular error states (not_found/invalid/permission_denied)
- `paperforge doctor` Path Resolution checks — junction detection, path validation
- `paperforge repair --fix-paths` — automatic path error repair
- `paperforge/worker/` package — 7 focused modules from 4041-line monolith
- `paperforge/skills/literature-qa/` — migrated skills with subdirectory structure

### Verification

- 203 tests passed, 2 skipped, 0 failed
- Consistency audit 4/4 passing
- No `pipeline.worker.scripts` or `skills.literature_qa` imports remain

### Archive

`.planning/milestones/v1.3.md`

---
*Milestone v1.3 completed: 2026-04-24*

---

## v1.10 Dependency Cleanup (Shipped: 2026-05-07)

**Phases completed:** 4 phases (42-45), 29 requirements

**Key accomplishments:**

- OCR/status workers read `do_ocr`/`analyze` from formal note frontmatter (same pattern as `get_analyze_queue()`) — core workflow unbroken for post-v1.9 papers
- `load_control_actions()` rewritten to scan Literature/; `auto_analyze_after_ocr` writes to formal notes
- Repair worker re-anchored: three-way divergence scan compares formal note frontmatter vs canonical index vs meta.json
- 14 hardcoded old directory defaults (`99_System`, `03_Resources`, `05_Bases`) updated to clean names across asset_index/sync/repair/setup_wizard/validate_setup/.gitignore/CLI
- 9 documentation files updated (AGENTS.md, 5 skill files, 3 docs) — zero remaining library-records references
- 473 tests pass, 0 regressions
