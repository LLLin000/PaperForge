# Phase 09 Discussion Log: Command Unification & CLI Simplification

## Date
2026-04-24

## Participants
- Overseer (user)
- VT-OS/OPENCODE

## Gray Areas Discussed

### 1. Backward Compatibility Strategy

**Options presented:**
- A: Aggressive migration (remove old commands entirely)
- B: Aliases + deprecation warnings (get-shit-done-main style)
- C: Permanent aliases

**Decision:** Option A — Aggressive migration

**Rationale:**
- v1.1→v1.2 is a major version jump
- Project still early stage (small user base)
- Clean break reduces technical debt
- No confusion from multiple command variants

**Impact:**
- `/LD-deep`, `/LD-paper`, `/lp-*` will no longer work
- Users must learn `/pf-deep`, `/pf-paper`, `/pf-*`
- All documentation must be updated

### 2. CLI Sync Command Behavior

**Options presented:**
- A: Default full sync (selection + index)
- B: Default dry-run (preview mode)
- C: Interactive confirmation

**Decision:** Option A — Default full sync

**Command design:**
```bash
paperforge sync              # selection-sync + index-refresh
paperforge sync --dry-run    # preview only
paperforge sync --domain 骨科 # filter by domain
paperforge sync --selection  # selection-sync only
paperforge sync --index      # index-refresh only
```

**Rationale:**
- `sync` intuition = synchronize everything
- `--dry-run` is standard CLI pattern
- Granular flags for power users

**Domain filter:** Supported but optional. When omitted, syncs all domains.

### 3. OCR Command Simplification

**Options presented:**
- A: Merge into `paperforge ocr`
- B: Keep separate but simplify names
- C: Reorganize subcommands

**Decision:** Option A — Merge into `paperforge ocr`

**Command design:**
```bash
paperforge ocr               # run OCR + auto-diagnose
paperforge ocr --diagnose    # diagnose only (no upload)
paperforge ocr --key XXX     # process specific item
```

**Rationale:**
- Users typically want "run and confirm"
- Diagnose on startup catches API key issues early
- `--diagnose` flag for standalone diagnostics

### 4. Command Dispatch Layer Architecture

**Options presented:**
- A: Unified command modules (`paperforge/commands/`)
- B: Agent calls CLI via subprocess
- C: Light shared layer (Agent imports cli.py)

**Decision:** Option A — Unified command modules

**Architecture:**
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

**Integration:**
- CLI: `cli.py` → `commands/*.py` (direct function calls)
- Agent: `command/pf-*.md` docs reference `python -m paperforge <cmd>` or direct module imports

**Rationale:**
- Maximum code reuse
- Single source of truth for command logic
- Follows get-shit-done-main pattern
- Paves way for future Python SDK

## Dependencies

### Prior Phase Decisions
- Phase 1: `paperforge` as canonical launcher
- Phase 1: `paperforge ocr` as alias for `ocr run`
- Phase 6: `paperforge paths --json` output fields
- Phase 6: `python -m paperforge` as fallback

### Cross-references
- SYS-01: Unify agent command namespace (`/pf-*`)
- SYS-02: Simplify CLI commands
- SYS-03: Make command interface cohesive

## Risks

1. **User disruption**: Aggressive migration breaks existing muscle memory
2. **Documentation lag**: All docs must be updated simultaneously
3. **Test coverage**: All tests must be updated for new command names
4. **Agent confusion**: Agent must be retrained on new command docs

## Notes

- Overseer confirmed all 4 gray areas for discussion
- All decisions aligned with v1.2 "systematization" theme
- Architecture choice (Option A) requires refactoring cli.py but provides cleanest long-term solution
- Consider adding migration guide in AGENTS.md for users upgrading from v1.1
