# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-23)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Phase 1: Config And Command Foundation -- Plan 01-03 complete

## Current Findings

- The parent `D:\L\Med\Research` already has a separate GSD `.planning`; this release repo uses its own local `.planning`.
- The release repo already supports configurable path names through `paperforge.json`, but user-facing commands still expose placeholders.
- PaddleOCR failures need a dedicated preflight and retry path before deeper workflow work.
- Production Base designs are richer than release-generated Bases and should be parameterized.
- `paperforge_lite/config.py` now provides a tested shared resolver; worker, `/LD-deep`, setup wizard, and validation all consume it (01-03 complete).
- `paperforge` CLI launcher provides copy-pasteable commands with resolved paths.
- All Phase 1 workers and agent commands now delegate to shared resolver: legacy public names preserved.

## Next Action

Continue Phase 1 Plan 01-04: Stable command documentation and setup next-step updates.

## Open Questions

- Confirm the exact PaddleOCR service currently used and whether it expects `Bearer`, `bearer`, API key query params, or another auth contract.
- Decide whether the launcher should be installed as `paperforge`, `pf`, or only exposed via `python -m paperforge_lite`.
- Decide how aggressive Base refresh should be when user-edited `.base` files already exist.

## Phase 1 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 01-01 | done | Shared config resolver (`paperforge_lite/config.py`) and 13-key path inventory |
| 01-02 | done | `paperforge` launcher, package entry point, and command dispatch |
| 01-03 | done | Worker, `/LD-deep`, setup, and validation resolver integration |
| 01-04 | pending | Stable command documentation and setup next-step updates |

**Completed:** 2026-04-23
**Completed Requirements:** CONF-01, CONF-02, CONF-03, CONF-04, CMD-01, CMD-02, CMD-03, DEEP-02

## Decisions Logged

- **2026-04-23:** Config precedence locked as: explicit overrides > env > JSON nested > JSON top-level > defaults
- **2026-04-23:** `paperforge_paths` returns exactly 13 keys; `command_dir` excluded (not user-facing)
- **2026-04-23:** `resolve_vault` walks cwd upward for `paperforge.json` enabling vault-free invocation
- **2026-04-23:** No `os.environ` mutation; `env` is a read-only parameter
- **2026-04-23:** CLI returns int exit codes (not `sys.exit()`) for testability; worker functions imported at module level for patchability
- **2026-04-23:** `load_simple_env` added to config.py for .env loading before worker dispatch
- **2026-04-23 (01-03):** Worker `load_vault_config` and `pipeline_paths` now delegate to `paperforge_lite.config`; `ld_deep._load_vault_config` and `_paperforge_paths` also delegate; setup wizard deploys `paperforge_lite/` package alongside scripts; validate_setup uses shared resolver with `PAPERFORGE_VAULT` first
- **2026-04-23 (01-03):** Public function names preserved as thin wrappers for backward compatibility with existing callers
- **2026-04-23 (01-03):** `pipeline_paths` uses `**shared` dict merge to combine resolver output with worker-only keys (pipeline, candidates, search_*, harvest_root, records, review, config, queue, log, bridge_config*, index, ocr_queue)

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-23 (01-03 complete)*