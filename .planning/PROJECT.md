# PaperForge Lite Release Hardening

## What This Is

PaperForge Lite is a local Obsidian + Zotero literature workflow for medical researchers. It should take a new user from registration/configuration through Better BibTeX export, Obsidian Base queue control, PaddleOCR processing, formal literature note generation, and `/LD-deep` deep reading without requiring an agent to manually inspect paths and rewrite commands.

This is a brownfield release-hardening project for `D:\L\Med\Research\99_System\LiteraturePipeline\github-release`, informed by the fuller local implementation under `D:\L\Med\Research\99_System\LiteraturePipeline` and the production Obsidian Base views under `D:\L\Med\Research\05_Bases`.

## Current Milestone: v1.2 Systematization & Cohesion

**Goal:** Transform PaperForge Lite from a functional-but-scattered prototype into a cohesive, user-centric system where commands are unified, workflows are intuitive, and the architecture feels intentional rather than assembled.

**Target features:**
- Agent commands use a single `/pf-*` namespace (`/pf-deep`, `/pf-paper`, `/pf-ocr`, `/pf-sync`, `/pf-status`) replacing the fragmented `/LD-*` and `/lp-*` prefixes.
- CLI commands are simplified and user-centric (e.g., `paperforge sync` combines `selection-sync` + `index-refresh`).
- Architecture is informed by reference projects (e.g., `get-shit-done-main`) for directory structure, command dispatch, and plugin patterns.
- Documentation and command docs are consistent across agent and CLI interfaces.
- Existing functionality is preserved; no breaking data format changes.

## Core Value

A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

## Requirements

### Validated

- ✓ Worker/Agent split exists: `literature_pipeline.py` handles mechanical sync/OCR/status, while `/LD-deep` handles deep reading.
- ✓ Configurable vault directories are partially supported through `paperforge.json` and `vault_config`.
- ✓ Existing Obsidian Base views prove the intended queue workflow: recommended analysis, OCR queue, completed OCR, pending deep reading, completed deep reading, and formal notes.
- ✓ OCR queue state is persisted in `<system_dir>/PaperForge/ocr/ocr-queue.json` and per-paper `meta.json`.
- ✓ v1.0 shipped a shared resolver, `paperforge` CLI, generated Bases, first-pass doctor command, fixture smoke tests, and command documentation.
- ✓ Setup wizard, `paperforge` CLI, direct worker fallback, deployed Agent scripts, and command docs agree on the installed path contract (Phase 6).
- ✓ Diagnostics validate actual supported Better BibTeX export shapes and correct PaddleOCR env names (Phase 6-7).
- ✓ PDF path resolution handles sandbox BBT attachment paths and common Zotero storage-relative paths (Phase 7).
- ✓ Selection sync writes complete normalized metadata into library-records, including author and journal fields (Phase 7).
- ✓ OCR status, formal note status, library-record status, and deep-reading queue status converge after each worker step (Phase 7).
- ✓ `/LD-deep` helpers run from the deployed Vault location without manual `PYTHONPATH` fixes (Phase 8).
- ✓ The sandbox smoke test catches every regression found in the manual first-time-user simulation (Phase 8).
- ✓ v1.1 hardens the sandbox onboarding flow, adds rollback to `prepare_deep_reading`, and ships 17 regression tests.

### Active

- [ ] Unify agent command namespace: `/ld-deep` → `/pf-deep`, `/lp-*` → `/pf-*`.
- [ ] Simplify CLI: combine `selection-sync` + `index-refresh` into `paperforge sync`, evaluate other command mergers.
- [ ] Research architecture from reference projects for directory structure, dispatch patterns, and plugin architecture.
- [ ] Ensure 1:1 mapping between agent commands and CLI commands where appropriate.
- [ ] Update all command docs, AGENTS.md, and provide migration guide.

### Out of Scope

- Replacing Zotero or Better BibTeX — the project is built around them.
- Automatically triggering deep-reading agents from workers — the Lite architecture intentionally keeps worker automation and agent reasoning separate.
- Cloud-hosted multi-user service — this project targets local single-user vault workflows.
- Full OCR provider abstraction in v1.2 — PaddleOCR path/env consistency is the priority.
- BBT bare path normalization in v1.2 — deferred to v1.3 (ZPATH-01/02/03 marked Partial).
- Adding new AI capabilities or OCR features in v1.2 — focus is on systematization, not new functionality.

## Context

The v1.1 milestone was completed after a manual sandbox audit from `tests/sandbox/00_TestVault` using README-level guidance. All audit findings have been addressed:

- [x] `python setup_wizard.py --vault ...` no longer stalls; Vault input is prefilled from `--vault`.
- [x] `python -m paperforge` fallback is documented in AGENTS.md and INSTALLATION.md.
- [x] `paperforge doctor` validates per-domain JSON exports and checks `PADDLEOCR_API_TOKEN`.
- [x] `paperforge paths --json` reports the same paths used by setup and runtime.
- [x] Command docs use `ld_deep_script` consistently.
- [x] `selection-sync` writes `first_author` and `journal` from normalized BBT metadata.
- [x] `deep-reading --verbose` prints ready/waiting/blocked queues directly.
- [x] `paperforge repair` detects and fixes three-way state divergence.
- [x] Deployed `ld_deep.py` runs without manual `PYTHONPATH` (via `pip install -e .` or importlib).
- [x] Sandbox smoke tests (17 tests) catch all regressions from the manual audit.

**Remaining from v1.1:** BBT bare `KEY/KEY.pdf` path normalization is not auto-converted. Users should configure BBT to emit `storage:` prefix or ensure PDFs are in absolute/vault-relative paths.

**v1.2 focus:** Command namespace unification, CLI simplification, architecture research, and UX cohesion. No new functional features; pure systematization.

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
| Keep Lite two-layer architecture | Worker and Agent responsibilities are already clear and lower-risk than automatic deep-reading triggers | Accepted |
| Add a PaperForge CLI/launcher layer | It removes placeholder command friction and centralizes path/env resolution | Implemented in v1.0, repair consistency in v1.1 |
| Treat PaddleOCR as a preflighted integration | Users need immediate diagnosis before jobs enter confusing pending/error states | Implemented in v1.0, align env names in v1.1 |
| Generate Bases from config-aware templates | Current production Base UX is better than release templates, but hardcoded paths must be parameterized | Implemented in v1.0 |
| Use sandbox audit as v1.1 release gate | Manual first-time-user simulation exposed regressions that unit tests missed | Complete — 17 smoke tests now cover all audit findings |
| Continue phase numbering after v1.0 | v1.1 is a follow-up hardening milestone, not a project reset | Phases start at 6 |
| Unify agent commands under `/pf-*` namespace | Two prefixes (`/LD-*` and `/lp-*`) confuse users; single namespace aligns with CLI brand | Planned for v1.2 |
| Simplify CLI with combined commands | `selection-sync` + `index-refresh` are almost always run together; one `sync` command reduces friction | Planned for v1.2 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? Move to Out of Scope with reason.
2. Requirements validated? Move to Validated with phase reference.
3. New requirements emerged? Add to Active.
4. Decisions to log? Add to Key Decisions.
5. "What This Is" still accurate? Update if drifted.

**After each milestone**:
1. Full review of all sections.
2. Core Value check.
3. Audit Out of Scope.
4. Update Context with current state.

---
*Last updated: 2026-04-24 — v1.2 initiated (systematization: unified commands, simplified CLI, architecture research)*
