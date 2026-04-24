# Phase 09 Context: Command Unification & CLI Simplification

## Overview

Systematize the command interface by unifying agent commands under `/pf-*` namespace and simplifying CLI commands. Create shared command modules for CLI and Agent consumption.

## Current State

### Agent Commands (to be unified)
- `/LD-deep` — deep reading
- `/LD-paper` — quick summary
- `/lp-ocr` — OCR helper
- `/lp-index-refresh` — index refresh helper
- `/lp-selection-sync` — selection sync helper
- `/lp-status` — status helper

### CLI Commands (to be simplified)
- `paperforge selection-sync` → `paperforge sync`
- `paperforge index-refresh` → `paperforge sync`
- `paperforge ocr run` + `paperforge ocr doctor` → `paperforge ocr`
- `paperforge deep-reading` → keep as-is (but agent becomes `/pf-deep`)
- `paperforge repair` → keep as-is
- `paperforge status` → keep as-is

### Architecture

```
paperforge/
  ├── cli.py              # CLI entry point (argparse)
  └── commands/           # Shared command implementations
        ├── __init__.py
        ├── sync.py       # selection-sync + index-refresh
        ├── ocr.py        # OCR run + diagnose
        ├── deep.py       # deep-reading queue
        ├── repair.py     # state repair
        └── status.py     # system status
```

- **CLI**: `cli.py` → `commands/*.py` (function calls)
- **Agent**: `command/pf-*.md` docs reference `python -m paperforge <cmd>` or direct `commands/*.py` imports

## Key Decisions

### 1. Backward Compatibility: Aggressive Migration
- Old commands (`/LD-*`, `/lp-*`) completely removed
- No aliases, no deprecation warnings
- Documentation updated to only reference new commands
- Rationale: v1.1→v1.2 is a major version jump, clean break reduces tech debt

### 2. CLI Sync: Default Full Sync
```bash
paperforge sync              # selection-sync + index-refresh
paperforge sync --dry-run    # preview only
paperforge sync --domain 骨科 # filter by domain
paperforge sync --selection  # selection-sync only
paperforge sync --index      # index-refresh only
```
- Rationale: `sync` intuition = synchronize everything

### 3. OCR: Merged Command
```bash
paperforge ocr               # run OCR + auto-diagnose
paperforge ocr --diagnose    # diagnose only (no upload)
paperforge ocr --key XXX     # process specific item
```
- Rationale: users typically want "run and confirm"

### 4. Command Dispatch: Unified Modules
- Create `paperforge/commands/` package
- Each module exposes `run(args)` or `run(**kwargs)` interface
- CLI imports and calls these functions
- Agent command docs reference the same modules
- Rationale: code reuse, single source of truth, paves way for Python SDK

## Reference Research

From get-shit-done-main analysis:
- Unified namespace (`/gsd-*`) for all commands
- User-centric command names (not implementation names)
- Thin orchestrators that delegate to shared modules
- File-based state tracked in `.planning/`

## Files to Modify

### New Files
- `paperforge/commands/__init__.py`
- `paperforge/commands/sync.py`
- `paperforge/commands/ocr.py`
- `paperforge/commands/deep.py`
- `paperforge/commands/repair.py`
- `paperforge/commands/status.py`
- `command/pf-deep.md`
- `command/pf-paper.md`
- `command/pf-ocr.md`
- `command/pf-sync.md`
- `command/pf-status.md`

### Modified Files
- `paperforge/cli.py` — refactor to use commands/
- `command/ld-deep.md` — delete
- `command/ld-paper.md` — delete
- `command/lp-*.md` — delete
- `AGENTS.md` — update command references
- `tests/test_smoke.py` — update command names
- `.planning/phases/09-command-unification/` — phase artifacts

## Acceptance Criteria

- [ ] All old commands removed (no `/LD-*`, `/lp-*`)
- [ ] New `/pf-*` command docs created
- [ ] `paperforge sync` works (selection + index)
- [ ] `paperforge ocr` works (run + diagnose)
- [ ] All tests pass with new command names
- [ ] AGENTS.md updated with new command reference
