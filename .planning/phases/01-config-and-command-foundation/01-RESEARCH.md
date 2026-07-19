# Phase 1: Config And Command Foundation - Research

**Researched:** 2026-04-23
**Domain:** Python CLI packaging, config/path resolution, Windows-first local workflow
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Claude's Discretion

### the agent's Discretion

- Exact module layout is flexible, but it must be importable both from the repo and from an installed package.
- The launcher may call worker functions directly or dispatch to the worker script as a subprocess, but tests must prove arguments and paths resolve correctly.
- The wording of user-facing output can be concise, but it must avoid `<system_dir>` placeholders.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- `paperforge ocr doctor` belongs to Phase 2.
- PDF path resolver belongs to Phase 2.
- Rich Base template generation belongs to Phase 3.
- Full onboarding guide rewrite belongs to Phase 4.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONF-01 | User can define vault and custom directories through environment variables without editing generated code. | Shared resolver must overlay `PAPERFORGE_*` environment variables above `paperforge.json` and defaults. |
| CONF-02 | User can inspect resolved PaperForge paths with a command. | `paperforge paths` and `paperforge paths --json` should be first-class CLI subcommands backed by the resolver. |
| CONF-03 | Worker, Agent scripts, command docs, and Base generation all use the same config resolver. | Current worker, `/LD-deep`, setup validation, and command docs each resolve paths independently; Phase 1 should centralize this contract. |
| CONF-04 | Existing `paperforge.json` installations remain backward-compatible. | Resolver must support both top-level keys and nested `vault_config`, matching current worker and `ld_deep.py` behavior. |
| CMD-01 | User can run stable commands such as `paperforge status`, `paperforge ocr run`, and `paperforge deep-reading`. | Add minimal packaging and CLI dispatch using Python console scripts plus `python -m paperforge` fallback. |
| CMD-02 | Legacy direct worker invocation remains supported. | Keep `pipeline/worker/scripts/literature_pipeline.py --vault ... <worker>` and copied-vault worker behavior working. |
| CMD-03 | Command output uses actionable statuses and avoids placeholder paths. | Replace command markdown placeholders with stable launcher commands; make `paths` print real resolved paths. |
| DEEP-02 | `/LD-deep` prepare uses the same resolved paths as workers. | Replace or wrap `_load_vault_config()` and `_paperforge_paths()` in `skills/literature-qa/scripts/ld_deep.py`. |
</phase_requirements>

## Summary

Phase 1 should introduce a small, importable `paperforge` package containing the shared config/path resolver and CLI launcher. The resolver is the contract: it must support explicit CLI overrides, `PAPERFORGE_*` process environment variables, existing `paperforge.json` top-level keys, existing nested `vault_config`, and built-in defaults. The CLI should use that resolver to expose `paperforge paths`, `paperforge status`, `paperforge selection-sync`, `paperforge index-refresh`, `paperforge ocr run`, `paperforge ocr`, and `paperforge deep-reading`.

The brownfield risk is not the CLI itself; it is compatibility with copied installation files. `setup_wizard.py` currently copies only `literature_pipeline.py` and `ld_deep.py` into the target vault, while the source repo has no `pyproject.toml`. If the worker starts importing `paperforge.config`, the plan must either install the package into the user's Python environment, copy the package beside the worker/skill scripts, or include a tested compatibility wrapper. Do not assume source-repo imports will exist after setup.

**Primary recommendation:** Add `paperforge/config.py` and `paperforge/cli.py`, expose `paperforge = "paperforge.cli:main"` in `pyproject.toml`, update worker and `/LD-deep` to import the shared resolver with a copied-install fallback, and update command docs to use `paperforge ...` instead of `<system_dir>` placeholders.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `argparse` | Python 3.10+ target; local Python 3.14.0 | CLI parser and subcommand dispatch | Built in, Windows-compatible, no new dependency; official docs recommend `add_subparsers()` with `set_defaults()` for command-specific handlers. |
| Python stdlib `pathlib` | Python 3.10+ target | Cross-platform path construction | Existing code already uses `Path`; required for Windows path safety and path serialization. |
| Python stdlib `json` and `os.environ` | Python 3.10+ target | `paperforge.json` and environment overlay | Existing config files are JSON; environment overrides are locked decisions. |
| PyPA `pyproject.toml` + `[project.scripts]` | setuptools backend, current guide checked 2026-04-23 | Install `paperforge` command | Official packaging guide says `[project.scripts]` creates executable commands after install. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | Latest 9.0.3, published 2026-04-07; installed 9.0.2 | Resolver and CLI tests | Use for Phase 1 tests around precedence, JSON output, command dispatch, and direct-worker compatibility. |
| requests | Latest 2.33.1, published 2026-03-30; installed 2.32.5 | Existing OCR HTTP dependency | Keep existing requirement; no Phase 1 changes needed. |
| PyMuPDF (`pymupdf`) | Latest 1.27.2.2, published 2026-03-19/20; installed 1.27.1 | Existing PDF/OCR processing | Keep existing requirement; PDF path hardening is Phase 2. |
| Pillow | Latest 12.2.0, published 2026-04-01; installed 11.3.0 | Existing OCR image processing | Keep existing requirement. |
| Textual | Latest/installed 8.2.4, published 2026-04-19 | Existing setup wizard UI | Do not add CLI dependency on Textual; setup wizard already depends on it. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `argparse` | Click/Typer | Better ergonomics, but adds dependency and install surface; not needed for this narrow command tree. |
| direct function dispatch | subprocess worker dispatch | Subprocess is safer for preserving current behavior but harder to unit test deeply; function dispatch is faster but may expose import side effects. Use direct import where possible and test subprocess fallback. |
| package-only resolver import | duplicated resolver in worker/skill scripts | Package-only is cleaner but can break copied-vault installs; duplicated logic must be generated or tested against the package contract. |

**Installation:**

```powershell
python -m pip install -e .
paperforge paths
python -m paperforge paths
```

**Version verification:** Current package versions were verified with:

```powershell
python -m pip index versions requests
python -m pip index versions pymupdf
python -m pip index versions pillow
python -m pip index versions textual
python -m pip index versions pytest
```

Publish dates were verified through PyPI JSON on 2026-04-23.

## Architecture Patterns

### Recommended Project Structure

```text
paperforge/
├── __init__.py
├── __main__.py          # calls cli.main()
├── cli.py               # paperforge command tree
├── config.py            # resolver contract shared by worker/agent/setup/validation
└── worker_bridge.py     # optional thin adapter to existing literature_pipeline functions

pipeline/worker/scripts/
└── literature_pipeline.py

skills/literature-qa/scripts/
└── ld_deep.py

tests/
├── test_config.py
├── test_cli_paths.py
├── test_cli_worker_dispatch.py
└── test_legacy_worker_compat.py
```

### Pattern 1: Resolver as the Boundary

**What:** Put all config precedence and path construction in `paperforge.config`. Existing worker and agent scripts should stop owning their own merge rules.

**When to use:** Any code path that needs vault, PaperForge root, exports, OCR root, library records, literature notes, bases, worker script, skill dir, command dir, or `ld_deep.py`.

**Example:**

```python
# Source: local contract derived from Phase 1 CONTEXT.md
DEFAULT_CONFIG = {
    "system_dir": "99_System",
    "resources_dir": "03_Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "05_Bases",
    "skill_dir": ".opencode/skills",
    "command_dir": ".opencode/command",
}

ENV_KEYS = {
    "vault": "PAPERFORGE_VAULT",
    "system_dir": "PAPERFORGE_SYSTEM_DIR",
    "resources_dir": "PAPERFORGE_RESOURCES_DIR",
    "literature_dir": "paperforgeRATURE_DIR",
    "control_dir": "PAPERFORGE_CONTROL_DIR",
    "base_dir": "PAPERFORGE_BASE_DIR",
    "skill_dir": "PAPERFORGE_SKILL_DIR",
    "command_dir": "PAPERFORGE_COMMAND_DIR",
}

def load_vault_config(vault, env=None, overrides=None):
    env = os.environ if env is None else env
    config = dict(DEFAULT_CONFIG)
    config.update(read_paperforge_json(vault))
    config.update(env_config(env))
    config.update({k: v for k, v in (overrides or {}).items() if v})
    return config
```

### Pattern 2: CLI Delegates, It Does Not Reimplement Workers

**What:** `paperforge.cli` parses stable user commands, resolves the vault, then calls existing worker functions or an adapter that preserves current worker behavior.

**When to use:** `status`, `selection-sync`, `index-refresh`, `deep-reading`, and `ocr run`.

**Example:**

```python
# Source: Python argparse docs recommend add_subparsers + set_defaults handlers.
def build_parser():
    parser = argparse.ArgumentParser(prog="paperforge")
    parser.add_argument("--vault", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("paths").set_defaults(func=cmd_paths)
    subparsers.add_parser("status").set_defaults(func=cmd_worker_status)
    subparsers.add_parser("selection-sync").set_defaults(func=cmd_worker_selection_sync)
    subparsers.add_parser("index-refresh").set_defaults(func=cmd_worker_index_refresh)
    subparsers.add_parser("deep-reading").set_defaults(func=cmd_worker_deep_reading)

    ocr = subparsers.add_parser("ocr")
    ocr_sub = ocr.add_subparsers(dest="ocr_command")
    ocr_sub.add_parser("run").set_defaults(func=cmd_worker_ocr)
    ocr.set_defaults(func=cmd_worker_ocr)
    return parser
```

### Pattern 3: JSON Output Is Pure Data

**What:** `paperforge paths --json` should write only JSON to stdout. Human explanatory text belongs in normal `paths` output.

**When to use:** Any command consumed by tests, scripts, or agents.

**Example:**

```python
def cmd_paths(args):
    vault = resolve_vault(args.vault)
    cfg = load_vault_config(vault, overrides=vars(args))
    paths = paperforge_paths(vault, cfg)
    data = {name: str(path) for name, path in paths.items()}
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for name, value in data.items():
            print(f"{name}: {value}")
```

### Pattern 4: Copied Install Compatibility

**What:** If `literature_pipeline.py` and `ld_deep.py` are copied into a vault, they still need access to the resolver.

**When to use:** Setup wizard deployment and direct legacy invocation.

**Recommended plan:** Copy `paperforge/` into `<system_dir>/PaperForge/worker/` and into `<skill_dir>/literature-qa/` or install the package through `pip install -e .` during setup. Add tests that execute the script from a temporary copied-vault layout.

### Anti-Patterns to Avoid

- **Ad hoc placeholder substitution as runtime config:** `setup_wizard.py` currently replaces `<system_dir>` in copied docs. Keep that for docs if needed, but runtime commands should resolve paths dynamically.
- **Multiple untested config loaders:** Current worker, `/LD-deep`, and validation script each merge `paperforge.json` separately. Any future config key can drift.
- **Changing direct worker syntax:** `python .../literature_pipeline.py --vault <vault> status` is explicitly required to remain valid.
- **Letting `.env` overwrite process env:** Process environment variables are locked above `paperforge.json`; if `.env` is loaded, actual `os.environ` must remain highest precedence.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI parsing | manual `sys.argv` parsing | stdlib `argparse` | Handles help, errors, subcommands, Windows quoting. |
| Console command installation | batch files or PowerShell-only shims as primary path | `pyproject.toml` `[project.scripts]` | Cross-platform packaging standard; official tooling creates wrappers. |
| Config precedence | inline merges in each script | one resolver function + tests | Prevents worker/agent/setup drift. |
| Path serialization | string concatenation | `pathlib.Path`, then string at output boundary | Avoids Windows separator and drive-letter edge cases. |
| JSON command output | table text parsed by agents | `--json` option | Stable for tests and automation. |

**Key insight:** The hard part is not discovering paths; it is ensuring every entry point uses the same path contract after the setup wizard copies files into a user vault.

## Common Pitfalls

### Pitfall 1: Breaking Copied Worker Imports

**What goes wrong:** Worker imports `paperforge.config` successfully in the source repo but fails after setup because only `literature_pipeline.py` was copied into the vault.
**Why it happens:** The setup wizard copies individual files, not a package.
**How to avoid:** Plan either package installation during setup or copy the package/module beside deployed worker and skill scripts. Test both source-repo and copied-vault invocation.
**Warning signs:** Tests only call `paperforge ...` and never call `python <tmp-vault>/99_System/PaperForge/worker/scripts/literature_pipeline.py --vault <tmp-vault> status`.

### Pitfall 2: Environment Precedence Inversion

**What goes wrong:** Values in `paperforge.json` or `.env` override a user's process environment.
**Why it happens:** Existing `load_simple_env()` mutates `os.environ` and preserves the first-loaded value.
**How to avoid:** For path config, compute a layered dictionary: defaults, JSON, `.env`-derived values if supported, then real process env, then CLI overrides. Preserve the locked order.
**Warning signs:** A test setting `PAPERFORGE_SYSTEM_DIR=CustomSystem` still prints `99_System`.

### Pitfall 3: Incomplete Path Inventory

**What goes wrong:** `paperforge paths` prints a few directory names but omits `worker_script`, `ld_deep_script`, `library_records`, or `exports`.
**Why it happens:** Existing `pipeline_paths()` was built for worker internals, not user diagnostics.
**How to avoid:** Treat the path list in CONTEXT.md as the acceptance list. Test exact key presence for text and JSON modes.
**Warning signs:** Docs still need `<system_dir>` to explain how to run worker commands.

### Pitfall 4: `ocr run` and `ocr` Diverge

**What goes wrong:** `paperforge ocr` and `paperforge ocr run` call different code or one returns help only.
**Why it happens:** Nested subparsers are wired without a default handler for the parent command.
**How to avoid:** Set the parent `ocr` command default to the same function as `ocr run`; keep `ocr doctor` out of scope for Phase 1.
**Warning signs:** `paperforge ocr` passes tests but `paperforge ocr run` is untested, or vice versa.

### Pitfall 5: Updating Source Docs But Not Installed Command Docs

**What goes wrong:** Repo command files are fixed, but installed OpenCode commands still contain placeholders because setup copied stale content.
**Why it happens:** `setup_wizard.py` copies `command/*.md` during deployment and applies string replacement.
**How to avoid:** Update source command docs and setup deployment expectations together. Prefer command docs that say `paperforge status` and no longer require path substitution.
**Warning signs:** `rg "<system_dir>" command README.md AGENTS.md` still finds user-run command examples after Phase 1.

## Code Examples

Verified patterns from official and local sources:

### Minimal `pyproject.toml` for the Launcher

```toml
# Source: Python Packaging User Guide, "Creating executable scripts"
[build-system]
requires = ["setuptools >= 77.0.3"]
build-backend = "setuptools.build_meta"

[project]
name = "paperforge-lite"
version = "1.2.0"
requires-python = ">=3.10"
dependencies = [
  "requests>=2.31.0",
  "pymupdf>=1.23.0",
  "pillow>=10.0.0",
  "textual>=0.47.0",
]

[project.optional-dependencies]
test = ["pytest>=7.4.0"]

[project.scripts]
paperforge = "paperforge.cli:main"
```

### Backward-Compatible `paperforge.json` Merge

```python
# Source: current worker and ld_deep.py behavior.
def read_paperforge_json(vault: Path) -> dict[str, str]:
    path = vault / "paperforge.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    nested = data.get("vault_config", {})
    merged = {}
    if isinstance(nested, dict):
        merged.update({k: v for k, v in nested.items() if v})
    merged.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG and v})
    return merged
```

### Worker Compatibility Wrapper

```python
# Source: local compatibility need from setup_wizard.py copying individual scripts.
try:
    from paperforge.config import load_vault_config, paperforge_paths
except ImportError:
    # Fallback only if copied installs cannot import the package.
    from _paperforge_config import load_vault_config, paperforge_paths
```

### CLI Dispatch to Existing Worker

```python
# Source: current literature_pipeline.py exposes run_status/run_ocr/etc.
WORKER_COMMANDS = {
    "status": "run_status",
    "selection-sync": "run_selection_sync",
    "index-refresh": "run_index_refresh",
    "deep-reading": "run_deep_reading",
    "ocr": "run_ocr",
}

def run_worker(command: str, vault: Path) -> int:
    from pipeline.worker.scripts import literature_pipeline
    return getattr(literature_pipeline, WORKER_COMMANDS[command])(vault)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setup.py`/ad hoc scripts for command exposure | `pyproject.toml` with `[project.scripts]` | PyPA current guidance as of 2026-04-21 docs | Use modern metadata and console script wrapper. |
| Placeholder path examples in docs | Stable launcher resolving config at runtime | Phase 1 target | New users can copy commands without agent/manual substitution. |
| Separate config loaders in worker and agent | Shared resolver contract | Phase 1 target | Environment overrides and custom directories behave consistently. |
| Text-only status as path debugging | `paths` plus `paths --json` | Phase 1 target | Humans and agents can inspect exact resolved locations. |

**Deprecated/outdated:**

- Source-only command examples such as `python <system_dir>/PaperForge/worker/scripts/literature_pipeline.py ...` should remain as legacy fallback, not the primary documentation path.
- Direct string concatenation for paths should not be added; existing `Path` usage should be preserved.
- `VAULT_PATH` as the only validation script input is insufficient for the Phase 1 config contract; use `PAPERFORGE_VAULT` or shared `resolve_vault()`.

## Existing Implementation Findings

| Area | Evidence | Phase 1 Implication | Confidence |
|------|----------|---------------------|------------|
| Worker config loader | `pipeline/worker/scripts/literature_pipeline.py:126` supports defaults, nested `vault_config`, and top-level keys. | Move this behavior into shared resolver without changing output. | HIGH |
| Worker paths | `pipeline_paths()` currently returns many worker internals but not the full required `paths` output set. | Add user-facing path inventory with required keys. | HIGH |
| Worker CLI | `--vault` is required and worker choices are fixed at `selection-sync`, `index-refresh`, `ocr`, `deep-reading`, `status`, `update`, `wizard`, `all`. | New CLI should make vault optional through resolver while preserving direct required `--vault` worker path. | HIGH |
| `/LD-deep` config | `ld_deep.py:14` duplicates config merge and `ld_deep.py:34` builds only `ocr`, `records`, `literature`. | Replace with shared resolver or tested wrapper. | HIGH |
| Validation config | `scripts/validate_setup.py:24` duplicates config logic and uses `VAULT_PATH`. | If touched, use shared resolver and `PAPERFORGE_VAULT`. | MEDIUM |
| Setup deployment | `setup_wizard.py:887` does placeholder replacement; `setup_wizard.py:1042` writes top-level and nested config keys. | Preserve both JSON shapes and update copied command docs. | HIGH |
| Packaging | No `pyproject.toml`; only `scripts/setup.py` wrapper for setup wizard. | Add minimal package metadata and entry point. | HIGH |
| Tests | No `tests/` directory detected; `pytest` exists in requirements and installed locally. | Planner should include Wave 0 test scaffolding despite Nyquist validation being disabled. | HIGH |

## Open Questions

1. **How will installed-vault worker scripts find `paperforge`?**
   - What we know: setup currently copies individual worker and skill files.
   - What's unclear: whether setup should run `pip install -e .`, copy the package, or keep a fallback resolver file.
   - Recommendation: plan tests for both source CLI and copied-vault direct worker invocation; choose package install plus copied fallback if setup cannot guarantee package availability.

2. **Should `paperforge` infer vault from current directory parents?**
   - What we know: setup wizard has `_find_vault()` logic but does not use it in `main()`.
   - What's unclear: whether users will run commands inside the vault root or outside it.
   - Recommendation: support `--vault`, `PAPERFORGE_VAULT`, current directory, and parent search for `paperforge.json`, in that order.

3. **Should `.env` path variables be supported or only process env?**
   - What we know: locked decisions name process environment variables; existing `.env` is mainly OCR credentials.
   - What's unclear: whether users expect `PAPERFORGE_*` in `.env`.
   - Recommendation: support process environment for Phase 1; if `.env` is loaded for credentials, document that process env remains highest precedence.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | CLI, worker, tests | Yes | 3.14.0 local; project docs target 3.10+ | Require Python >=3.10 in `pyproject.toml`; setup wizard currently checks >=3.8 and should be aligned later. |
| pip | Editable install and dependency checks | Yes | 25.2 | Direct `python -m paperforge ...` after source checkout if editable install is unavailable. |
| pytest | Phase 1 tests | Yes | 9.0.2 installed; latest 9.0.3 | Use `python -m pytest`; no existing tests detected. |
| pyproject.toml | `paperforge` command installation | No | Not present | Add in Phase 1; fallback `python -m paperforge ...` must work. |

**Missing dependencies with no fallback:**

- None for research. Implementation needs a new `pyproject.toml` file before `paperforge` can be installed as a console script.

**Missing dependencies with fallback:**

- `paperforge` executable is not currently installed; fallback after implementation should be `python -m paperforge ...`.

## Sources

### Primary (HIGH confidence)

- Local `.planning/phases/01-config-and-command-foundation/01-CONTEXT.md` - locked command surface, config hierarchy, path output, compatibility, packaging, deferred scope.
- Local `.planning/REQUIREMENTS.md` - requirement IDs CONF-01 through DEEP-02.
- Local `.planning/PROJECT.md` - project constraints: local-first, Windows compatibility, plain Python, credential safety, agent independence.
- Local `pipeline/worker/scripts/literature_pipeline.py` - current worker config, path, and command dispatcher behavior.
- Local `skills/literature-qa/scripts/ld_deep.py` - current agent-side duplicated resolver and prepare/queue behavior.
- Local `setup_wizard.py` - deployment copying, placeholder substitution, and `paperforge.json` write shape.
- Local `scripts/validate_setup.py` - current validation config duplication and `VAULT_PATH` behavior.
- Python Packaging User Guide - `pyproject.toml` and `[project.scripts]`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- PyPA Entry Points specification - console scripts and Windows console behavior: https://packaging.python.org/en/latest/specifications/entry-points/
- Python 3.14 argparse docs - subparsers and `set_defaults()` dispatch: https://docs.python.org/3/library/argparse.html

### Secondary (MEDIUM confidence)

- PyPI JSON and `pip index versions` checks on 2026-04-23 for `requests`, `pymupdf`, `pillow`, `textual`, and `pytest`.
- pytest fixture docs for test infrastructure reference: https://docs.pytest.org/en/stable/reference/fixtures.html

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - based on official Python/PyPA docs and existing dependency constraints.
- Architecture: HIGH - based on current source code, locked phase context, and direct file inspection.
- Pitfalls: HIGH - derived from concrete duplicated resolver code and setup copying behavior.
- Environment: HIGH - probed local tools and package versions on 2026-04-23.

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 for architecture; re-check PyPI/package versions within 30 days if planning dependency upgrades.
