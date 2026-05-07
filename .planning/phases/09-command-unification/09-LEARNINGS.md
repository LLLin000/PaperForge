---
phase: 09
phase_name: "Command Unification"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 7
  lessons: 4
  patterns: 4
  surprises: 3
missing_artifacts:
  - "VERIFICATION.md"
  - "UAT.md"
---

## Decisions

### D-01: Aggressive migration — no aliases or deprecation for old Agent commands
Old commands (`/LD-*`, `/lp-*`) were completely removed with no aliases or deprecation period. Clean break for v1.2.

**Rationale/Context:** Deprecation warnings add complexity without benefit in a CLI tool with few users. Cleaner to migrate aggressively with clear documentation.  
**Source:** 09-SUMMARY.md (Key Decisions)

### D-02: Unified `paperforge sync` runs both selection-sync and index-refresh
The new `sync` subcommand runs both phases by default. `--selection` and `--index` flags allow partial execution.

**Rationale/Context:** Most users want to run both phases together. The two-step process was an implementation detail leaking into the user interface.  
**Source:** 09-PLAN.md (Task 2) / 09-SUMMARY.md (Key Decisions)

### D-03: Merged `paperforge ocr` combines run + doctor
The new `ocr` subcommand integrates both OCR execution and diagnostics. `--diagnose` flag runs standalone diagnostics.

**Rationale/Context:** `ocr run` and `ocr doctor` were always used together in practice. Merging reduces command surface area.  
**Source:** 09-PLAN.md (Task 2) / 09-SUMMARY.md (Key Decisions)

### D-04: All CLI logic extracted into `paperforge/commands/` modules
Each subcommand has a dedicated module in `paperforge/commands/` exposing a `run(args_namespace)` interface. `cli.py` becomes a thin argparse wrapper.

**Rationale/Context:** Shared logic between CLI and Agent layers requires importable modules, not inline argparse handlers. Enables command reuse.  
**Source:** 09-PLAN.md (Task 1) / 09-SUMMARY.md (Key Decisions)

### D-05: Python package unified under `paperforge` name
Renamed from `paperforge_lite` to `paperforge` across 98+ import statements and 377+ markdown references.

**Rationale/Context:** The `_lite` suffix was a historical artifact. CLI command and Python package should share the same name.  
**Source:** 09-PLAN.md (Task 0) / 09-SUMMARY.md

### D-06: Old command references kept only in migration sections
AGENTS.md and other docs keep old command names (`selection-sync`, `/LD-*`) only in dedicated migration tables, not in primary documentation flow.

**Rationale/Context:** Primary docs should reflect the current interface. Migration references help existing users but shouldn't clutter normal usage sections.  
**Source:** 09-05-SUMMARY.md (Decisions Made)

### D-07: Old CLI commands still function for backward compatibility
`cli.py` preserves backward-compatible aliases for old CLI commands (`selection-sync`, `index-refresh`, `ocr run`), even though docs only show new names.

**Rationale/Context:** Prevents breaking existing user scripts and muscle memory. The aliases are not documented — users are encouraged to migrate.  
**Source:** 09-05-SUMMARY.md (Decisions Made)

---

## Lessons

### L-01: Aggressive rename of 98+ Python imports is feasible when systematic
The package rename from `paperforge_lite` to `paperforge` touched 98+ import statements and 377+ markdown references, but was completed without introducing new failures.

**Rationale/Context:** Systematic search-and-replace with automated verification (running tests, checking imports) makes large renames safe.  
**Source:** 09-SUMMARY.md

### L-02: Backward-compatible CLI aliases prevent breaking existing workflows
Old CLI commands (`selection-sync`, `index-refresh`, `ocr run`) were preserved as aliases, ensuring users' existing scripts and habits continue to work.

**Rationale/Context:** Breaking changes should be opt-in. Backward-compatible aliases allow gradual migration without user disruption.  
**Source:** 09-05-SUMMARY.md (Decisions Made)

### L-03: Automated tests prevent regression of old command names in docs
`TestUnifiedCommandsInUserDocs` catches any accidental re-introduction of old command names in primary documentation sections.

**Rationale/Context:** Without automation, docs can regress when someone copies old text or uses outdated references.  
**Source:** 09-05-SUMMARY.md (Decisions Made)

### L-04: Pre-existing test failures unrelated to command unification
Two test files (`test_pdf_resolver.py`, `test_base_preservation.py`, `test_base_views.py`) had pre-existing failures caused by `pipeline` module import issues, not by Phase 9 changes.

**Rationale/Context:** Important to establish baseline test results before a refactoring phase so new breakage can be distinguished from pre-existing issues.  
**Source:** 09-SUMMARY.md (Known Issues)

---

## Patterns

### P-01: Command module pattern with `run(args)` interface
Each submodule in `paperforge/commands/` exposes a uniform `run(args_namespace)` interface, registered in `__init__.py`.

**When to use:** When building a CLI where commands should be independently importable and testable, and where multiple callers (CLI, Agent, tests) need access.  
**Source:** 09-PLAN.md (Task 1)

### P-02: Thin CLI wrapper pattern
`cli.py` is reduced to argparse dispatch only. All business logic lives in `paperforge/commands/` modules.

**When to use:** When the CLI layer should be a thin adapter, not an application. Keeps command logic reusable across interfaces.  
**Source:** 09-PLAN.md (Task 2) / 09-SUMMARY.md

### P-03: Migration documentation pattern
Old command names appear only in dedicated migration sections (tables, sidebars), not in primary documentation flow.

**When to use:** During any interface migration. Helps existing users transition while keeping new users focused on current syntax.  
**Source:** 09-05-SUMMARY.md (Decisions Made)

### P-04: Registry-based command discovery
`paperforge/commands/__init__.py` acts as a command registry, allowing `cli.py` to discover and dispatch to subcommands without hardcoded import chains.

**When to use:** When the number of subcommands grows and you want a single point of registration rather than scattered imports.  
**Source:** 09-PLAN.md (Task 1)

---

## Surprises

### S-01: Zero deviations from plan across all 6 tasks
Every task was executed exactly as written in the plan. No unexpected issues, no auto-fixes, no scope changes during Task 6 verification.

**Impact:** Positive — demonstrates that the planning process has matured to high accuracy.  
**Source:** 09-SUMMARY.md (Deviation from Plan)

### S-02: 155 tests still pass despite 98+ Python import changes
A massive rename touching almost every Python file in the project didn't break a single passing test.

**Impact:** Positive — systematic rename with verification works. Validates the testing infrastructure's coverage.  
**Source:** 09-SUMMARY.md (Test Results)

### S-03: Pre-existing `pipeline` module import errors in two test files
`test_base_preservation.py` and `test_base_views.py` import from `pipeline.worker.scripts.literature_pipeline` which doesn't exist in the current package structure.

**Impact:** Low — pre-existing issue. Tests were likely created for a different module layout and never updated.  
**Source:** 09-SUMMARY.md (Known Issues)
