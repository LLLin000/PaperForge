# PaperForge Lite Release Hardening

## What This Is

PaperForge Lite is a polished local Obsidian + Zotero literature workflow for medical researchers. It takes a new user from registration/configuration through Better BibTeX export, Obsidian Base queue control, PaddleOCR processing, formal literature note generation, and `/pf-deep` deep reading. The UX is smooth, code is clean, and failures are diagnosed clearly.

v1.4 focuses on eliminating accumulated technical debt (~1,610 lines of code duplication, ad-hoc logging) and smoothing the user-facing workflow friction points identified in a comprehensive codebase audit.

## Completed Milestone: v1.3 Path Normalization & Architecture Hardening

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

## Current Milestone: v1.4 Code Health & UX Hardening

**Goal:** Eliminate all code duplication, add formal observability, and streamline the end-to-end user workflow.

**Target features (User-facing):**
- Simplify OCR → deep-reading workflow (reduce manual frontmatter-editing steps)
- Add progress indicators for long-running operations (large-file OCR)
- Improve error visibility on OCR failure (structured log output)
- Unify Agent/CLI naming mental model (audit `/pf-*` vs `paperforge *` boundaries)
- Fix README rendering artifacts (legacy code snippet on line 102)

**Target features (Maintainer-facing):**
- Extract `worker/_utils.py` shared module (eliminate ~1,610 lines of duplicated code)
- Replace `print()` with level-based structured `logging` module
- Merge duplicate deep-reading queue scanning implementations
- Add retry/backoff/rate-limiting for OCR worker
- Clean up dead code and unused imports across all 7 workers
- Add pre-commit hook with consistency audit
- Add `CONTRIBUTING.md`, `CHANGELOG.md`
- Add E2E integration tests + setup_wizard tests
- Cross-reference chart-reading guides in agent prompt

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
- [ ] Consistency audit CI integration (pre-commit / GitHub Action) — deferred to future

### Out of Scope

- Replacing Zotero or Better BibTeX — the project is built around them.
- Automatically triggering deep-reading agents from workers — the Lite architecture intentionally keeps worker automation and agent reasoning separate.
- Cloud-hosted multi-user service — this project targets local single-user vault workflows.
- Full OCR provider abstraction in v1.2 — deferred to v1.3+ (PaddleOCR path/env consistency was the v1.2 priority).

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

**v1.4 focus:** A comprehensive codebase audit (2026-04-25) revealed 1,610 lines of duplicated code across 7 worker modules, ad-hoc `print()`-based logging, duplicate deep-reading queue implementations, and user-facing UX friction. v1.4 will extract a shared utilities module, add structured logging, merge duplicate implementations, add pre-commit hooks, and streamline the OCR→deep-reading workflow.

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
| Extract shared worker utilities to `_utils.py` | ~1,610 lines of duplicate utility code exist across 7 worker modules; single source of truth reduces maintenance burden | — Pending |

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

---\n*Last updated: 2026-04-25 — Milestone v1.4 started (code health & UX hardening)*
