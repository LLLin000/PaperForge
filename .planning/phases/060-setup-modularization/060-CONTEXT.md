# Phase 60: Setup Modularization - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — refactoring)

<domain>
## Phase Boundary

Monolithic setup_wizard.py (979 lines, 2 classes + 1 main function + helpers) decomposed into six focused classes with explicit dependencies:

1. `SetupPlan` — defines setup phases and their dependencies
2. `SetupChecker` — validates preconditions (Python, pip, dependency health)
3. `RuntimeInstaller` — pip install with version pinning, progress callback, ErrorCode classification
4. `VaultInitializer` — creates directory structure, Zotero junction, .env merge
5. `AgentInstaller` — deploys skill files and agent configs for supported platforms
6. `ConfigWriter` — writes paperforge.json atomically (tempfile + os.replace)

Output: `paperforge setup --headless --json` returns per-step status with `{ok, error, message}` fields per step.

No user-facing design decisions — the contract was already defined in Phase 57 (dashboard/result types) and the UI behavior is already stable.
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure decomposition/refactoring phase. Follow ROADMAP success criteria and existing codebase conventions.

### Prior Decisions
- PFResult/PFError from Phase 57 for --json output
- ErrorCode enum from Phase 57 for error classification
- Version pinning: pip install paperforge pins to plugin manifest version (Phase 56, BLEED-04)
- Config writing: tempfile + os.replace for atomicity
</decisions>

<code_context>
## Existing Code Assets

### setup_wizard.py Structure (979 lines)
- `CheckResult` (line 110) — result dataclass → repurpose for SetupChecker
- `EnvChecker` (line 118) — preflight env checks → becomes SetupChecker
- `_find_vault()` (line 408) — vault path detection
- `_substitute_vars()` (line 417) — template variable substitution
- `_copy_file_incremental()` (line 441) — file copy
- `_write_text_incremental()` (line 450) — text file writing
- `_copy_tree_incremental()` (line 459) — directory copy
- `_merge_env_incremental()` (line 476) — .env file merge
- `_deploy_skill_directory()` (line 515) — skill deployment → becomes AgentInstaller
- `_deploy_flat_command()` (line 567) — command deployment → becomes AgentInstaller
- `_deploy_rules_file()` (line 597) — rules deployment → becomes AgentInstaller
- `headless_setup()` (line 631) — main orchestration → becomes SetupPlan
- `main()` (line 1066) — CLI entry point → thin dispatch

### Available Imports
- `paperforge/core/result.py` — PFResult, PFError (Phase 57)
- `paperforge/core/errors.py` — ErrorCode (Phase 57)
- `paperforge/core/state.py` — state enums (Phase 59)
- `paperforge.schema` — load_field_registry (Phase 59)

### Integration Points
- `paperforge/cli.py` — setup command dispatch
- `paperforge/plugin/main.js` — setup installer subprocess call (Phase 21)
- `paperforge/commands/` — existing command module pattern

</code_context>

<specifics>
## Specific Ideas

### Decomposition Map
| New Class | Source Functions | Purpose |
|-----------|-----------------|---------|
| SetupPlan | headless_setup() orchestration logic | Define steps, dependencies, execute sequence |
| SetupChecker | EnvChecker, CheckResult | Validate preconditions before install |
| RuntimeInstaller | pip install logic (currently inline) | Install Python package with version pin |
| VaultInitializer | _find_vault, _copy_tree_incremental, _merge_env_incremental | Create vault structure |
| AgentInstaller | _deploy_skill_directory, _deploy_flat_command, _deploy_rules_file | Deploy agent configs |
| ConfigWriter | paperforge.json writing (currently inline) | Atomic config file writes |

### Step Contract (for --headless --json)
```python
{
    "step": "checker",
    "ok": true,
    "message": "Python 3.10+ found",
    "error": None
}
```

Steps in order: checker → writer → vault → runtime → agent → plan

</specifics>

<deferred>
## Deferred Ideas

- None — infrastructure phase.
</deferred>
