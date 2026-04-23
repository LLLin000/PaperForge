# PaperForge Lite Release Hardening

## What This Is

PaperForge Lite is a local Obsidian + Zotero literature workflow for medical researchers. It should take a new user from registration/configuration through Better BibTeX export, Obsidian Base queue control, PaddleOCR processing, formal literature note generation, and `/LD-deep` deep reading without requiring an agent to manually inspect paths and rewrite commands.

This is a brownfield release-hardening project for `D:\L\Med\Research\99_System\LiteraturePipeline\github-release`, informed by the fuller local implementation under `D:\L\Med\Research\99_System\LiteraturePipeline` and the production Obsidian Base views under `D:\L\Med\Research\05_Bases`.

## Current Milestone: v1.1 Sandbox Onboarding Hardening

**Goal:** Make the GitHub README + sandbox path behave like a real first-time user flow, with no silent setup stalls, contradictory diagnostics, unresolved mock Zotero PDFs, or broken `/LD-deep` prepare commands.

**Target features:**
- Setup wizard and CLI commands are internally consistent when a user follows README exactly.
- `paperforge doctor`, `paperforge paths --json`, worker fallback commands, and Agent command docs report the same installed paths and env variable names.
- Sandbox Better BibTeX exports and mock Zotero storage exercise the full flow from selection sync through `/LD-deep prepare`.
- PDF/OCR/deep-reading statuses remain consistent across library-records, formal notes, `meta.json`, and queue output.

## Core Value

A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

## Requirements

### Validated

- ✓ Worker/Agent split exists: `literature_pipeline.py` handles mechanical sync/OCR/status, while `/LD-deep` handles deep reading.
- ✓ Configurable vault directories are partially supported through `paperforge.json` and `vault_config`.
- ✓ Existing Obsidian Base views prove the intended queue workflow: recommended analysis, OCR queue, completed OCR, pending deep reading, completed deep reading, and formal notes.
- ✓ OCR queue state is persisted in `<system_dir>/PaperForge/ocr/ocr-queue.json` and per-paper `meta.json`.
- ✓ v1.0 shipped a shared resolver, `paperforge` CLI, generated Bases, first-pass doctor command, fixture smoke tests, and command documentation.

### Active

- [ ] README-driven setup works in the sandbox without hidden required inputs or unexplained terminal stalls.
- [ ] Setup wizard, `paperforge` CLI, direct worker fallback, deployed Agent scripts, and command docs agree on the installed path contract.
- [ ] Diagnostics validate the actual supported Better BibTeX export shapes and PaddleOCR env names.
- [ ] PDF path resolution handles sandbox BBT attachment paths and common Zotero storage-relative paths.
- [ ] Selection sync writes complete normalized metadata into library-records, including author and journal fields.
- [ ] OCR status, formal note status, library-record status, and deep-reading queue status converge after each worker step.
- [ ] `/LD-deep` helpers run from the deployed Vault location without manual `PYTHONPATH` fixes.
- [ ] The sandbox smoke test catches every regression found in the manual first-time-user simulation.

### Out of Scope

- Replacing Zotero or Better BibTeX — the project is built around them.
- Automatically triggering deep-reading agents from workers — the Lite architecture intentionally keeps worker automation and agent reasoning separate.
- Cloud-hosted multi-user service — this project targets local single-user vault workflows.
- Full OCR provider abstraction in v1.1 — PaddleOCR path/env consistency is the priority.

## Context

The v1.1 milestone is based on a manual sandbox audit performed from `tests/sandbox/00_TestVault` using only README-level guidance. The audit found that v1.0's claimed release-hardening coverage is not yet sufficient for a real first-time user:

- `python setup_wizard.py --vault ...` can appear to hang in a terminal, and the Vault input is not prefilled from `--vault`.
- `paperforge` may be unavailable when setup does not complete; README does not clearly provide a reliable fallback.
- `paperforge doctor` checks `library.json` and `PADDLEOCR_API_KEY`, while the implemented flow supports per-domain JSON exports and uses `PADDLEOCR_API_TOKEN`.
- `paperforge paths --json` reports a worker path under `vault/pipeline/...`, but setup deploys the worker under `<system_dir>/PaperForge/worker/scripts/...`.
- Command docs reference `literature_script`, but the CLI emits `ld_deep_script`.
- Sandbox BBT attachment paths such as `TSTONE001/TSTONE001.pdf` do not resolve to `<Zotero>/storage/TSTONE001/TSTONE001.pdf`.
- `selection-sync` normalizes export rows but later reads raw BBT fields, leaving `first_author` and `journal` empty in library-records.
- `deep-reading --verbose` writes the useful queue report to a file but prints only a terse pending count.
- Deployed `ld_deep.py` depends on `paperforge_lite` importability and fails without manual `PYTHONPATH` or a successful package install.

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
| Use sandbox audit as v1.1 release gate | Manual first-time-user simulation exposed regressions that unit tests missed | Active |
| Continue phase numbering after v1.0 | v1.1 is a follow-up hardening milestone, not a project reset | Phases start at 6 |

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
*Last updated: 2026-04-23 starting milestone v1.1*
