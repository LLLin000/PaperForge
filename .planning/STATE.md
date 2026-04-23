# State: PaperForge Lite Release Hardening

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-23)

**Core value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

**Current focus:** Phase 1: Config And Command Foundation — Plan 01-01 complete

## Current Findings

- The parent `D:\L\Med\Research` already has a separate GSD `.planning`; this release repo uses its own local `.planning`.
- The release repo already supports configurable path names through `paperforge.json`, but user-facing commands still expose placeholders.
- PaddleOCR failures need a dedicated preflight and retry path before deeper workflow work.
- Production Base designs are richer than release-generated Bases and should be parameterized.
- `paperforge_lite/config.py` now provides a tested shared resolver; remaining Phase 1 plans must integrate worker and `/LD-deep` to use it.

## Next Action

Continue Phase 1 Plan 01-02: `paperforge` launcher, package entry point, and command dispatch.

## Open Questions

- Confirm the exact PaddleOCR service currently used and whether it expects `Bearer`, `bearer`, API key query params, or another auth contract.
- Decide whether the launcher should be installed as `paperforge`, `pf`, or only exposed via `python -m paperforge_lite`.
- Decide how aggressive Base refresh should be when user-edited `.base` files already exist.

## Phase 1 Progress

| Plan | Status | Summary |
|------|--------|---------|
| 01-01 | done | Shared config resolver (`paperforge_lite/config.py`) and 13-key path inventory |
| 01-02 | pending | `paperforge` launcher, package entry point, and command dispatch |
| 01-03 | pending | Worker, `/LD-deep`, setup, and validation resolver integration |
| 01-04 | pending | Stable command documentation and setup next-step updates |

**Completed:** 2026-04-23
**Completed Requirements:** CONF-01, CONF-02, CONF-03, CONF-04

## Decisions Logged

- **2026-04-23:** Config precedence locked as: explicit overrides > env > JSON nested > JSON top-level > defaults
- **2026-04-23:** `paperforge_paths` returns exactly 13 keys; `command_dir` excluded (not user-facing)
- **2026-04-23:** `resolve_vault` walks cwd upward for `paperforge.json` enabling vault-free invocation
- **2026-04-23:** No `os.environ` mutation; `env` is a read-only parameter

---
*Initialized: 2026-04-23*
*Last updated: 2026-04-23 (01-01 complete)*
