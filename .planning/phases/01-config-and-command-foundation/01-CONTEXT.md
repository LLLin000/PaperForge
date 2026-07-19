# Phase 1: Config And Command Foundation - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Source:** Derived from `$gsd-new-project` research and Phase 1 roadmap.

<domain>
## Phase Boundary

Phase 1 delivers a shared configuration/path resolution foundation and stable user command surface. It does not implement PaddleOCR doctor, PDF path hardening, Base template redesign, or full onboarding docs beyond updating command references affected by this phase.

The implementation should make the following user workflow possible:

```powershell
paperforge paths
paperforge status
paperforge selection-sync
paperforge index-refresh
paperforge ocr run
paperforge deep-reading
```

Legacy usage remains valid:

```powershell
python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py --vault <vault> status
```
</domain>

<decisions>
## Implementation Decisions

### Command Surface

- The canonical launcher command is `paperforge`.
- A short alias `pf` is optional and not required in Phase 1.
- The launcher must support at least these subcommands: `paths`, `status`, `selection-sync`, `index-refresh`, `ocr run`, `ocr`, and `deep-reading`.
- `paperforge ocr` may behave as an alias for `paperforge ocr run` for backward-friendly ergonomics.
- The launcher should call or reuse the existing worker implementation instead of duplicating worker behavior.

### Configuration Hierarchy

- Configuration precedence is:
  1. Explicit CLI flags.
  2. Process environment variables.
  3. Vault `paperforge.json`.
  4. Built-in defaults.
- Environment variable names for paths are:
  - `PAPERFORGE_VAULT`
  - `PAPERFORGE_SYSTEM_DIR`
  - `PAPERFORGE_RESOURCES_DIR`
  - `paperforgeRATURE_DIR`
  - `PAPERFORGE_CONTROL_DIR`
  - `PAPERFORGE_BASE_DIR`
  - `PAPERFORGE_SKILL_DIR`
  - `PAPERFORGE_COMMAND_DIR`
- Existing `paperforge.json` top-level keys and nested `vault_config` remain supported.
- Defaults remain:
  - `system_dir`: `99_System`
  - `resources_dir`: `03_Resources`
  - `literature_dir`: `Literature`
  - `control_dir`: `LiteratureControl`
  - `base_dir`: `05_Bases`
  - `skill_dir`: `.opencode/skills`

### Path Output

- `paperforge paths` must print resolved absolute paths for:
  - `vault`
  - `system`
  - `paperforge`
  - `exports`
  - `ocr`
  - `resources`
  - `literature`
  - `control`
  - `library_records`
  - `bases`
  - `worker_script`
  - `skill_dir`
  - `ld_deep_script`
- `paperforge paths --json` should print a JSON object with the same keys.

### Worker And Agent Compatibility

- Existing direct calls to `pipeline/worker/scripts/literature_pipeline.py --vault ... <worker>` must continue to work.
- The worker should use the shared resolver for `load_vault_config()` and `pipeline_paths()`.
- `skills/literature-qa/scripts/ld_deep.py` should use the same resolver or a small compatibility wrapper with identical behavior.
- Setup wizard and validation scripts should be planned for integration with the resolver if touched in this phase.

### Packaging

- Because this repo currently has no `pyproject.toml`, Phase 1 should add the minimal packaging/entrypoint files needed to expose `paperforge` after editable install.
- If packaging is deferred inside a plan, the fallback command `python -m paperforge ...` must still work.

### the agent's Discretion

- Exact module layout is flexible, but it must be importable both from the repo and from an installed package.
- The launcher may call worker functions directly or dispatch to the worker script as a subprocess, but tests must prove arguments and paths resolve correctly.
- The wording of user-facing output can be concise, but it must avoid `<system_dir>` placeholders.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Planning

- `.planning/PROJECT.md` — project purpose, constraints, and known issues.
- `.planning/REQUIREMENTS.md` — Phase 1 requirement IDs and traceability.
- `.planning/ROADMAP.md` — Phase 1 goal and success criteria.
- `.planning/research/DEFECTS.md` — path/config defects motivating this phase.
- `.planning/research/SUMMARY.md` — release-hardening strategy.

### Existing Implementation

- `pipeline/worker/scripts/literature_pipeline.py` — current worker implementation, config loader, path builder, and command dispatcher.
- `skills/literature-qa/scripts/ld_deep.py` — current agent-side path resolution for `/LD-deep`.
- `setup_wizard.py` — writes `paperforge.json`, `.env`, docs, and command files during setup.
- `scripts/validate_setup.py` — current validation config loading.
- `command/lp-status.md` — command docs currently using placeholders.
- `command/lp-selection-sync.md` — command docs currently using placeholders.
- `command/lp-index-refresh.md` — command docs currently using placeholders.
- `command/lp-ocr.md` — command docs currently using placeholders.
- `command/ld-deep.md` — agent command docs for deep reading path variables.
- `README.md` and `AGENTS.md` — user-facing command examples.

### Test Surface

- `requirements.txt` — dependencies available in release repo.
- Existing tests if present under `tests/` or copied from the fuller local pipeline should inform style, but Phase 1 can add a local `tests/` directory if missing.
</canonical_refs>

<specifics>
## Specific Ideas

- Add a module such as `paperforge/config.py` with:
  - `DEFAULT_CONFIG`
  - `load_simple_env(env_path)`
  - `load_vault_config(vault, env=os.environ, overrides=None)`
  - `resolve_vault(cli_vault=None, env=os.environ)`
  - `paperforge_paths(vault, cfg)`
- Add a launcher module such as `paperforge/cli.py` with:
  - `main(argv=None)`
  - `paths` command
  - worker command dispatch for `status`, `selection-sync`, `index-refresh`, `deep-reading`, and `ocr run`
- Add `paperforge.py` at repo root only if needed as a Windows-friendly script shim.
- Add tests for nested `vault_config`, top-level legacy keys, environment overrides, CLI overrides, path output keys, and worker compatibility.
</specifics>

<deferred>
## Deferred Ideas

- `paperforge ocr doctor` belongs to Phase 2.
- PDF path resolver belongs to Phase 2.
- Rich Base template generation belongs to Phase 3.
- Full onboarding guide rewrite belongs to Phase 4.
</deferred>

---

*Phase: 01-config-and-command-foundation*
*Context gathered: 2026-04-23 via derived planning context*
