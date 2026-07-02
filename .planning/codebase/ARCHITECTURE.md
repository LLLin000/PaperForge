<!-- refreshed: 2026-07-02 -->
# Architecture

**Analysis Date:** 2026-07-02

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    CLI + Obsidian Plugin                     │
├──────────────────┬──────────────────┬───────────────────────┤
│ argparse CLI     │ command modules  │ plugin subprocess UI  │
│ `paperforge/cli.py` │ `paperforge/commands/` │ `paperforge/plugin/` │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Service / Worker / Domain Layer              │
│ `paperforge/services/`, `paperforge/worker/`, `paperforge/annotation/` │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│           Vault filesystem, SQLite DBs, Zotero exports        │
│ `paperforge/config.py`, `paperforge/memory/`, `paperforge/adapters/` │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI parser and dispatcher | Defines `paperforge` commands, resolves vault/config/env, dispatches to command modules | `paperforge/cli.py` |
| Command modules | Thin user-facing command adapters that return exit codes and print text or `PFResult` JSON | `paperforge/commands/` |
| Command registry | Dynamic lookup for command modules used by agents and internal callers | `paperforge/commands/__init__.py` |
| Configuration resolver | Single source of truth for vault config, environment precedence, and generated path inventory | `paperforge/config.py` |
| Result contract | Standard JSON envelope for CLI/plugin/agent command responses | `paperforge/core/result.py` |
| Core errors | Shared stable error codes for PFResult failures | `paperforge/core/errors.py` |
| Sync service | Transitional service facade around sync lifecycle and legacy worker migration | `paperforge/services/sync_service.py` |
| Worker layer | Filesystem-oriented pipeline logic: sync, OCR, repair, status, asset index, base views | `paperforge/worker/` |
| Adapters | External format normalization for Better BibTeX, Zotero paths, collections, Obsidian frontmatter | `paperforge/adapters/` |
| Memory layer | SQLite-backed paper index, reading log, project log, FTS, retrieval, vector runtime state | `paperforge/memory/` |
| Annotation layer | Zotero annotation import, normalization, storage, and read-only export/list/status commands | `paperforge/annotation/` |
| Setup layer | Environment checks, vault initialization, config writing, runtime/agent installation | `paperforge/setup/`, `paperforge/setup_wizard.py` |
| Obsidian plugin | JavaScript UI shell that runs Python `paperforge` subprocesses and renders dashboard/annotation state | `paperforge/plugin/main.js`, `paperforge/plugin/src/testable.js` |
| Agent skill payload | Packaged PaperForge skill docs, workflows, and `/pf-deep` scripts deployed into vault agent directories | `paperforge/skills/paperforge/` |

## Pattern Overview

**Overall:** Layered local-first CLI with command adapters, worker/service modules, filesystem and SQLite persistence, and an Obsidian plugin bridge.

**Key Characteristics:**
- Keep CLI parsing in `paperforge/cli.py`; put command behavior behind `run(args)` functions in `paperforge/commands/*.py`.
- Use `paperforge/config.py` for every vault-relative path. Do not reconstruct PaperForge paths by string concatenation in new code.
- Use `PFResult` from `paperforge/core/result.py` for machine-readable command output consumed by the plugin and tests.
- Keep external format parsing in `paperforge/adapters/` or a domain package such as `paperforge/annotation/`; worker modules should orchestrate, not parse every external shape inline.
- Treat `paperforge/worker/sync.py` as legacy-constrained. Its header states no new business logic; place new sync behavior in `paperforge/services/`, `paperforge/adapters/`, or `paperforge/core/`.

## Layers

**Entry Layer:**
- Purpose: Convert command line or plugin action into a normalized command invocation.
- Location: `paperforge/cli.py`, `paperforge/__main__.py`, `paperforge/plugin/main.js`
- Contains: `argparse` parser construction, vault resolution, `.env` loading, logging setup, command dispatch, plugin subprocess calls.
- Depends on: `paperforge.config`, `paperforge.logging_config`, `paperforge.commands`, selected worker modules for compatibility aliases.
- Used by: Installed console script from `pyproject.toml`, `python -m paperforge`, Obsidian plugin runtime.

**Command Adapter Layer:**
- Purpose: Keep command-specific I/O contracts close to the command name.
- Location: `paperforge/commands/`
- Contains: `run(args) -> int` command functions, PFResult printing, user-facing validation, subcommand dispatch.
- Depends on: `paperforge.core.result`, `paperforge.core.errors`, `paperforge.worker`, `paperforge.memory`, `paperforge.annotation`, `paperforge.services`.
- Used by: `paperforge/cli.py`, agent workflows, tests under `tests/cli/` and `tests/unit/commands/`.

**Service / Worker Layer:**
- Purpose: Execute application workflows against vault files, exports, and indexes.
- Location: `paperforge/services/`, `paperforge/worker/`
- Contains: Sync orchestration, OCR state updates, repair, status/doctor checks, base view generation, canonical asset index creation.
- Depends on: `paperforge.config`, `paperforge.adapters`, `paperforge.core`, third-party libs such as `requests`, `filelock`, `pymupdf`, `PIL`.
- Used by: Command modules and legacy compatibility paths.

**Domain Storage Layer:**
- Purpose: Own durable data schemas and persistence APIs.
- Location: `paperforge/memory/`, `paperforge/annotation/`, `paperforge/worker/asset_index.py`
- Contains: SQLite schema management, DB connection helpers, index envelopes, import/upsert logic, query APIs.
- Depends on: `sqlite3`, `paperforge.config`, `paperforge.worker.asset_state`, adapter modules.
- Used by: `paperforge.commands.memory`, `paperforge.commands.annotation`, `paperforge.commands.search`, plugin annotation views.

**External Adapter Layer:**
- Purpose: Isolate external representations from internal PaperForge records.
- Location: `paperforge/adapters/`, `paperforge/pdf_resolver.py`, `paperforge/ocr_diagnostics.py`
- Contains: Better BibTeX row loading, Zotero path normalization, Obsidian frontmatter reads/writes, PDF path resolution, PaddleOCR diagnostics.
- Depends on: stdlib, `requests` where network/API diagnostics are needed.
- Used by: Worker and service modules.

**Setup / Deployment Layer:**
- Purpose: Prepare a vault, install skills/commands/plugin assets, and validate prerequisites.
- Location: `paperforge/setup/`, `paperforge/setup_wizard.py`, `scripts/`
- Contains: setup plan objects, checks, config writers, runtime installer, agent installer, version sync scripts.
- Depends on: filesystem, subprocess, `paperforge.services.skill_deploy`.
- Used by: `paperforge setup`, installation scripts, tests for setup flows.

## Data Flow

### Primary Request Path

1. Console script `paperforge` enters `main(argv)` (`paperforge/cli.py:474`).
2. Parser from `build_parser()` defines commands and options (`paperforge/cli.py:118`).
3. `main()` resolves the vault, loads config, attaches `args.vault_path`, `args.cfg`, and `args.paths` from `paperforge_paths()` (`paperforge/cli.py:474`, `paperforge/config.py:255`).
4. Dispatch imports a command module and calls `run(args)` such as sync, annotation, memory, search, or dashboard (`paperforge/cli.py:474`).
5. Command modules call service/worker/domain APIs, then return an integer exit code; JSON commands print `PFResult.to_json()` (`paperforge/core/result.py:19`).

### Sync and Index Flow

1. `paperforge sync` dispatches to `paperforge.commands.sync.run(args)` (`paperforge/commands/sync.py:13`).
2. The sync command delegates to `SyncService.run()` (`paperforge/services/sync_service.py:211`).
3. Selection sync loads Better BibTeX exports and writes/updates formal literature notes (`paperforge/worker/sync.py:219`).
4. Index rebuild uses `asset_index.build_index()` and writes `formal-library.json` through an envelope and atomic lock (`paperforge/worker/asset_index.py`).
5. Memory DB rebuild reads the canonical index and populates SQLite tables via `build_from_index(vault)` (`paperforge/memory/builder.py:130`).

### Annotation Import and Display Flow

1. `paperforge annotation import --paper KEY --zotero-db PATH --apply` dispatches through annotation command subcommands (`paperforge/commands/annotation.py:780`).
2. The command snapshots and opens Zotero read-only, probes the annotation schema, resolves paper/attachment, and locates `annotations.db` (`paperforge/commands/annotation.py`).
3. Import logic calls `import_zotero_annotations_for_paper()` (`paperforge/annotation/importer.py:262`).
4. The importer ensures `annotations.db` schema, enriches raw Zotero annotation rows, normalizes them, upserts rows, and scope-limits stale marking (`paperforge/annotation/schema.py:143`, `paperforge/annotation/importer.py:262`).
5. Plugin annotation UI loads annotations by calling CLI JSON commands and maps rows into load/list/overlay view models (`paperforge/plugin/src/testable.js:220`, `paperforge/plugin/src/testable.js:350`, `paperforge/plugin/src/testable.js:1516`).

### Plugin Runtime Flow

1. Obsidian loads `PaperForgePlugin` from `paperforge/plugin/main.js:6415`.
2. Plugin runtime resolves a Python executable and checks installed `paperforge` version (`paperforge/plugin/src/testable.js`).
3. Dashboard actions spawn `python -m paperforge` commands via `runSubprocess()` (`paperforge/plugin/src/testable.js`).
4. Annotation screens call `annotation status` and `annotation export`, parse `PFResult`, and render list/overlay states (`paperforge/plugin/src/testable.js:350`).

**State Management:**
- Runtime CLI state is per invocation and carried in `argparse.Namespace`.
- Path/config state is recomputed through `paperforge_paths(vault)` and `load_vault_config(vault)` in `paperforge/config.py`.
- Durable library state lives in vault files: formal notes under configured literature paths, OCR output under configured PaperForge system paths, and the canonical index at `indexes/formal-library.json`.
- Memory and annotations use SQLite DBs resolved through `paperforge_paths()`: `paperforge.db` and `annotations.db`.
- Plugin UI state is JavaScript object state, with testable pure functions in `paperforge/plugin/src/testable.js`.

## Key Abstractions

**PFResult / PFError:**
- Purpose: Stable JSON envelope for command results, plugin parsing, and CLI contract tests.
- Examples: `paperforge/core/result.py`, `paperforge/commands/annotation.py`, `paperforge/services/sync_service.py`
- Pattern: Dataclass response object with `ok`, `command`, `version`, `data`, `error`, `warnings`, and `next_actions`.

**Vault Path Inventory:**
- Purpose: Centralized resolved paths for vault resources, exports, OCR output, indexes, DBs, skills, and command files.
- Examples: `paperforge/config.py`, `paperforge/annotation/db.py`, `paperforge/memory/db.py`
- Pattern: Call `paperforge_paths(vault)` and read named keys such as `paths["index"]`, `paths["memory_db"]`, and `paths["annotations_db"]`.

**Command Module Contract:**
- Purpose: Keep command execution reusable outside the CLI parser.
- Examples: `paperforge/commands/sync.py`, `paperforge/commands/annotation.py`, `paperforge/commands/memory.py`
- Pattern: Each module exposes `run(args: argparse.Namespace) -> int`; subcommands may dispatch internally.

**Canonical Asset Index:**
- Purpose: Stable machine-readable inventory for papers, assets, lifecycle state, and downstream DB builds.
- Examples: `paperforge/worker/asset_index.py`, `paperforge/memory/builder.py`
- Pattern: Build entries from exports/formal notes, wrap in a versioned envelope, write atomically with a `filelock`.

**SQLite Domain Stores:**
- Purpose: Queryable local state for memory and annotations.
- Examples: `paperforge/memory/schema.py`, `paperforge/memory/db.py`, `paperforge/annotation/schema.py`, `paperforge/annotation/db.py`
- Pattern: Explicit schema ensure functions, `sqlite3.Row` row factories, WAL mode for writable annotation DB connections.

**Annotation Load State Machine:**
- Purpose: Stable UI state for missing paper, missing DB, CLI error, invalid JSON, empty, and ready annotation states.
- Examples: `paperforge/plugin/src/testable.js:220`, `paperforge/plugin/src/testable.js:350`
- Pattern: Pure JS functions create state objects and view models from CLI JSON results.

## Entry Points

**Console Script:**
- Location: `paperforge/cli.py:474`
- Triggers: Installed `paperforge` script from `pyproject.toml`, direct `paperforge.cli.main()` calls.
- Responsibilities: Parse args, resolve vault, load `.env` files, configure logging, dispatch commands.

**Python Module Entry:**
- Location: `paperforge/__main__.py`
- Triggers: `python -m paperforge`
- Responsibilities: Import and call `paperforge.cli.main`.

**Obsidian Plugin Entry:**
- Location: `paperforge/plugin/main.js:6415`
- Triggers: Obsidian plugin loading.
- Responsibilities: Dashboard rendering, command subprocess calls, annotation state and overlay UI.

**Setup Wizard:**
- Location: `paperforge/setup_wizard.py:867`
- Triggers: `paperforge setup` legacy/headless path.
- Responsibilities: Configure a vault, install agent assets, write config, run checks.

**Modular Setup Plan:**
- Location: `paperforge/setup/plan.py`
- Triggers: `paperforge setup --modular`.
- Responsibilities: Coordinate setup checker, config writer, vault initializer, runtime installer, and agent installer.

**Packaged Agent Skill Script:**
- Location: `paperforge/skills/paperforge/scripts/pf_deep.py:1556`
- Triggers: Deployed agent command workflows.
- Responsibilities: Deep-reading preparation and agent-facing paper workflows.

## Architectural Constraints

- **Threading:** CLI commands are synchronous. Cross-process protection is explicit where needed, such as `filelock` in `paperforge/worker/asset_index.py`. Plugin commands use subprocess execution from Node, not in-process Python calls.
- **Global state:** `paperforge/cli.py` has module-level worker function stubs (`run_status`, `run_selection_sync`, etc.) for test patching and compatibility. Avoid adding more mutable globals.
- **Circular imports:** Keep `paperforge/worker/_utils.py` as a leaf utility module. Its documented constraint is stdlib plus `paperforge.config`; do not import `paperforge.worker.*` or `paperforge.commands.*` from it.
- **Legacy boundary:** `paperforge/worker/sync.py` is marked as frozen for new business logic. Use `paperforge/services/sync_service.py`, adapters, or core modules for new behavior.
- **Secrets:** `.env` files are loaded at runtime by `paperforge/cli.py` and `paperforge/config.py`; do not document or embed secret values in codebase maps, tests, or fixtures.
- **Encoding:** The repository contains Chinese user-facing strings and some mojibake in comments/messages. Preserve existing text unless changing the specific behavior under test.

## Anti-Patterns

### Direct Path Reconstruction

**What happens:** New code manually builds `System/PaperForge/indexes` or `Resources/Literature` paths.
**Why it's wrong:** It bypasses `paperforge.json`, environment overrides, and future path migrations.
**Do this instead:** Use `paperforge_paths(vault)` from `paperforge/config.py` and pass named paths into lower layers.

### Adding Logic to Frozen Sync Worker

**What happens:** New sync behavior is added directly to `paperforge/worker/sync.py`.
**Why it's wrong:** The file is explicitly reserved for deletion, migration, and legacy wrappers, and it already mixes older responsibilities.
**Do this instead:** Add orchestration to `paperforge/services/sync_service.py`, parsing to `paperforge/adapters/`, and generic helpers to `paperforge/core/` or a domain module.

### Plugin Parsing Human Text

**What happens:** Plugin code infers command state from human-readable stdout.
**Why it's wrong:** Human text is not a stable contract and may include localized strings.
**Do this instead:** Add or extend `--json` command output using `PFResult` in `paperforge/core/result.py`, then parse JSON in `paperforge/plugin/src/testable.js`.

### Writing to Zotero

**What happens:** Annotation import or probe code opens the live Zotero DB in write mode.
**Why it's wrong:** The annotation importer contract is read-only against Zotero and writes only to PaperForge `annotations.db`.
**Do this instead:** Use snapshot/read-only helpers in `paperforge.annotation.zotero_probe` and write through `paperforge/annotation/importer.py`.

## Error Handling

**Strategy:** User-facing commands return integer exit codes and, for JSON-capable paths, print `PFResult` envelopes with stable `ErrorCode` values.

**Patterns:**
- Use `PFError` with `ErrorCode` for machine-readable failures (`paperforge/core/result.py`, `paperforge/core/errors.py`).
- Catch domain-specific exceptions at command boundaries, map them to `PFResult`, and keep low-level modules focused on raising meaningful exceptions (`paperforge/commands/annotation.py`).
- Log diagnostic details to `logging` stderr and reserve stdout for user-facing command output (`paperforge/logging_config.py`).
- For read-only status/list commands, return graceful empty states when DBs are missing (`paperforge/commands/annotation.py`).

## Cross-Cutting Concerns

**Logging:** Use `logging.getLogger(__name__)` in modules and configure via `paperforge/logging_config.py`. `paperforge/cli.py` calls `configure_logging(verbose=...)` before dispatch.
**Validation:** Use parser-level constraints in `paperforge/cli.py`, command-level required argument checks in modules such as `paperforge/commands/annotation.py`, and setup/doctor validators in `paperforge/setup/` and `paperforge/doctor/`.
**Authentication:** No central auth provider. External API credentials and local vault settings come from `.env`, `PAPERFORGE_*` variables, and `paperforge.json`; never hardcode keys.
**Persistence:** Use atomic writes for canonical indexes (`paperforge/worker/asset_index.py`), SQLite schema ensure functions for DB stores (`paperforge/memory/schema.py`, `paperforge/annotation/schema.py`), and helper writers from `paperforge/core/io.py` or `paperforge/worker/_utils.py`.
**Testing Surface:** Python tests are split by risk and boundary under `tests/unit/`, `tests/cli/`, `tests/integration/`, `tests/e2e/`, `tests/journey/`, `tests/chaos/`, and `tests/audit/`. Plugin tests live in `paperforge/plugin/tests/`.

---

*Architecture analysis: 2026-07-02*
