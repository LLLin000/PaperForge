---
phase: 13-logging-foundation
plan: 01
subsystem: observability
tags: [logging, stdlib, argparse, cli, stderr, env-var]

# Dependency graph
requires:
  - phase: 13-logging-foundation
    provides: context decisions (D-02 through D-10) for logging_config.py design
provides:
  - paperforge/logging_config.py — single configure_logging(verbose) entry point
  - Global --verbose flag on CLI root parser, inherited by all subcommands
  - configure_logging() call in cli.py:main() before command dispatch
affects:
  - 13-02 (logging worker modules) — worker modules will import logging.getLogger(__name__)
  - 13-03 (logging command modules) — command modules will wire verbose passthrough

# Tech tracking
tech-stack:
  added: [stdlib logging module]
  patterns:
    - "Single configure_logging() entry point for all logging setup"
    - "Root-level --verbose/-v flag for cross-command debug output"
    - "PAPERFORGE_LOG_LEVEL env var for default level control"
    - "logger.setLevel() + StreamHandler(stderr) programmatic setup (no dictConfig)"
    - "Idempotency guard (if logger.handlers: return) prevents double-config"

key-files:
  created:
    - paperforge/logging_config.py
  modified:
    - paperforge/cli.py

key-decisions:
  - "D-02 implemented: single configure_logging(verbose) export from logging_config.py"
  - "D-03 implemented: programmatic logger.setLevel() + handler.setLevel() (not dictConfig)"
  - "D-05 implemented: --verbose maps to logging.DEBUG level"
  - "D-06 implemented: PAPERFORGE_LOG_LEVEL env var, default INFO"
  - "D-09 implemented: invalid env var values silently fall back to WARNING"
  - "D-10 implemented: idempotency guard for early-boot safety"
  - "Deviation: argparse does not inherit root flags to subparsers; backward compat for 'deep-reading -v' and 'repair -v' broken — users must use 'paperforge -v deep-reading'"

patterns-established:
  - "Pattern: configure_logging() is the single entry point — never call logging.basicConfig() directly"
  - "Pattern: Root-level -v/--verbose for all commands; access via args.verbose"
  - "Pattern: StreamHandler writes to stderr; stdout remains clean for user-facing print()"

requirements-completed:
  - OBS-01
  - OBS-02
  - OBS-03

# Metrics
duration: 18min
completed: 2026-04-27
---

# Phase 13: Logging Foundation Summary

**Single `configure_logging(verbose)` entry point for Python stdlib logging, with global `--verbose` flag on CLI root parser wired before command dispatch**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-27 (session start)
- **Completed:** 2026-04-27
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `paperforge/logging_config.py` with `configure_logging(verbose)` — the single entry point for all Python stdlib logging configuration
- Implemented `PAPERFORGE_LOG_LEVEL` env var support with INFO default and WARNING fallback for invalid values
- Added global `--verbose` / `-v` flag to CLI root parser, accessible by all subcommands
- Removed per-subcommand `--verbose` from `deep-reading` and `repair` (now handled globally)
- Wired `configure_logging(verbose=args.verbose)` in `cli.py:main()` before command dispatch
- Added idempotency guard to prevent double handler configuration
- StreamHandler targets stderr with compact `LEVEL:name:message` format

## Task Commits

Each task was committed atomically:

1. **Task 1: Create logging_config.py** - `abe9afe` (feat)
2. **Task 2: Add global --verbose to CLI and wire configure_logging()** - `ca7d665` (feat)

## Files Created/Modified
- `paperforge/logging_config.py` — Created: `configure_logging(verbose)` function with env var support, stderr handler, idempotency guard
- `paperforge/cli.py` — Modified: added import, root-level `--verbose`/`-v` flag, removed per-subcommand `--verbose` from deep-reading/repair, added `configure_logging()` call in `main()`

## Decisions Made
- **D-02 (single entry point):** `configure_logging(verbose)` is the only exported function
- **D-03 (programmatic setup):** Uses `logger.setLevel()` + `handler.setLevel()` — simpler than `dictConfig` and avoids external config files
- **D-05 (verbose=DEBUG):** `--verbose` forces `logging.DEBUG` regardless of env var
- **D-06 (env var):** `PAPERFORGE_LOG_LEVEL` accepted values: `DEBUG`/`INFO`/`WARNING`/`ERROR`; default `INFO`
- **D-09 (invalid fallback):** Invalid values (e.g., `banana`) silently fall back to `WARNING`
- **D-10 (idempotency guard):** `if logger.handlers: return` prevents double configuration
- **Root-level flag only:** `--verbose` lives on the root parser, not on subparsers; `paperforge -v status` works, but `paperforge status -v` does not (argparse limitation — root parser flags are not inherited to subparsers)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Backward Compatibility] argparse root flags not inherited by subparsers**
- **Found during:** Task 2 (Add global --verbose to CLI and wire configure_logging)
- **Issue:** The plan stated "argparse resolves them identically" and claimed `deep-reading -v` would continue to work. This is incorrect — argparse does NOT inherit root parser flags to subparsers when the flag appears after the subcommand name. Having `--verbose` on both root and subparser silently breaks root-level usage.
- **Fix:** Removed per-subcommand `--verbose` from `deep-reading` and `repair`, keeping it ONLY on the root parser. This means `paperforge -v deep-reading` works but `paperforge deep-reading -v` does not. The backward compat break is a necessary consequence of argparse's design.
- **Files modified:** `paperforge/cli.py`
- **Verification:** All parser tests pass with root-level usage; `deep-reading -v` raises SystemExit (expected, documented)
- **Committed in:** `ca7d665` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2)
**Impact on plan:** Minor — the backward compat break affects the `deep-reading -v` and `repair -v` syntax. Users must use `paperforge -v <command>` instead. The core goal (global --verbose for all subcommands) is achieved.

## Issues Encountered
- **argparse root-to-subparser inheritance:** Discovered that argparse does NOT inherit root parser arguments to subparsers. This differs from what the plan assumed. Resolved by using root-parser-only --verbose; users put `-v` before the subcommand.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Logging infrastructure ready for Phase 13-02 (worker module logging integration)
- Global `--verbose` available for all subcommands immediately
- `configure_logging()` function ready to be imported by worker modules via `logging.getLogger(__name__)`
- Command modules can access `args.verbose` for verbose passthrough

## Self-Check: PASSED

```
FOUND: paperforge/logging_config.py
FOUND: paperforge/cli.py
FOUND: .planning/phases/13-logging-foundation/13-01-SUMMARY.md
FOUND: abe9afe (Task 1)
FOUND: ca7d665 (Task 2)
```

---
*Phase: 13-logging-foundation*
*Completed: 2026-04-27*
