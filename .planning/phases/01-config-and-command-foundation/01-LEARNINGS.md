---
phase: 01
phase_name: "Config and Command Foundation"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 14
  lessons: 5
  patterns: 8
  surprises: 6
missing_artifacts:
  - "UAT.md"
---

# Phase 01 Learnings: Config and Command Foundation

## Decisions

### D1: Config Precedence Hierarchy (Locked)
The merged config follows a strict layered order: explicit overrides > environment variables > JSON nested `vault_config` > JSON top-level keys > built-in defaults. This was locked as the D-Configuration Hierarchy in Plan 01-01 and never revisited.

**Rationale:** Multiple config sources (paperforge.json, env vars, CLI arguments) needed an unambiguous resolution order. The hierarchy ensures that a user's `PAPERFORGE_SYSTEM_DIR` env var always beats their paperforge.json setting, and explicit programmatic overrides beat everything.

**Source:** 01-01-PLAN.md, 01-01-SUMMARY.md

---

### D2: 13-Key Path Inventory (Fixed Contract)
`paperforge_paths()` returns exactly 13 keys: `vault`, `system`, `paperforge`, `exports`, `ocr`, `resources`, `literature`, `control`, `library_records`, `bases`, `worker_script`, `skill_dir`, `ld_deep_script`. `command_dir` was intentionally excluded (not a user-facing diagnostic path).

**Rationale:** Every downstream consumer (worker, agent, setup, validation, CLI) needed the same path dictionary shape. A fixed contract prevents key drift across 7+ modules.

**Source:** 01-01-PLAN.md, 01-01-SUMMARY.md

---

### D3: resolve_vault Walks cwd Upward for paperforge.json
The vault root is discovered by searching upward from the current directory for a `paperforge.json` file, enabling `--vault`-free CLI invocation.

**Rationale:** Reduces friction — users shouldn't need to pass `--vault` every time they run a command from inside their vault. Falls back to explicit `--vault`, then `PAPERFORGE_VAULT` env, then cwd.

**Source:** 01-01-SUMMARY.md

---

### D4: No os.environ Mutation
The resolver accepts an optional `env` dict parameter and never mutates global `os.environ`. All config loading is a pure function of its inputs.

**Rationale:** Testability and safety — tests can pass custom env dicts without global side effects. Prevents accidental credential leakage or config mutation across calls.

**Source:** 01-01-SUMMARY.md

---

### D5: CLI Returns int Exit Codes (Not sys.exit)
`cli.main()` returns an integer exit code rather than calling `sys.exit()` directly.

**Rationale:** Testability — tests can inspect the return code without catching SystemExit exceptions. The `__main__.py` wrapper is the sole caller of `sys.exit()`.

**Source:** 01-02-SUMMARY.md

---

### D6: Module-Level Worker Imports in CLI
Worker functions (`run_status`, `run_selection_sync`, etc.) are imported at module level in `cli.py`, not lazily.

**Rationale:** Tests can monkeypatch worker functions before importing `cli.main`, enabling dispatch verification without invoking real workers. Lazy imports would make patching unreliable.

**Source:** 01-02-SUMMARY.md

---

### D7: `ocr` Aliases to `ocr run` by Default
The `ocr` subcommand has its default action set to `run`, so `paperforge ocr` and `paperforge ocr run` dispatch identically.

**Rationale:** Per D-Command Surface requirements — "ocr" alone should trigger the most common operation (running OCR). Reduces user confusion about required sub-subcommands.

**Source:** 01-02-SUMMARY.md

---

### D8: load_simple_env Added to config.py (Not in Original Scope)
`.env` file loading was added to `paperforge/config.py` during Plan 01-02 because the CLI needed to load environment variables before dispatching to workers.

**Rationale:** The original Plan 01-01 resolver omitted `.env` loading, but the legacy worker always loaded `.env` files before execution. The CLI needed the same behavior to preserve backward compatibility.

**Source:** 01-02-SUMMARY.md (Deviations)

---

### D9: Delegate-Wrapper Pattern for Backward Compatibility
Legacy public function names (`load_vault_config`, `pipeline_paths` in worker; `_load_vault_config`, `_paperforge_paths` in ld_deep) were preserved as thin wrappers that delegate to `paperforge.config`.

**Rationale:** Direct legacy invocation (`python literature_pipeline.py --vault . status`) must continue working. The wrapper pattern keeps the public API stable while centralizing resolver logic.

**Source:** 01-03-SUMMARY.md

---

### D10: `**shared` Dict Merge for Worker-Only Keys
`pipeline_paths()` uses `**shared` dict merge to combine the shared resolver's 13 keys with worker-only keys (`pipeline`, `candidates`, `search_*`, `harvest_root`, `records`, `review`, `config`, `queue`, `log`, `bridge_config*`, `index`, `ocr_queue`).

**Rationale:** Worker modules need additional paths beyond the shared contract. The merge approach avoids key collision because shared uses `library_records` while worker uses `records` and `pipeline`.

**Source:** 01-03-SUMMARY.md

---

### D11: Parallel Package Deployment in Setup Wizard
`setup_wizard.py` copies the `paperforge/` package to two locations: `<pf_path>/worker/paperforge/` and `<skill_dir>/literature-qa/paperforge/`.

**Rationale:** Both the worker script and the ld_deep agent script need to import `paperforge.config`. Copying to both locations ensures either can import the package regardless of which script is invoked.

**Source:** 01-03-SUMMARY.md

---

### D12: Legacy Fallback in validate_setup.py
`validate_setup.py` tries to import `paperforge.config` first, and falls back to legacy JSON parsing if the shared resolver is unavailable (for pre-Phase-1 installations).

**Rationale:** Users who haven't yet run `pip install -e .` or had the package deployed by setup_wizard still need validation to work.

**Source:** 01-03-SUMMARY.md

---

### D13: Stable-Command-First Documentation Strategy
Primary user-facing docs show `paperforge status|selection-sync|index-refresh|ocr run|deep-reading` as the main commands. Legacy `python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py` is retained as a documented fallback with path-resolution instructions.

**Rationale:** New users should never see unresolved path tokens (`<system_dir>`) as their primary way to run commands. But existing users who know the old invocation pattern need continued support.

**Source:** 01-04-SUMMARY.md

---

### D14: Documentation Test Scope Excludes Architecture Diagrams
`tests/test_command_docs.py` checks user-run code blocks for stable commands but explicitly skips AGENTS.md frontmatter examples, architecture diagrams, and field reference tables.

**Rationale:** These non-user-run sections legitimately reference internal paths and field names. The Phase 1 scope was to update user-facing commands, not to rewrite the entire architecture documentation.

**Source:** 01-04-SUMMARY.md

---

## Lessons

### L1: Missing load_simple_env Was a Planning Gap
During Plan 01-02 implementation, the CLI import failed because `cli.py` needed `load_simple_env` from `config.py`, but Plan 01-01's resolver contract didn't include it.

**Context:** The legacy worker always called `load_simple_env()` before dispatching commands to load `.env` files. The planning phase didn't trace this dependency fully. Auto-fixed during implementation by adding the function to config.py.

**Source:** 01-02-SUMMARY.md (Deviations section)

---

### L2: Standalone Scripts Require Special Import Handling
`literature_pipeline.py` and `ld_deep.py` are standalone scripts (no `__init__.py`), which meant tests couldn't use standard `import` statements. Required `importlib.util.spec_from_file_location` to load them as modules.

**Context:** Tests needed to import these scripts to verify their wrapper functions delegate to the shared resolver, but Python's import system treats them as scripts, not modules.

**Source:** 01-03-SUMMARY.md (Issues Encountered)

---

### L3: Subprocess Tests Need Explicit PYTHONPATH
The subprocess smoke test (`python literature_pipeline.py --vault . status`) initially failed with `ModuleNotFoundError: No module named 'paperforge'` because `paperforge` wasn't on the subprocess's Python path.

**Context:** The test needed to simulate the installed-package scenario. Fixed by passing `PYTHONPATH` env var to the subprocess, which mirrors how an editable install would make the package available.

**Source:** 01-03-SUMMARY.md (Issues Encountered)

---

### L4: TDD-for-Docs Creates Temporary State Where Docs Reference Non-Existent Commands
Plan 01-04 wrote documentation tests AND updated docs in the same plan, but the SUMMARY noted that "the actual CLI module does not exist in this repo yet" — documentation was updated before the CLI was fully implemented across all phases.

**Context:** The TDD-for-docs pattern ensures tests catch regressions, but the doc content itself references commands that were only partially wired at the time of writing.

**Source:** 01-04-SUMMARY.md (Next Phase Readiness)

---

### L5: Well-Scoped Plans Execute with Near-Zero Deviations
All 4 sub-plans executed essentially as written. Plans 01-01, 01-03, and 01-04 had zero deviations from the plan. Plan 01-02 had one auto-fixed blocking deviation (L1 above). This suggests the planning phase had high precision.

**Context:** This was the first phase of the PaperForge release hardening project. The high planning accuracy established confidence in the GSD methodology for subsequent phases.

**Source:** All four SUMMARY.md files

---

## Patterns

### P1: Delegate-Wrapper Pattern
Preserve existing public API function names but replace their implementation bodies with thin wrappers that delegate to the shared module. The function signatures stay identical; only the internals change.

**When to use:** When migrating existing code to a shared library while preserving backward compatibility for direct invocation and existing callers.

**Source:** 01-03-SUMMARY.md

---

### P2: Parallel Package Deployment
Copy the shared utility package to each script's adjacent directory so that standalone scripts in different directory trees can all import the same library without requiring pip installation or PYTHONPATH manipulation.

**When to use:** When deploying a Python package to a vault or runtime environment where `pip install` is not always available or reliable.

**Source:** 01-03-SUMMARY.md

---

### P3: stdlib-Only Layered Merge Resolver
Build configuration resolution using only stdlib (`json`, `os`, `pathlib`) with a deterministic layered merge: hardcoded defaults → JSON file → environment variables → explicit overrides. Each layer overwrites keys from previous layers.

**When to use:** For local-first CLI tools that need configurable paths with clear precedence, without pulling in config management libraries.

**Source:** 01-01-SUMMARY.md

---

### P4: Upward-Directory Vault Discovery
Discover the project root by searching upward from cwd for a sentinel file (`paperforge.json`). Fall back through explicit CLI argument, then environment variable, then cwd itself.

**When to use:** For CLI tools that operate within a project directory but may be invoked from any subdirectory.

**Source:** 01-01-SUMMARY.md

---

### P5: Fixed Command-to-Function Dispatch Map
Use a static dictionary mapping command name strings to handler functions rather than dynamically evaluating command names or constructing shell commands.

**When to use:** Any CLI that dispatches user-provided subcommand names to handler functions — mitigates code injection and improves auditability.

**Source:** 01-02-PLAN.md, 01-02-SUMMARY.md

---

### P6: paths --json as Machine-Parseable Contract
The `paths --json` subcommand outputs only the key contract keys (not all internal paths), producing valid JSON that scripts and tools can consume programmatically.

**When to use:** When CLI output needs to be consumed by automation scripts, CI pipelines, or agent helpers that need resolved paths.

**Source:** 01-02-SUMMARY.md

---

### P7: Stable-Command-First Documentation
In user-facing docs, present the new stable launcher command as the primary example, with the legacy invocation shown as a clearly labeled fallback with path-resolution instructions using `paperforge paths --json`.

**When to use:** When migrating documentation from a legacy command surface to a new one — gives new users the clean path while supporting existing users.

**Source:** 01-04-SUMMARY.md

---

### P8: TDD for Documentation
Write tests that assert specific content must exist (or must NOT exist) in documentation files before editing the docs. This creates a regression safety net that catches documentation drift in future changes.

**When to use:** When documentation is critical enough that regressions (unresolved tokens, outdated commands) would break the user experience.

**Source:** 01-04-SUMMARY.md

---

## Surprises

### S1: All Config Tests Passed on First Implementation Attempt
After writing 22 failing tests (TDD RED), the full `config.py` implementation passed all 22 on the first run. No iterative debugging or refactoring was needed.

**Impact:** Plan 01-01 completed in just 8 minutes. The planning phase (RESEARCH.md, CONTEXT.md, D-Configuration Hierarchy) was thorough enough that the implementation was essentially transcription.

**Source:** 01-01-SUMMARY.md

---

### S2: load_simple_env Blocking Gap Escaped Planning Phase
The `.env` file loading function was omitted from the Plan 01-01 resolver contract but was required by Plan 01-02's CLI implementation. This dependency was not traced during the multi-source coverage audit.

**Impact:** Plan 01-02 had its only deviation — a blocking auto-fix that added the function to config.py. The planning audit tracked 9 requirement-to-plan mappings but missed the `.env` → CLI dependency chain.

**Source:** 01-02-SUMMARY.md (Deviations)

---

### S3: Script-vs-Module Import Distinction Required Test Adaptation
The worker and ld_deep scripts are standalone executables without `__init__.py`, which meant standard `import` statements couldn't load them in tests. Required `importlib.util.spec_from_file_location` workaround.

**Impact:** Moderate test code complexity — the import pattern is non-standard and less readable than normal imports. This is a structural issue that could be revisited if these scripts are converted to proper modules.

**Source:** 01-03-SUMMARY.md (Issues Encountered)

---

### S4: Subprocess Environment Isolation Was an Unanticipated Test Requirement
The legacy worker invocation smoke test required explicit `PYTHONPATH` injection because subprocesses don't inherit the test process's Python path configuration.

**Impact:** This wasn't described in the test design but was caught immediately during implementation. The fix was straightforward (pass `PYTHONPATH` env to subprocess), but the need for it wasn't anticipated.

**Source:** 01-03-SUMMARY.md (Issues Encountered)

---

### S5: Full Phase Completed in ~38 Minutes — Faster Than Expected
The combined duration of all 4 sub-plans was approximately 38 minutes (8 + 11 + 15 + 4.5). For a phase touching 7 modules and producing 58 tests across 6 test files, this was faster than typical phase estimates.

**Impact:** Demonstrated that the GSD planning methodology (RESEARCH → CONTEXT → PLAN → EXECUTE) with clear dependency graphs between sub-plans produces high-velocity execution. The sequential dependency chain (01→02→03→04) didn't create bottlenecks because each plan was independently scoped.

**Source:** All four SUMMARY.md duration metrics

---

### S6: 01-VERIFICATION.md Confirmed 8/8 Truths with Zero Gaps
The post-hoc verification scan found that all 8 observable truths were satisfied, all 14 required artifacts existed, all 9 key links were wired, and all 8 requirements were satisfied. Zero anti-patterns or gaps were found.

**Impact:** The phase achieved 100% requirement coverage with no deferred items, no TODO placeholders, and no partial implementations. This level of completeness was not guaranteed at the planning stage.

**Source:** 01-VERIFICATION.md
