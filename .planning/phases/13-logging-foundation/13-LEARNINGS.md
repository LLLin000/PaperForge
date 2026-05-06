---
phase: 13
phase_name: "Logging Foundation"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 11
  lessons: 5
  patterns: 5
  surprises: 1
missing_artifacts:
  - "13-UAT.md"
---

## Decisions

### Single configure_logging(verbose) entry point (D-02)
`paperforge/logging_config.py` exports a single `configure_logging(verbose: bool = False)` function as the only entry point for all logging configuration.

**Rationale/Context:** Prevents scattered `basicConfig()` calls across modules. A single entry point ensures consistent log behavior across all commands.

**Source:** 13-01-PLAN.md (Decision D-02)

---

### Programmatic setup over dictConfig (D-03)
Uses `logger.setLevel()` + `handler.setLevel()` programmatic setup instead of `dictConfig` or `fileConfig`.

**Rationale/Context:** Simpler implementation, no external config files needed, and avoids the complexity of `dictConfig` for a straightforward logging setup.

**Source:** 13-01-PLAN.md (Decision D-03)

---

### --verbose maps to DEBUG level (D-05)
The `--verbose` / `-v` CLI flag forces `logging.DEBUG` level regardless of the `PAPERFORGE_LOG_LEVEL` environment variable.

**Rationale/Context:** Users who explicitly pass `--verbose` want maximum detail, overriding any environment-level configuration. This provides a reliable way to get debug output on demand.

**Source:** 13-01-PLAN.md (Decision D-05)

---

### PAPERFORGE_LOG_LEVEL env var with INFO default (D-06)
Environment variable `PAPERFORGE_LOG_LEVEL` controls default log level. Accepted values: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`.

**Rationale/Context:** Environment-level control allows system administrators and CI scripts to set log verbosity without modifying CLI invocations.

**Source:** 13-01-PLAN.md (Decision D-06)

---

### Invalid env var falls back to WARNING (D-09)
Invalid `PAPERFORGE_LOG_LEVEL` values (e.g., `banana`) silently fall back to `WARNING`.

**Rationale/Context:** A typo in an environment variable should not crash the application. Falling back to a safe, less verbose level is better than failing silently at INFO or raising an error.

**Source:** 13-01-PLAN.md (Decision D-09)

---

### Idempotency guard prevents double configuration (D-10)
`if logger.handlers: return` guard ensures `configure_logging()` is safe to call multiple times.

**Rationale/Context:** Early-boot code may call `logging.basicConfig()` or `configure_logging()` before the CLI's `main()` runs. The idempotency guard prevents duplicate handlers and duplicate log lines.

**Source:** 13-01-PLAN.md (Decision D-10)

---

### StreamHandler targets stderr
The logging StreamHandler writes to `sys.stderr`, not `sys.stdout`.

**Rationale/Context:** Diagnostic output must be separated from user-facing output (OBS-02). Stdout is reserved for `print()` calls that produce command results; stderr carries log messages. This ensures piped commands and redirected output function correctly.

**Source:** 13-01-PLAN.md (Implementation notes)

---

### Formatter: LEVEL:name:message
Log format is `LEVEL:name:message` (e.g., `INFO:paperforge.worker.sync:Starting sync`).

**Rationale/Context:** Compact format is grep-friendly. No timestamps because users see real-time terminal output. The hierarchical logger name (`paperforge.worker.sync`) enables targeted filtering.

**Source:** 13-01-PLAN.md (Implementation notes)

---

### printf-style format strings for all logger calls
All migrated logger calls use `%s`, `%d` formatting instead of f-strings.

**Rationale/Context:** printf-style formatting enables lazy evaluation — if the log level suppresses a message, string formatting is never executed. This is a performance best practice for logging.

**Source:** 13-02-SUMMARY.md (Decisions Made)

---

### verbose=getattr(args, "verbose", False) as safe extraction pattern
All command modules use `getattr(args, "verbose", False)` to extract the verbose flag from argparse namespace.

**Rationale/Context:** Handles the case where `args` might not have a `verbose` attribute (e.g., when command modules are called outside CLI dispatch in tests or offline contexts). The default `False` ensures backward compatibility.

**Source:** 13-03-SUMMARY.md (Decisions Made)

---

### Contract-first verbose parameter in worker functions
Worker functions accept `verbose: bool = False` parameter even when not yet used internally.

**Rationale/Context:** The parameter serves as a contract between command and worker layers. Adding it upfront (before internal implementation) prevents cascading signature changes across all call sites later.

**Source:** 13-03-SUMMARY.md (Decisions Made)

---

## Lessons

### argparse does NOT inherit root parser flags to subparsers
The plan assumed `deep-reading -v` would continue to work after moving `--verbose` to the root parser. This is incorrect — argparse only recognizes root-level flags when they appear BEFORE the subcommand name. `paperforge deep-reading -v` fails; `paperforge -v deep-reading` works.

**Rationale/Context:** This is a fundamental argparse design limitation. The fix was to keep `--verbose` on the root parser only, document the syntax change, and accept the backward compatibility break.

**Source:** 13-01-SUMMARY.md (Deviation 1)

---

### paperforge/update.py (standalone) does not exist
The plan listed `paperforge/update.py` as a target file, but only `paperforge/worker/update.py` exists on disk.

**Rationale/Context:** The plan incorrectly referenced a standalone update module that was never created. The actual update logic lives in the worker module hierarchy. This was discovered during execution and the non-existent file was skipped.

**Source:** 13-02-SUMMARY.md (Deviation 1)

---

### Removing _color() function breaks input() prompt
When `_log()` and `_color()` functions were removed from `worker/update.py`, an `input(_color("确认更新..."))` call remained, referencing the now-deleted `_color()`.

**Rationale/Context:** The code review missed that `_color()` was used not only for logging but also for user prompts. The fix was to replace the colored prompt with plaintext `input("...")`.

**Source:** 13-02-SUMMARY.md (Deviation 2)

---

### 12/12 truths verified across all 3 sub-plans
The final verification confirmed all 12 observable truths from the plan's must-haves, 5/5 ROADMAP success criteria, and all key links as wired.

**Rationale/Context:** Rigorous verification ensures no gaps. The structured must-haves/artifacts/key-links pattern from the plan translated directly into verifiable criteria.

**Source:** 13-VERIFICATION.md (Must-Haves Truths Verification)

---

### 50+ diagnostic print() calls migrated
Across repair.py (10), commands/ocr.py (4), and update.py (36+), the migration replaced scattered diagnostic `print()` calls with structured logging.

**Rationale/Context:** This volume of print-to-logger migration demonstrates the extent of ad-hoc diagnostic output that had accumulated in the codebase. A systematic migration was needed, not a targeted cleanup.

**Source:** 13-VERIFICATION.md (Gaps Summary)

---

## Patterns

### Root-level -v/--verbose for all commands
A single global `--verbose` flag on the root parser is inherited by all subcommands via argparse, eliminating per-subcommand flag duplication.

**Rationale/Context:** Centralizing the flag simplifies argument parsing and ensures consistent behavior across all commands. Users must place `-v` before the subcommand.

**Source:** 13-01-SUMMARY.md (Patterns Established)

---

### configure_logging() as single entry point
Never call `logging.basicConfig()` or `dictConfig()` directly. Always use `configure_logging()` from `paperforge.logging_config`.

**Rationale/Context:** Scattered logging configuration leads to inconsistent behavior (different formats, different levels, duplicate handlers). A single call point ensures determinism.

**Source:** 13-01-SUMMARY.md (Patterns Established)

---

### stdout reserved for user-facing output; stderr for diagnostics
`print()` calls that produce command results go to stdout. All diagnostic/trace/error output goes through logging to stderr.

**Rationale/Context:** (OBS-02) Separating output streams ensures piped commands receive clean data on stdout while diagnostic messages are visible on stderr without polluting pipeline data.

**Source:** 13-01-SUMMARY.md (Patterns Established), 13-VERIFICATION.md (Goal Achievement)

---

### verbose=getattr(args, "verbose", False) standard wiring pattern
All command modules use this exact pattern to extract the verbose flag from argparse and pass it to worker functions.

**Rationale/Context:** Standardized pattern is reviewable, testable, and safe for CLI and non-CLI invocation contexts.

**Source:** 13-03-SUMMARY.md (Patterns Established)

---

### def foo(vault, verbose=False) standard worker signature
All worker functions that accept verbose follow the same signature pattern: `def function_name(vault, verbose: bool = False) -> int:`.

**Rationale/Context:** Consistent signatures across all worker modules reduce cognitive load for developers and enable straightforward automated tooling (e.g., signature introspection for documentation generation).

**Source:** 13-03-SUMMARY.md (Patterns Established)

---

## Surprises

### Argparse root-to-subparser flag inheritance is one-directional
The plan's assumption that moving `--verbose` to the root parser would be transparent was incorrect. argparse does not pass root-level flags to subparsers when the flag appears after the subcommand name. This means `paperforge deep-reading -v` (which worked in v1.3) no longer works. Users must use `paperforge -v deep-reading`.

**Rationale/Context:** This is a known argparse design choice, not a bug. Argparse parses arguments positionally — once the subcommand is consumed, the remaining arguments only match that subparser's definition. The fix required accepting a backward compatibility break, which was a necessary trade-off for the unified flag approach.

**Source:** 13-01-SUMMARY.md (Deviation), 13-VERIFICATION.md (Deviations)
