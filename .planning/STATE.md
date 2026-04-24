# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Milestone v1.2 — Systematization & Cohesion

## Current Position

Phase: 9 (planned)
Milestone: v1.2
Status: Phase 9 planned and ready for execution
Last activity: 2026-04-24 — Phase 9 context, discussion, and plan created

## Next Action

Phase 9 planning complete. Ready for `/gsd-execute-phase` to begin implementation.

Phase 9 scope:
- Task 0: Rename Python package (`paperforge_lite` → `paperforge`)
- Task 1: Create shared command modules
- Task 2: Refactor CLI to use command modules
- Task 3: Create new `/pf-*` agent command docs
- Task 4: Remove old `/LD-*` and `/lp-*` command docs
- Task 5: Update AGENTS.md and tests
- Task 6: Verification and cleanup

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
*Last updated: 2026-04-24 (Milestone v1.2 initiated)*

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
| 7 | done | Zotero PDF, metadata, and state repair — OCR meta validation, three-way divergence repair command, PDF resolver tests |
| 8 | done | Deep helper deployment and sandbox regression gate — importability, fixtures, smoke tests, rollback |

Milestone v1.1 (Sandbox Onboarding Hardening) completed as part of Phases 6-8.

## Decisions Logged

- **2026-04-23:** Config precedence locked as: explicit overrides > env > JSON nested > JSON top-level > defaults.
- **2026-04-23:** `paperforge_paths` returns a stable user-facing path inventory; v1.1 must make that inventory match deployed installation layout.
- **2026-04-23:** CLI returns int exit codes for testability; worker functions imported at module level for patchability.
- **2026-04-23:** `load_simple_env` loads vault root `.env` and PaperForge `.env` before worker dispatch.
- **2026-04-23:** `paperforge ocr doctor` uses tiered diagnostics with live provider checks optional.
- **2026-04-23:** v1.1 will use the sandbox first-time-user simulation as a release gate before claiming setup/onboarding reliability.
- **2026-04-24:** v1.2 will unify agent commands under `/pf-*` namespace and simplify CLI commands for cohesion.
- **2026-04-24:** Use importlib.util with sys.modules pre-registration for Python 3.14 dataclass compatibility.
- **2026-04-24:** Generate deterministic OCR fixtures once and commit; never regenerate in CI.
- **2026-04-24:** Rollback in prepare_deep_reading tracks written files and restores original note text, not full filesystem snapshot.
- **2026-04-24:** Unify agent commands under `/pf-*` namespace; deprecate `/LD-*` and `/lp-*` prefixes.
- **2026-04-24:** Simplify CLI by combining `selection-sync` + `index-refresh` into `paperforge sync`.
- **2026-04-24:** Aggressive migration strategy: old commands (`/LD-*`, `/lp-*`) removed entirely with no aliases.
- **2026-04-24:** `paperforge ocr` merges `ocr run` + `ocr doctor`; `--diagnose` for standalone diagnostics.
- **2026-04-24:** Unified command modules in `paperforge/commands/` (formerly `paperforge_lite/commands/`).
- **2026-04-24:** Rename Python package from `paperforge_lite` to `paperforge` for naming consistency.
