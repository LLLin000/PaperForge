# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-23)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.1 — Sandbox Onboarding Hardening

## Current Position

Phase: 7 (discuss-phase complete, execution complete)
Plan: 07-PLAN.md
Status: Ready to initiate Phase 8
Last activity: 2026-04-24 — Phase 7 execution complete (5/5 tasks done)

## Milestone Context

Manual sandbox simulation exposed release-blocking gaps after v1.0:

- Setup wizard can appear to stall when invoked exactly as README says.
- CLI/doctor/docs disagree on paths, env variable names, and JSON fields.
- Per-domain BBT exports are supported by workers but rejected by doctor.
- Sandbox Zotero storage PDFs are not resolved from BBT attachment paths.
- Selection sync loses normalized author/journal metadata in library-records.
- OCR and deep-reading states can diverge across records, notes, and meta files.
- Deployed `/LD-deep` helper fails without package importability or manual `PYTHONPATH`.

## Next Action

Run `/gsd-plan-phase 6` for **Setup, CLI, And Diagnostics Consistency**.

## Phase 6 Decisions (Locked)

- `paperforge paths --json` outputs: `vault`, `worker_script`, `ld_deep_script` (not `literature_script`)
- Canonical PaddleOCR env var: `PADDLEOCR_API_TOKEN` (must be consistent across setup/worker/doctor)
- Doctor validates all `*.json` exports, not only `library.json`
- Doctor L2 distinguishes HTTP 405 from bad URL with actionable message
- VaultStep Input pre-filled from `--vault` argument
- `python -m paperforge_lite` is documented fallback when `paperforge` not registered

## Open Questions

- HTTP 405 error message wording (agent's discretion per CONTEXT.md)
- ProgressBar stall if prefilled vault doesn't resolve it

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-24 (Phase 7 complete)*

## Previous Milestone Summary

Milestone v1.0 completed Phases 1-5:

| Phase | Status | Summary |
|------|--------|---------|
| 1 | done | Shared config resolver, `paperforge` launcher, worker/Agent resolver integration, stable command docs |
| 2 | done | PDF path resolver, OCR failure classification, OCR doctor, selection-sync PDF reporting |
| 3 | done | Config-aware Base generation and `base-refresh` |
| 4 | done | Deep-reading queue states, doctor command, AGENTS/README updates |
| 5 | done | Fixture smoke test suite and release verification |
| 6 | done | Setup/CLI/docs consistency — field names, env vars, export validation, HTTP 405 handling, vault prefill |

## Decisions Logged

- **2026-04-23:** Config precedence locked as: explicit overrides > env > JSON nested > JSON top-level > defaults.
- **2026-04-23:** `paperforge_paths` returns a stable user-facing path inventory; v1.1 must make that inventory match deployed installation layout.
- **2026-04-23:** CLI returns int exit codes for testability; worker functions imported at module level for patchability.
- **2026-04-23:** `load_simple_env` loads vault root `.env` and PaperForge `.env` before worker dispatch.
- **2026-04-23:** `paperforge ocr doctor` uses tiered diagnostics with live provider checks optional.
- **2026-04-23:** v1.1 will use the sandbox first-time-user simulation as a release gate before claiming setup/onboarding reliability.
