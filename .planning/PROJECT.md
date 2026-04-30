# PaperForge Lite Release Hardening

## What This Is

PaperForge Lite is a polished local Obsidian + Zotero literature workflow for medical researchers. It takes a new user from registration/configuration through Better BibTeX export, Obsidian Base queue control, PaddleOCR processing, formal literature note generation, and `/pf-deep` deep reading. The UX is smooth, code is clean, and failures are diagnosed clearly.

v1.5 moves the setup/configuration entry point from terminal CLI into the Obsidian plugin itself — a settings tab where users fill in paths and API keys, then click one button for full installation. The plugin becomes the single artifact a new user needs to download.

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

A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

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

### Active

None.

### Out of Scope

- Replacing Zotero or Better BibTeX — the project is built around them.
- Automatically triggering deep-reading agents from workers — the Lite architecture intentionally keeps worker automation and agent reasoning separate.
- Cloud-hosted multi-user service — this project targets local single-user vault workflows.
- Full OCR provider abstraction — deferred (PaddleOCR path/env consistency is the priority).
- Plugin sidebar redesign — sidebar stays as-is for v1.5; enhancement deferred to future milestone.
- Plugin auto-update — deferred to when listed on Obsidian Community Plugins.
- Plugin published to Obsidian Community Plugins — deferred until after v1.5 stabilizes the settings experience.

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

## Constraints

- **Local-first:** Must work in a user's Obsidian vault without a daemon or cloud service.
- **Windows compatibility:** Windows junctions, PowerShell, and paths with Chinese names are first-class use cases.
- **Plain Python:** Keep dependencies small; current requirements are `requests`, `pymupdf`, `pillow`, `textual`, and `pytest`.
- **Obsidian compatibility:** `.base` files must use Obsidian Bases syntax and relative vault paths.
- **Credential safety:** API keys belong in `.env` or user environment variables and must not be committed.
- **Agent independence:** Users should not need an agent to inspect `paperforge.json` just to build a worker command.
- **Sandbox realism:** `tests/sandbox` must remain safe, deterministic, and representative of a GitHub user trying the project locally.

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

---\n*Last updated: 2026-04-29 — v1.5 shipped (Phases 20-21: Obsidian Plugin Setup Integration)*
