---
phase: 48-textual-tui-removal
plans:
  - "001 — TUI Code Removal (DEPR-01, DEPR-03)"
  - "002 — Documentation Updates (DEPR-02)"
subsystem: setup-wizard
tags:
  - textual
  - setup-wizard
  - headless
  - deprecation
  - dependency-cleanup
dependency-graph:
  requires: []
  provides:
    - TUI-removed setup_wizard.py
    - Headless-only setup workflow
    - Clean dependency tree (no textual)
    - Updated documentation
  affects:
    - paperforge.setup_wizard
    - paperforge.cli
    - pyproject.toml
    - docs/setup-guide.md
    - docs/INSTALLATION.md
    - scripts/validate_setup.py
tech-stack:
  added: []
  removed:
    - textual>=0.47.0
  patterns:
    - "`paperforge setup` (bare) now prints help message instead of launching TUI"
    - "All documentation uses `--headless` exclusively"
key-files:
  created:
    - ".planning/phases/48-textual-tui-removal/deferred-items.md"
  modified:
    - "paperforge/setup_wizard.py"  # -1187 lines, TUI removed
    - "paperforge/cli.py"           # help text updated
    - "pyproject.toml"              # textual removed from deps
    - "scripts/validate_setup.py"   # textual removed from check
    - "docs/setup-guide.md"         # headless-only workflow
    - "docs/INSTALLATION.md"        # headless-only commands
metrics:
  duration: ~15 min
  completed_date: "2026-05-07"
  tasks_completed: 5
  lines_added: 61
  lines_deleted: 1262
  files_modified: 6
---

# Phase 48: Textual TUI Removal — Summary

**One-liner:** Removed all 1187 lines of broken Textual TUI from setup_wizard.py, replaced main() with help-message redirect, purged textual dependency, and updated all documentation to headless-only.

## Objectives

Three requirements from milestone v1.11:

| Req | Description | Status |
|-----|-------------|--------|
| DEPR-01 | Remove broken Textual TUI code | DONE |
| DEPR-02 | Update docs to headless-only | DONE |
| DEPR-03 | Remove textual from project deps | DONE |

## Plan 48-001: TUI Code Removal

### Task 1 — Surgical TUI removal from setup_wizard.py
- Removed all `from textual` imports (BLOCK A: lines 30-43)
- Removed all TUI classes: `StepScreen`, `WelcomeStep`, `AgentPlatformStep`, `PythonStep`, `VaultStep`, `ZoteroStep`, `BBTStep`, `JsonStep`, `DeployStep`, `DoneStep`, `StepPassed`, `RestartWizard`, `SetupWizardApp` (BLOCK B: lines 436-1575)
- Removed `STEP_TITLES`, `STEP_IDS` constants (lines 421-433)
- Replaced `main()` with help-message printing redirect (BLOCK C)
- **Preserved:** `headless_setup()`, `EnvChecker`, `CheckResult`, `AGENT_CONFIGS`, `_find_vault`, `_copy_file_incremental`, `_merge_env_incremental`, `_write_text_incremental`, `_copy_tree_incremental`, `_substitute_vars`, `_deploy_skill_directory`, `_deploy_flat_command`, `_deploy_rules_file`
- File went from 2261 to 1094 lines (-1187, -52%)

### Task 2 — CLI help text update
- Updated `paperforge setup` parser help from "Run the setup wizard (Textual-based)" to "Set up PaperForge in a vault (use --headless for non-interactive)"
- No `--non-interactive` option existed — nothing to remove
- All `--headless` arguments preserved and functional

### Task 3 — Dependency cleanup
- Removed `"textual>=0.47.0"` from `pyproject.toml` dependencies
- Removed `"textual": "textual"` from `scripts/validate_setup.py` required dict
- 6 dependencies remain: requests, pymupdf, pillow, tenacity, tqdm, filelock

## Plan 48-002: Documentation Updates

### Task 1 — setup-guide.md
- Replaced bare `paperforge setup` with `paperforge setup --headless` in all 4 locations
- Rewrote Section 3 to describe headless-only workflow (no TUI wizard steps)
- Updated command reference table at Section 7.1

### Task 2 — INSTALLATION.md
- Updated setup command to include `--headless --agent opencode --paddleocr-key <your-key>`
- Updated description to reflect headless-only workflow
- Updated Better BibTeX section reference

## Verification Results

| Check | Result |
|-------|--------|
| `rg "from textual" paperforge/setup_wizard.py` | PASS — zero hits |
| All TUI class names removed (11 classes) | PASS — none remain |
| All preserved items present (7 items) | PASS — all verified |
| `main()` prints help with `--headless` redirect | PASS |
| `from paperforge.setup_wizard import headless_setup` | PASS — no ImportError |
| `py_compile.compile(setup_wizard.py)` | PASS — syntax valid |
| `pytest tests/test_setup_wizard.py -q` | PASS — 40/40 passed |
| `pytest tests/ -q` | 478/480 passed (2 pre-existing failures) |
| No bare `paperforge setup` refs in docs | PASS — all use `--headless` |

## Deviations from Plan

### Auto-fixed Issues

**None** — plan executed exactly as written. No deviations needed.

### Pre-existing Issues (logged as deferred)

**1. [Out of Scope] 2 pre-existing OCR state machine test failures**
- `test_retry_exhaustion_becomes_error`: expects `"error"` but got `"blocked"`
- `test_full_cycle_from_pending_to_done`: expects `"done"` but got `"queued"`
- Logged to `deferred-items.md` — unrelated to TUI removal.

## Decisions Made

- **File path reconciliation:** Plan references `paperforge/setup_wizard.py` (correct) and `paperforge/worker/setup_wizard.py` (incorrect). Used actual file path `paperforge/setup_wizard.py`.
- **Step constants removal:** `STEP_TITLES` and `STEP_IDS` were removed along with TUI code since they're only used by TUI classes. Not explicitly stated in plan but logically required.
- **Deferred pre-existing failures:** Two OCR state machine test failures predated TUI removal. Logged to `deferred-items.md` per deviation rules.

## Commits

| Task | Hash | Description |
|------|------|-------------|
| Plan 001, Task 1 | `2d66a2a` | feat: remove Textual TUI code from setup_wizard.py |
| Plan 001, Tasks 2-3 | `ac3095e` | feat: update CLI help and remove textual dependency |
| Plan 002, Tasks 1-2 | `5abcb7b` | docs: update docs for headless-only setup |
