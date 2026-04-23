---
phase: 01-config-and-command-foundation
plan: 02
subsystem: cli
tags: [argparse, cli, packaging, entrypoint, paperforge]

# Dependency graph
requires:
  - phase: 01-config-and-command-foundation
    provides: config resolver (load_vault_config, resolve_vault, paperforge_paths, paths_as_strings)
provides:
  - paperforge CLI command (python -m paperforge_lite and `paperforge` after editable install)
  - pyproject.toml packaging with [project.scripts] entry point
  - CLI dispatch for status, selection-sync, index-refresh, deep-reading, ocr commands
  - paths command (text and --json output) with resolved absolute paths
affects:
  - Phase 1 remaining plans (03, 04)
  - User onboarding and command documentation

# Tech tracking
tech-stack:
  added: [setuptools, argparse (stdlib)]
  patterns: [CLI subcommand dispatch, fixed command-to-function map (no eval), .env loading before worker dispatch]

key-files:
  created:
    - paperforge_lite/cli.py - argparse CLI with all subcommands
    - paperforge_lite/__main__.py - python -m paperforge_lite entry point
    - paperforge_lite/config.py - load_simple_env added to Plan 01 resolver
    - pyproject.toml - setuptools packaging with paperforge console script
    - tests/test_cli_paths.py - paths command tests (3 tests)
    - tests/test_cli_worker_dispatch.py - worker dispatch tests (6 tests)
  modified:
    - paperforge_lite/config.py - added load_simple_env function

key-decisions:
  - "CLI returns int exit codes rather than calling sys.exit() for testability"
  - "Worker functions imported at module level in cli.py (not lazy) so tests can patch them"
  - "ocr command default action set to 'run' to alias 'ocr' -> 'ocr run' per D-Command Surface"
  - "load_simple_env added to config.py to enable .env loading in CLI before worker dispatch"

patterns-established:
  - "Fixed command-to-function dispatch map (no eval, no shell) for T-01-03 mitigation"
  - "paths --json outputs only contract keys (vault, worker_script, ld_deep_script) to avoid leaking internal paths"
  - ".env files loaded from vault root and <system_dir>/PaperForge/.env before worker dispatch (legacy behavior preserved)"

requirements-completed: [CONF-02, CMD-01, CMD-03]

# Metrics
duration: 11 min
completed: 2026-04-23
---

# Phase 1 Plan 2: Config and Command Foundation Summary

**paperforge CLI launcher with argparse subcommands, pyproject.toml entry point, and load_simple_env .env loader for worker dispatch**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-23T11:33:29Z
- **Completed:** 2026-04-23T11:44:53Z
- **Tasks:** 2 (RED test + GREEN implementation)
- **Files modified:** 8

## Accomplishments
- `paperforge` command installable via `pip install -e .` (pyproject.toml [project.scripts])
- `python -m paperforge_lite` fallback works without editable install
- `paperforge paths --json` emits D-Path Output keys: vault, worker_script, ld_deep_script
- `paperforge paths` (text) emits resolved absolute paths, no unresolved `<system_dir>` or `<resources_dir>` tokens
- `paperforge ocr` and `paperforge ocr run` both dispatch to `run_ocr()` (alias per D-Command Surface)
- All 5 worker commands (status, selection-sync, index-refresh, deep-reading, ocr) dispatch correctly
- .env loading from vault root and `<system_dir>/PaperForge/.env` before worker dispatch (legacy behavior preserved)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): test(01-02): add failing test for CLI paths output and worker dispatch** - `216ea4e` (test)
2. **Task 2 (GREEN): feat(01-02): implement CLI launcher, packaging entry point, and shared config resolver** - `9496382` (feat)

**Plan metadata:** `6dc62ac` (docs: complete plan)

## Files Created/Modified

- `paperforge_lite/cli.py` - argparse CLI with subcommands: paths (--json), status, selection-sync, index-refresh, deep-reading, ocr (default run)
- `paperforge_lite/__main__.py` - entry point for `python -m paperforge_lite`
- `paperforge_lite/__init__.py` - package init (from Plan 01)
- `paperforge_lite/config.py` - added `load_simple_env` to Plan 01 resolver for .env loading
- `pyproject.toml` - setuptools build, paperforge-lite 1.0.0, Python >=3.10, [project.scripts] paperforge="paperforge_lite.cli:main"
- `tests/test_cli_paths.py` - 3 tests for paths command output (JSON and text)
- `tests/test_cli_worker_dispatch.py` - 6 tests for worker dispatch (status, selection-sync, index-refresh, deep-reading, ocr run, ocr alias)

## Decisions Made
- CLI returns int exit codes rather than calling sys.exit() for testability (confirmed by test output)
- Worker functions imported at module level in cli.py (not lazy) so tests can patch them
- `ocr` command default action set to 'run' to alias `ocr` -> `ocr run` per D-Command Surface requirement
- `load_simple_env` added to config.py to enable .env loading in CLI before worker dispatch (Rule 3 - Blocking: missing function prevented CLI from loading .env files)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing load_simple_env function to config.py**
- **Found during:** Task 2 (CLI implementation)
- **Issue:** cli.py imports `load_simple_env` from config.py, but Plan 01's resolver did not include it. Without it, the CLI could not load .env files before worker dispatch.
- **Fix:** Added `load_simple_env()` function to config.py (matching the identical function from literature_pipeline.py), enabling .env loading before worker dispatch
- **Files modified:** paperforge_lite/config.py
- **Verification:** All 31 tests pass (3 path + 6 dispatch + 22 config from Plan 01)
- **Committed in:** 9496382 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was essential - without load_simple_env, the CLI would crash on import and could not load .env files as required by legacy behavior.

## Issues Encountered
- None - plan executed as specified with one auto-fix for missing function

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CLI foundation is complete and tested
- `paperforge` command surface is stable and matches D-Command Surface contract
- Ready for remaining Phase 1 plans (03, 04)

---
*Phase: 01-config-and-command-foundation*
*Completed: 2026-04-23*

## Self-Check: PASSED

- All 8 key files exist on disk
- All 3 commits verified in git history: 216ea4e (test), 9496382 (feat), 767548d (docs)
- 31 tests passing (3 path + 6 dispatch + 22 config from Plan 01)
- `python -m paperforge_lite --vault . paths --json` exits 0, prints valid JSON with required keys
- pyproject.toml contains paperforge entry point
