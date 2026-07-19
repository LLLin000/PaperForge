# Phase 09 Plan: Command Unification & CLI Simplification

## Goal
Systematize the command interface: unify agent commands under `/pf-*`, simplify CLI commands, create shared command modules, unify Python package naming.

## Reference
- Context: `.planning/phases/09-command-unification/09-CONTEXT.md`
- Discussion Log: `.planning/phases/09-command-unification/09-DISCUSSION-LOG.md`
- Requirements: `.planning/REQUIREMENTS-v1.2.md` (SYS-01, SYS-02, SYS-03)

## Tasks

### Task 0: Rename Python Package (`paperforge` → `paperforge`)
**Goal:** Unify Python package name with CLI command name.

**Files to rename/move:**
- `paperforge/` → `paperforge/`

**Files to update:**
- `pyproject.toml` — update `name`, `packages`, `entry_points`, `package-data`
- All Python imports (98 occurrences) — `from paperforge...` → `from paperforge...`
- All markdown references (377 occurrences)
- `AGENTS.md` — update `python -m paperforge` → `python -m paperforge`
- `tests/*.py` — update imports

**Verification:**
- `pip install -e .` succeeds
- `python -m paperforge --help` works
- `from paperforge.cli import main` imports correctly
- All tests pass

### Task 1: Create Shared Command Modules
**Goal:** Extract command logic from cli.py into reusable modules.

**Files to create:**
- `paperforge/commands/__init__.py` — Package init with command registry
- `paperforge/commands/sync.py` — `selection_sync()` + `index_refresh()` + unified `sync()`
- `paperforge/commands/ocr.py` — `run_ocr()` + `diagnose_ocr()` + unified `ocr()`
- `paperforge/commands/deep.py` — `deep_reading_queue()`
- `paperforge/commands/repair.py` — `run_repair()`
- `paperforge/commands/status.py` — `show_status()`

**Key design:**
- Each module exposes `run(args_namespace)` interface
- Extract logic from existing cli.py functions without changing behavior
- Keep existing validation and error handling

**Verification:**
- All existing CLI tests still pass
- Commands can be imported: `from paperforge.commands.sync import sync`

### Task 2: Refactor CLI to Use Command Modules
**Goal:** Rewrite cli.py as thin argparse wrapper around commands/.

**Files to modify:**
- `paperforge/cli.py`

**Changes:**
- Replace inline command implementations with `from .commands import ...`
- Add new subcommands:
  - `paperforge sync [--dry-run] [--domain DOMAIN] [--selection] [--index]`
  - `paperforge ocr [--diagnose] [--key KEY]`
- Keep existing subcommands for backward compatibility during transition
- Add `paperforge doctor` → alias for `ocr --diagnose`

**Verification:**
- `paperforge --help` shows new commands
- `paperforge sync --dry-run` previews without executing
- All smoke tests pass

### Task 3: Create New Agent Command Docs
**Goal:** Write `/pf-*` command documentation.

**Files to create:**
- `command/pf-deep.md` — replaces `/LD-deep`
- `command/pf-paper.md` — replaces `/LD-paper`
- `command/pf-ocr.md` — replaces `/lp-ocr`
- `command/pf-sync.md` — replaces `/lp-selection-sync` + `/lp-index-refresh`
- `command/pf-status.md` — replaces `/lp-status`

**Content guidelines:**
- Use `/pf-*` prefix in headers
- Reference `python -m paperforge <cmd>` for execution
- Update variable names (e.g., `{{SCRIPT}}` path references)
- Maintain same functional descriptions as old docs

**Verification:**
- All new docs are parseable markdown
- Commands are discoverable by Agent

### Task 4: Remove Old Command Docs
**Goal:** Delete deprecated command documentation.

**Files to delete:**
- `command/ld-deep.md`
- `command/ld-paper.md`
- `command/lp-ocr.md`
- `command/lp-index-refresh.md`
- `command/lp-selection-sync.md`
- `command/lp-status.md`

**Verification:**
- No references to `/LD-*` or `/lp-*` remain in repo
- `grep -r "LD-deep\|lp-ocr\|lp-index\|lp-selection\|lp-status" .` returns nothing (except git history)

### Task 5: Update AGENTS.md and Tests
**Goal:** Update system documentation and tests for new command names.

**Files to modify:**
- `AGENTS.md` — Update command reference table
- `tests/test_smoke.py` — Update command invocations
- `tests/test_cli.py` (if exists) — Update test cases

**Changes:**
- Replace `paperforge selection-sync` → `paperforge sync`
- Replace `paperforge index-refresh` → `paperforge sync`
- Replace `paperforge ocr run` → `paperforge ocr`
- Update Agent command examples from `/LD-*` → `/pf-*`
- Update Python package references

**Verification:**
- All tests pass
- AGENTS.md accurately reflects current commands

### Task 6: Verification & Cleanup
**Goal:** Full system verification.

**Steps:**
1. Run full test suite
2. Verify CLI help output
3. Spot-check command execution
4. Update STATE.md
5. Create 09-SUMMARY.md
6. Commit

## Acceptance Criteria

- [ ] Python package renamed to `paperforge` (imports work, pip install works)
- [ ] `paperforge sync` runs both selection-sync and index-refresh
- [ ] `paperforge sync --dry-run` previews without changes
- [ ] `paperforge ocr` runs OCR and auto-diagnoses
- [ ] `paperforge ocr --diagnose` diagnoses without running
- [ ] All `/pf-*` command docs exist and are valid
- [ ] No `/LD-*` or `/lp-*` docs remain
- [ ] All tests pass
- [ ] AGENTS.md updated with new naming

## Risk Mitigation

1. **Breaking changes**: Document in AGENTS.md migration section
2. **Import errors**: Systematic rename with verification after each batch
3. **Agent confusion**: Ensure new docs are comprehensive
4. **Test failures**: Update tests in parallel with implementation

## Dependencies

- Phase 8 completed (deep-reading deployment)
- v1.2 milestone initiated
- REQUIREMENTS-v1.2.md defined

## Timeline Estimate

- Task 0 (package rename): 40 min
- Task 1-2 (modules + cli refactor): 60 min
- Task 3-4 (docs): 30 min
- Task 5 (tests + AGENTS.md): 30 min
- Task 6 (verification): 20 min
- **Total: ~3 hours**
