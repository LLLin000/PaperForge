# PaperForge

## What This Is

PaperForge is a local-first Obsidian + Zotero literature asset manager. It turns Zotero exports, PDFs, OCR fulltext, figures, notes, and AI outputs into a structured, traceable, reusable research library. v1.9 consolidated the fragmented tracking layers (library-records + formal notes) into a single per-workspace structure with slim frontmatter and paper-meta.json for internal state. v1.10 fixed cross-cutting dependency drift. v1.11 resolved all v1.9 ripple effects (index paths, library-records cleanup, TUI removal, module hardening, repair blind spots).

## Current Milestone: v2.0 Testing Infrastructure — 6-Layer Quality Gates

**Goal:** Establish a multi-layer testing infrastructure that covers version consistency, Python units, CLI contracts, plugin-backend integration, temp vault E2E workflows, user journey contracts, and destructive scenarios — with CI matrix, golden datasets, and snapshot testing.

**Target features:**
- Level 0: Version/build consistency checking (check_version_sync.py)
- Level 1: Python unit tests (config, BBT parser, PDF resolver, OCR state machine, etc.)
- Level 2: CLI contract tests (--json schema stability)
- Level 3: Plugin-backend integration tests (plugin runtime helpers)
- Level 4: Temp vault E2E tests (automatic vault creation, mock OCR, full workflow)
- Level 5: User journey tests (UX Contract doc + journey scripts)
- Level 6: Destructive/abnormal scenario tests (chaos matrix)
- Fixtures: Golden dataset (zotero/ JSON fixtures, PDF fixtures, expected snapshots)
- CI: GitHub Actions matrix (win/mac/linux, py3.10-3.12, node 20)

## Completed Milestone: v1.10 Dependency Cleanup

**Status:** COMPLETE (2026-05-07)

**Delivered:**
- OCR/status/repair workers read workflow state from formal note frontmatter — no library-records dependency
- 14 hardcoded old directory defaults updated to clean names
- 9 documentation files updated for v1.9 structure
- 473 tests pass, 0 regressions

## Completed Milestone: v1.11 Merge Gate — v1.9 Ripple Remediation

**Status:** COMPLETE (2026-05-07)
**Archive:** `.planning/milestones/v1.11-ROADMAP.md`

**Delivered:**
- Index path resolution: 5 workspace fields use config-resolved `literature_dir` (not hardcoded `"Literature/"`); env var typo fixed; legacy config migration
- Library-records deprecation cleanup: zero residual traces in production code, documentation, and user-facing labels
- Textual TUI removal: broken TUI classes removed; `paperforge setup` prints headless redirect; 3 docs updated
- Module hardening: discussion.py (file locking, markdown escaping, UTC timestamps), main.js (API key via env, createEl(), async I/O), asset_state.py (next_step ordering, null JSON outputs), repair.py (all 6 divergence types detected)
- Repair blind spots: condition 4 divergence detection, --fix mode coverage, silent exception logging, dead code removal

## Completed Milestone: v1.9 Frontmatter Rationalization & Library-Record Deprecation

**Status:** COMPLETE (2026-05-07)
**Archive:** `.planning/milestones/v1.9-ROADMAP.md`

**Delivered:**
- Slimmed formal note frontmatter (28 → 16 fields); per-workspace paper-meta.json for internal state
- Library-record generation removed; sync no longer creates library-records
- Unconditional workspace creation on first sync; flat-to-workspace migration with fulltext bridge
- Base views restored to workflow-gate filters (has_pdf/do_ocr/analyze/ocr_status), pointing to Literature/
- Version badge fixed; lifecycle keys aligned; doctor workspace integrity + stale library-records checks
- 188 tests passing, 0 failures

## In Progress: v1.8 AI Discussion & Deep-Reading Dashboard (paused)

**Goal:** Capture AI-paper discussions into structured ai/ records and extend the per-paper dashboard with deep-reading content and AI interaction history.

**Status:** Phases 31-35 partial — 2/6 phases complete. Paused to prioritize v1.9 structural foundation before surfacing more dashboard features.

## Completed Milestone: v1.7 Context-Aware Dashboard

**Status:** COMPLETE (2026-05-04)

**Delivered:**
- Pure CSS dashboard components (metric cards, lifecycle stepper, health matrix, maturity gauge, bar chart)
- Mode-aware dashboard routing with auto-detect and debounced switching
- Full per-paper dashboard: lifecycle stepper, health matrix, maturity gauge, next-step recommendations
- Collection dashboard: domain-level metric cards, lifecycle bar chart, health grid aggregation
- Global dashboard with enhanced library overview

## Completed Milestone: v1.6 AI-Ready Literature Asset Foundation

## Completed Milestone: v1.4 Code Health & UX Hardening

**Status:** COMPLETE (2026-04-27)
**Archive:** `.planning/milestones/v1.4.md`

**Delivered:**
- Structured logging module (`paperforge/logging_config.py`) with dual-output (stdout + stderr)
- Shared utilities module (`paperforge/worker/_utils.py`) eliminating ~1,610 lines of duplication
- Merged deep-reading queue implementations (3 → 1)
- OCR retry/backoff/rate-limiting
- Dead code elimination + pre-commit hooks (ruff)
- `auto_analyze_after_ocr` workflow option
- E2E integration tests + setup_wizard unit tests (317 passed, 2 skipped)
- CONTRIBUTING.md, CHANGELOG.md

### v1.3 Path Normalization & Architecture Hardening

**Status:** COMPLETE (2026-04-24)
**Archive:** `.planning/milestones/v1.3.md`

**Delivered:**
- Zotero attachment path normalization (3 BBT formats → Vault-relative wikilinks)
- Multi-attachment support (main PDF + supplementary with hybrid strategy)
- Pipeline module boundary cleanup (`pipeline/` → `paperforge/worker/` as 7 modules)
- Skill scripts integration (`skills/` → `paperforge/skills/`)
- Test dead zone elimination (203 passed, 2 skipped, 0 failed)
- Enhanced `paperforge doctor` with Path Resolution checks
- `paperforge repair --fix-paths` for automatic path error repair

---

## Completed Milestone: v1.5 Obsidian Plugin Setup Integration

**Status:** COMPLETE (2026-04-29)

**Delivered:**
- Plugin settings tab exposing all setup_wizard.py fields (vault path, system/resource/lit/ctrl/agent dirs, PaddleOCR API token, Zotero junction) — Phase 20
- Settings fields persist via Obsidian `loadData/saveData` API with debounced 500ms save — Phase 20
- One-click "Install" button running full setup via `python -m paperforge setup --headless` with explicit args — Phase 21
- Client-side field validation with Chinese error messages before subprocess spawn — Phase 21
- Subprocess orchestration with button disable/enable lifecycle, stdout step-parsing, and color-coded status area — Phase 21
- Friendly Chinese error mapping (5 patterns) — no raw traceback exposure — Phase 21
- Existing sidebar and command palette completely untouched — strictly additive

## Core Value

Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## Requirements

### Validated

- ✓ Worker/Agent split exists: `literature_pipeline.py` handles mechanical sync/OCR/status, while `/pf-deep` handles deep reading.
- ✓ Configurable vault directories supported through `paperforge.json` and `vault_config`.
- ✓ Obsidian Base views prove the intended queue workflow: recommended analysis, OCR queue, completed OCR, pending deep reading, completed deep reading, and formal notes.
- ✓ OCR queue state persisted in `<system_dir>/PaperForge/ocr/ocr-queue.json` and per-paper `meta.json`.
- ✓ v1.0 shipped shared resolver, `paperforge` CLI, generated Bases, first-pass doctor command, fixture smoke tests, and command documentation.
- ✓ Setup wizard, `paperforge` CLI, direct worker fallback, deployed Agent scripts, and command docs agree on the installed path contract (Phase 6).
- ✓ Diagnostics validate actual supported Better BibTeX export shapes and correct PaddleOCR env names (Phase 6-7).
- ✓ PDF path resolution handles sandbox BBT attachment paths and common Zotero storage-relative paths (Phase 7).
- ✓ Selection sync writes complete normalized metadata into library-records, including author and journal fields (Phase 7).
- ✓ OCR status, formal note status, library-record status, and deep-reading queue status converge after each worker step (Phase 7).
- ✓ `/pf-deep` helpers run from the deployed Vault location without manual `PYTHONPATH` fixes (Phase 8).
- ✓ Sandbox smoke tests (17 tests) catch all regressions from the manual first-time-user simulation (Phase 8).
- ✓ v1.1 hardened the sandbox onboarding flow, adds rollback to `prepare_deep_reading`, and ships 17 regression tests.
- ✓ v1.2 unified agent commands under `/pf-*` namespace and simplified CLI (`paperforge sync`, `paperforge ocr`).
- ✓ v1.2 documented architecture (10 ADRs), migration guide, and established consistency audit.

### v1.3 Completed (2026-04-24)

- ✓ Zotero attachment path normalization (absolute paths, multi-attachments, wikilinks) — Phase 11
- ✓ Pipeline module boundary cleanup (`pipeline/` → `paperforge/worker/` as 7 modules) — Phase 12
- ✓ Skill scripts integration (`skills/` → `paperforge/skills/`) — Phase 12
- ✓ Test dead zone elimination (203 passed, 0 failed) — Phase 12

### v1.4 Completed (2026-04-27)

- ✓ Structured logging (`paperforge/logging_config.py`, `PAPERFORGE_LOG_LEVEL`) — Phase 13
- ✓ Shared utilities extraction (`_utils.py`, ~1,610 lines deduplicated) — Phase 14
- ✓ Deep-reading queue merge (3 implementations → 1) — Phase 15
- ✓ OCR retry/backoff/rate-limiting + progress bar — Phase 16
- ✓ Dead code elimination + pre-commit hooks (ruff) — Phase 17
- ✓ CONTRIBUTING.md, CHANGELOG.md — Phase 18
- ✓ E2E integration tests + setup_wizard tests (317 passed, 2 skipped) — Phase 19
- ✓ `auto_analyze_after_ocr` workflow option — Phase 18
- [ ] Consistency audit CI integration (GitHub Action) — deferred to future

### Validated (v1.5)

- ✓ **SETUP-01**: Plugin settings tab renders all setup_wizard.py fields (vault path, system/resource/lit/ctrl/agent dirs, PaddleOCR API token, Zotero junction) — Phase 20
- ✓ **SETUP-02**: Settings fields persist to plugin data (Obsidian `settings` API), survive reload — Phase 20
- ✓ **SETUP-03**: One-click "Install" button triggers full setup pipeline — write paperforge.json, create directories, env check, agent configs — Phase 21
- ✓ **SETUP-04**: Each setup step produces polished, human-readable output via Obsidian notices/UI (never raw terminal text) — Phase 21
- ✓ **SETUP-05**: Install button validates all fields before execution, shows specific field-level errors in friendly language — Phase 21
- ✓ **SETUP-06**: Existing sidebar and command palette actions continue working unchanged alongside new settings tab — Phase 21

### Validated (v1.11)

- ✓ **REMED-01**: Index workspace path fields use config-resolved literature_dir (not hardcoded "Literature/")
- ✓ **REMED-02**: All library-records residual traces removed — dead code, stale docstrings, wrong scan dirs, misleading labels
- ✓ **REMED-03**: Setup wizard TUI removed; headless-only redirect with clean message
- ✓ **REMED-04**: Discussion recorder hardened: file locking, markdown escaping, UTC timezone, QA key validation
- ✓ **REMED-05**: Plugin hardened: API key via env not CLI args, innerHTML replaced with createEl, sync I/O→async
- ✓ **REMED-06**: Asset state/repair logic fixed: next_step ordering, null JSON outputs, repair divergence blind spots
- ✓ **REMED-07**: 5 command files updated to reflect v1.9 workflow (no library-records references)

### Validated (v1.10)

- ✓ OCR worker reads `do_ocr` from formal note frontmatter (same `get_analyze_queue()` logic as analyze), not from deprecated library-records.
- ✓ Status worker reads `do_ocr`/path counts from formal notes + canonical index, not from library-records.
- ✓ Repair worker three-way divergence scan and path error detection re-anchored to formal notes + canonical index.
- ✓ `load_control_actions()` rewritten to scan formal note frontmatter; orphan cleanup targets Literature/.
- ✓ 14 hardcoded old defaults (`99_System`/`03_Resources`/`05_Bases`) updated in production code to match `DEFAULT_CONFIG`.
- ✓ 5 skill files (pf-sync/pf-ocr/pf-status/pf-paper/pf-deep) updated to reflect library-records deprecation.
- ✓ AGENTS.md, docs/setup-guide.md, docs/ARCHITECTURE.md, docs/COMMANDS.md updated.
- ✓ setup_wizard function signatures and cli.py help text updated to clean directory names.
- ✓ `.gitignore` patterns updated for new clean directory defaults.
- ✓ All tests pass after changes (473 passed, 0 regressions).

### Validated (v1.9)

- ✓ Library-records directory eliminated: sync no longer creates `<control_dir>/library-records/`; new users never see it.
- ✓ Upgrading users get lossless library-record → formal note frontmatter migration on first sync (via `_build_entry()` defaults + paper_meta.py).
- ✓ Base views fixed: removed ghost lifecycle/maturity_level/next_step; restored has_pdf/do_ocr/analyze/ocr_status; folder filter points to Literature/.
- ✓ Formal note frontmatter slimmed to identity fields + workflow flags + pdf_path; redundant fields removed.
- ✓ Per-workspace paper-meta.json stores OCR backend data, derived state details, and debug fields.
- ✓ Workspace folder construction: new papers create workspace on first sync (no flat-first-then-migrate); fulltext.md bridged from OCR output.
- ✓ Path construction unified: discussion.py reads workspace paths from canonical index instead of reconstructing independently.
- ✓ Plugin dashboard: version badge reads paperforge_version from index envelope; lifecycle keys aligned; CSS components verified.

### Validated (v1.8)

- ✓ AI discussion recorder: `/pf-paper` and agent chats produce `discussion.md` + `discussion.json` in workspace `ai/`.
- ✓ Deep-reading dashboard mode with status bar, Pass 1 summary, and AI Q&A history.
- ✓ "Jump to Deep Reading" button on per-paper dashboard card.
- ✓ Bug fix: removed meaningless "ai" row from plugin UI.
- ✓ Bug fix: restored version number display in plugin.

### Out of Scope

- Replacing Zotero or Better BibTeX — the project is built around them.
- Automatically triggering deep-reading agents from workers — the Lite architecture intentionally keeps worker automation and agent reasoning separate.
- Cloud-hosted multi-user service — this project targets local single-user vault workflows.
- Full OCR provider abstraction — deferred (PaddleOCR path/env consistency is the priority).
- Discipline-specific extraction products (PICO tables, mechanism tables, parameter tables) as core built-ins — PaperForge should provide a framework, not hardcoded scholarly schemas.
- Replacing Zotero, Better BibTeX, or Obsidian Bases — the system is built around those primitives.
- Automatically turning every prompt into a fixed UI button — prompt-specific workflows stay optional templates, not core product logic.
- Cloud multi-user collaboration or hosted sync — this milestone remains local-first and single-user.
- Plugin auto-update — deferred to when listed on Obsidian Community Plugins.
- Plugin published to Obsidian Community Plugins — deferred until after v1.5 stabilizes the settings experience.
- v1.8 dashboard features (deep-reading mode, Jump to Deep Reading, AI discussion recorder) — paused, not cancelled; will resume after v1.9 cleans the structural foundation.

## Context

The v1.1 milestone was completed after a manual sandbox audit from `tests/sandbox/00_TestVault` using README-level guidance. All audit findings have been addressed:

- [x] `python setup_wizard.py --vault ...` no longer stalls; Vault input is prefilled from `--vault`.
- [x] `python -m paperforge` fallback is documented in AGENTS.md and INSTALLATION.md.
- [x] `paperforge doctor` validates per-domain JSON exports and checks `PADDLEOCR_API_TOKEN`.
- [x] `paperforge paths --json` reports the same paths used by setup and runtime.
- [x] Command docs use unified `/pf-*` namespace consistently.
- [x] `selection-sync` writes `first_author` and `journal` from normalized BBT metadata.
- [x] `deep-reading --verbose` prints ready/waiting/blocked queues directly.
- [x] `paperforge repair` detects and fixes three-way state divergence.
- [x] Deployed `ld_deep.py` runs without manual `PYTHONPATH` (via `pip install -e .` or importlib).
- [x] Sandbox smoke tests (17 tests) catch all regressions from the manual audit.

**v1.2 shipped:**
- Unified `/pf-*` agent command namespace (5 commands)
- Simplified CLI (`paperforge sync`, `paperforge ocr`)
- `paperforge/commands/` shared modules architecture
- `paperforge` Python package rename (from `paperforge_lite`)
- Architecture documentation with 10 ADRs
- Complete v1.1 → v1.2 migration guide
- Consistency audit (4/4 passing)
- 178 tests passing, 0 failures

**v1.3 focus:** Fix real-world Zotero path handling (absolute Windows paths in BBT JSON → Vault-relative wikilinks), clean up module architecture (`pipeline/` and `skills/` integration), eliminate test dead zones, establish CI-ready consistency audit.

**v1.4 shipped (2026-04-27):**
- Structured logging with `PAPERFORGE_LOG_LEVEL` env var
- `_utils.py` shared module (read_json, write_json, yaml operations, slugify, journal_db)
- Single deep-reading queue implementation
- OCR retry/backoff/rate-limiting with progress bar
- Pre-commit hooks (ruff check --fix + ruff format)
- CONTRIBUTING.md, CHANGELOG.md
- 317 tests passing, 2 skipped, 0 failures

**v1.5 shipped (2026-04-29):** Settings tab with all 8 wizard fields, debounced persistence, one-click "安装配置" button, client-side field validation with Chinese errors, subprocess orchestration via `python -m paperforge setup --headless`, step-by-step Chinese progress notices, and color-coded status area. Plugin becomes single download artifact — no terminal required for new user setup.

**v1.6 focus:** Consolidate the next layer of product evolution into one milestone instead of splitting it across several small releases. The emphasis is not on more one-off extraction buttons, but on durable asset state, asset health, maturity-guided workflow progression, and AI-ready context packaging.

**v1.9 focus:** The feature branch (milestone/v1.6-ai-ready-asset-foundation) accumulated 117 commits of v1.6-v1.8 work. Before merging to master, structural cleanup is needed: library-records (a v1.0 tracking layer) must be deprecated in favor of formal note frontmatter; Base views regressed in v1.7 (lost workflow flags, gained unwritten ghost fields); frontmatter grew to 47 unique fields across two note types. This milestone fixes the foundation so incremental PRs can land cleanly on master.

Key gaps identified on feature branch:
- Base views declare lifecycle/maturity_level/next_step but NO .md writer exists for these fields — columns permanently empty
- Base views lost has_pdf/do_ocr/analyze/ocr_status — users cannot batch-toggle workflow from Obsidian
- _build_entry() declares fulltext_path in workspace but no code copies OCR output there — broken link
- New papers go flat-first-then-migrate — should create workspace directly
- discussion.py builds ai/ path independently instead of reading from canonical index

## Constraints

- **Local-first:** Must work in a user's Obsidian vault without a daemon or cloud service.
- **Windows compatibility:** Windows junctions, PowerShell, and paths with Chinese names are first-class use cases.
- **Plain Python:** Keep dependencies small; current requirements are `requests`, `pymupdf`, `pillow`, `textual`, and `pytest`.
- **Obsidian compatibility:** `.base` files must use Obsidian Bases syntax and relative vault paths.
- **Credential safety:** API keys belong in `.env` or user environment variables and must not be committed.
- **Agent independence:** Users should not need an agent to inspect `paperforge.json` just to build a worker command.
- **Sandbox realism:** `tests/sandbox` must remain safe, deterministic, and representative of a GitHub user trying the project locally.
- **Thin-shell plugin:** Obsidian plugin UI must not become a second implementation of lifecycle or health logic already owned by Python workers.
- **Traceability:** AI-facing outputs must remain traceable back to original PDFs, OCR outputs, and notes.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep Lite two-layer architecture | Worker and Agent responsibilities are already clear and lower-risk than automatic deep-reading triggers | ✓ Accepted — v1.0-v1.2 stable |
| Add a PaperForge CLI/launcher layer | It removes placeholder command friction and centralizes path/env resolution | ✓ Implemented v1.0, refined v1.1-v1.2 |
| Treat PaddleOCR as a preflighted integration | Users need immediate diagnosis before jobs enter confusing pending/error states | ✓ Implemented v1.0, aligned v1.1 |
| Generate Bases from config-aware templates | Current production Base UX is better than release templates, but hardcoded paths must be parameterized | ✓ Implemented v1.0 |
| Use sandbox audit as v1.1 release gate | Manual first-time-user simulation exposed regressions that unit tests missed | ✓ Complete — 17 smoke tests cover all findings |
| Unify agent commands under `/pf-*` namespace | Two prefixes (`/LD-*` and `/lp-*`) confuse users; single namespace aligns with CLI brand | ✓ Implemented v1.2 |
| Simplify CLI with combined commands | `selection-sync` + `index-refresh` almost always run together; one `sync` command reduces friction | ✓ Implemented v1.2 |
| Aggressive migration (no aliases) | Clean break reduces maintenance burden; migration guide handles transition | ✓ Implemented v1.2 |
| Command modules in `paperforge/commands/` | Shared logic between CLI and Agent layers reduces duplication | ✓ Implemented v1.2 |
| Package rename to `paperforge` | Naming consistency with CLI brand | ✓ Implemented v1.2 |
| Extract shared worker utilities to `_utils.py` | ~1,610 lines of duplicate utility code exist across 7 worker modules; single source of truth reduces maintenance burden | ✓ Implemented v1.4 |
| Settings tab in Obsidian plugin as setup entry point | Eliminates terminal requirement for new users; plugin becomes single download artifact. CLI/Agent unchanged — plugin is a new UI surface | ✓ Implemented v1.5 |
| Reposition PaperForge around literature assets, not one-off prompts | Long-term user value comes from clean, traceable, AI-ready libraries rather than hardcoded extraction buttons | — Active for v1.6 |
| Keep plugin as thin shell over CLI and canonical index | Avoids duplicated business logic and configuration drift between JS and Python layers | — Active for v1.6 |
| Deprecate library-records in favor of formal notes | Two tracking layers (library-records + formal notes) create divergence, double the frontmatter surface, and confuse users. Formal notes already carry most metadata; adding workflow flags makes them self-sufficient. | ✓ Integrated |
| Separate Base views (workflow batch ops) from Dashboard (derived state viz) | lifecycle/maturity/next_step already have rich visualization in the Obsidian plugin dashboard; duplicating them in Base views as empty columns adds noise. Base views focus on user-actionable workflow gates. | ✓ Implemented |
| Per-workspace paper-meta.json for internal state | Frontmatter is the user-facing surface; internal pipeline data (OCR jobs, health details, debug fields) belongs in a machine-readable JSON file. Keeps formal notes clean while preserving all state for tools. | ✓ Implemented |
| Unconditional workspace creation on first sync | Flat-note fallback created confusion and required separate migration step. Always creating workspace dirs simplifies the architecture and eliminates the flat-first-then-migrate path. | ✓ Implemented |

## Research Lock

Research has been frozen at milestone boundaries to avoid redundant re-research.  

**v1.6 (Literature Asset Foundation)** — product direction and architecture are settled:
- Asset lifecycle, canonical index, thin-shell plugin, paper workspace direction, ai/ in workspace, Python-owned health/maturity rules.  
- No re-research needed unless architecture or product direction changes materially.  

**v1.7 (LLMWiki Concept Network)** — direction settled:
- Cross-paper synthesis layer, concept/mechanism network, source-traceable, human-reviewable.  
- No re-research on "whether to build a wiki" or "first use case."  

**v1.9 (Frontmatter Rationalization)** — no new research needed:
- All pieces already exist on the feature branch: workspace migration, derived state, canonical index, Base generation, frontmatter writing.
- This milestone is structural cleanup — rewire, remove, and fix existing code, not invent new capabilities.
- Skip research for this milestone.

See: `.planning/research/MILESTONE-RESEARCH-LOCK.md` for the full lock definition.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? Move to Out of Scope with reason.
2. Requirements validated? Move to Validated with phase reference.
3. New requirements emerged? Add to Active.
4. Decisions to log? Add to Key Decisions.
5. "What This Is" still accurate? Update if drifted.

**After each milestone:**
1. Full review of all sections.
2. Core Value check.
3. Audit Out of Scope.
4. Update Context with current state.

---
*Last updated: 2026-05-08 after milestone v2.0 initiation*
