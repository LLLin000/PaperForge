# Phase 48: Textual TUI Removal - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

The broken Textual TUI setup wizard is removed entirely. `paperforge setup` (bare, no `--headless`) prints a help message redirecting users to `--headless` or the plugin settings tab. All TUI classes, import paths, and the `textual` optional dependency are purged. Documentation updated to reflect headless-only setup. `headless_setup()` and all shared utilities preserved intact.

Requirements: DEPR-01 through DEPR-03.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — infrastructure/removal phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Known code context:
- `paperforge/worker/setup_wizard.py` — contains both TUI classes (~1200 lines) and headless code
- TUI classes to remove: `WelcomeStep`, `DirOverviewStep`, `VaultStep`, `PlatformStep`, `DeployStep`, `DoneStep`, `SetupWizardApp`, `ContentSwitcher`, `StepScreen`
- All `from textual` import paths to remove
- `headless_setup()`, `EnvChecker`, `AGENT_CONFIGS`, `_copy_file_incremental`, `_merge_env_incremental` — preserve
- CLI entry: `paperforge setup` (bare) → redirect help message
- `--non-interactive` CLI option → remove
- `textual` → remove from project optional dependencies
- Docs: `docs/setup-guide.md`, `docs/INSTALLATION.md`, `README.md`

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `paperforge/worker/setup_wizard.py` — main target
- `docs/setup-guide.md` — documentation to update
- `docs/INSTALLATION.md` — documentation to update
- `README.md` — documentation to update
- `pyproject.toml` or `setup.py` or `setup.cfg` — optional dependency list

### Preserved Assets
- `headless_setup()` function
- `EnvChecker` class  
- `AGENT_CONFIGS` dict
- `_copy_file_incremental` utility
- `_merge_env_incremental` utility

</code_context>

<specifics>
No specific requirements — infrastructure phase.

</specifics>

<deferred>
None

</deferred>
