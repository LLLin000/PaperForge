---
phase: 06
phase_name: "Setup CLI Diagnostics Consistency"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 7
  lessons: 4
  patterns: 3
  surprises: 2
missing_artifacts:
  - "VERIFICATION.md"
  - "UAT.md"
---

## Decisions

### D-01: Use `ld_deep_script` as canonical field name
Consistently use `ld_deep_script` (not `literature_script`) in command documents to match `paperforge paths --json` output.

**Rationale/Context:** Field name drift between docs and actual config output caused Agent confusion. D-02, D-03 from CONTEXT.md locked the name.  
**Source:** 06-01-PLAN.md (Task 1)

### D-02: `python -m paperforge` as documented fallback
When `paperforge` CLI command is not registered (e.g., user hasn't run `pip install`), `python -m paperforge` is the documented alternative.

**Rationale/Context:** Provides a universal fallback that doesn't require PYTHONPATH or pip installation. D-16, D-17 from CONTEXT.md.  
**Source:** 06-01-PLAN.md (Task 2)

### D-03: HTTP 405 "Method Not Allowed" gets distinct diagnostic message
Doctor L2 check distinguishes HTTP 405 from other HTTP errors with an actionable message about method mismatch (GET vs POST).

**Rationale/Context:** Generic "HTTP error" message didn't help users fix 405 issues. D-10, D-11, D-12 from CONTEXT.md.  
**Source:** 06-01-PLAN.md (Task 3)

### D-04: Doctor validates all `*.json` exports, not only `library.json`
The doctor's export validation uses `glob("*.json")` instead of checking for a single hardcoded `library.json`.

**Rationale/Context:** BBT can generate per-domain JSON files; requiring `library.json` specifically was too restrictive. D-07, D-08, D-09 from CONTEXT.md.  
**Source:** 06-02-PLAN.md (Task 1)

### D-05: Vault path prefilled from `--vault` CLI argument into wizard
`setup_wizard.py` passes the `--vault` command-line argument through to `VaultStep` to prefill the input widget.

**Rationale/Context:** Users had to re-type the vault path in the wizard UI even when specified on the command line. D-13, D-14, D-15 from CONTEXT.md.  
**Source:** 06-02-PLAN.md (Task 2)

### D-06: Doctor uses `paperforge_paths()` resolver for path reporting
The doctor reports `worker_script` path via the same `paperforge_paths()` resolver used by `paperforge paths --json`.

**Rationale/Context:** Hardcoded paths in doctor could drift from actual config. Using the central resolver ensures consistency. D-18, D-19 from CONTEXT.md.  
**Source:** 06-02-PLAN.md (Task 3)

### D-07: `PADDLEOCR_API_TOKEN` is canonical env var name
All three system components (setup wizard, worker, doctor) consistently use `PADDLEOCR_API_TOKEN` for the API token.

**Rationale/Context:** Env var names had drift between components. D-04, D-05, D-06 from CONTEXT.md locked the canonical name.  
**Source:** 06-02-PLAN.md (Task 3)

---

## Lessons

### L-01: Doctor was too restrictive on JSON export validation
The doctor's export check only validated `library.json`, but Better BibTeX can generate per-domain `*.json` files. This caused false "missing export" warnings when `library.json` didn't exist but other JSON files were present.

**Rationale/Context:** Previous implementation assumed a single `library.json` was the only valid export format. BBT's per-domain export feature was missed.  
**Source:** 06-02-PLAN.md (Task 1) / 06-02-SUMMARY.md (Task 1)

### L-02: Vault path wasn't propagating through setup wizard
The `--vault` CLI argument was accepted but not actually passed to the InteractiveTextUI's VaultStep, forcing users to manually re-enter paths.

**Rationale/Context:** `SetupWizardApp.__init__` stored the vault parameter but didn't forward it to VaultStep's compose method.  
**Source:** 06-02-PLAN.md (Task 2) / 06-02-SUMMARY.md (Task 2)

### L-03: Environment variable name drift across components
Different parts of the system used different names for the same API token env var (e.g., `TOKEN` vs `KEY` vs `PADDLEOCR_API_TOKEN`).

**Rationale/Context:** Independent development without cross-component naming conventions caused inconsistency.  
**Source:** 06-02-PLAN.md (Task 3) / 06-02-SUMMARY.md (Task 3)

### L-04: ProgressBar "stall" was a terminal display issue, not a logic bug
The wizard's ProgressBar appeared to "stall" because of terminal rendering behavior, not because the underlying step transitions were missing.

**Rationale/Context:** Confirmed in D-15 that ProgressBar exists and advances correctly; the visual stall is a display artifact.  
**Source:** 06-02-PLAN.md (Task 2, D-15)

---

## Patterns

### P-01: Independent doc fixes parallelized across waves
Multiple small doc fixes (field name, fallback command) are grouped into an independent wave that doesn't block other work.

**When to use:** When tasks modify different files with no shared dependencies, execute them in parallel.  
**Source:** 06-01-PLAN.md (overview: "independent doc fixes")

### P-02: Glob-based validation over hardcoded filenames
Using `glob("*.json")` instead of `Path("library.json").exists()` future-proofs against changes in export format.

**When to use:** When validating file existence in directories that may contain multiple valid files of a type.  
**Source:** 06-02-PLAN.md (Task 1) / 06-02-SUMMARY.md (Task 1)

### P-03: Centralized path resolver for cross-component consistency
`paperforge_paths()` serves as the single source of truth for script paths across doctor, CLI, and configuration.

**When to use:** When multiple components need to reference the same filesystem paths. One resolver, one contract.  
**Source:** 06-02-PLAN.md (Task 3)

---

## Surprises

### S-01: `literature_script` field name survived in docs after refactoring
Despite previous work, the incorrect field name `literature_script` was still present in `command/ld-deep.md` lines 170 and 194.

**Impact:** Low — caused Agent command failures but no data loss. Fixed by replacing 2 occurrences.  
**Source:** 06-01-PLAN.md (Task 1)

### S-02: JSON export validation was checking only `library.json`
The doctor assumed `library.json` was the only valid BBT export, but BBT can generate per-domain JSON files. The single-file check was too restrictive.

**Impact:** Medium — caused false positive "missing export" warnings for users using per-domain export configuration.  
**Source:** 06-02-PLAN.md (Task 1) / 06-02-SUMMARY.md (Task 1)
