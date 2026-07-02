# Codebase Structure

**Analysis Date:** 2026-07-02

## Directory Layout

```text
PaperForge-feat-pdf-annotation-layer/
├── paperforge/              # Python package plus bundled Obsidian plugin and agent skill payload
│   ├── adapters/            # External format adapters: BBT, Zotero paths, collections, frontmatter
│   ├── annotation/          # Annotation SQLite schema/import/normalization/Zotero probe layer
│   ├── commands/            # CLI/agent command modules exposing run(args) functions
│   ├── command_files/       # Packaged agent command markdown files
│   ├── core/                # Shared result, error, state, date, and IO primitives
│   ├── doctor/              # Setup/index/frontmatter validation helpers
│   ├── memory/              # SQLite memory DB, FTS, vector/runtime, reading/project log APIs
│   ├── plugin/              # Obsidian plugin JavaScript, CSS, package metadata, plugin tests
│   ├── schema/              # Field registry and schema package resources
│   ├── services/            # Higher-level service orchestration and deployment helpers
│   ├── setup/               # Modular setup components
│   ├── skills/              # Bundled PaperForge agent skill and workflows
│   └── worker/              # Filesystem pipeline workers and legacy compatibility modules
├── tests/                   # Python test suite split by unit/CLI/integration/e2e/journey/chaos/audit
├── fixtures/                # Deterministic Zotero/OCR/PDF/snapshot fixtures and vault builder
├── docs/                    # Maintainer and user documentation
├── command/                 # Top-level command docs for agent command distribution
├── scripts/                 # Install, validation, version, and consistency helper scripts
├── .planning/               # GSD planning artifacts and generated codebase maps
├── .github/                 # GitHub workflow/configuration files
├── pyproject.toml           # Python packaging, dependencies, pytest and ruff configuration
├── requirements.txt         # Runtime dependency pins/minimums
├── paperforge.json          # Default vault configuration sample
└── manifest.json            # Top-level manifest metadata
```

## Directory Purposes

**`paperforge/`:**
- Purpose: Main installable Python package and bundled plugin/agent assets.
- Contains: CLI entry points, command modules, worker logic, storage schemas, setup flows, plugin sources, packaged skills.
- Key files: `paperforge/cli.py`, `paperforge/config.py`, `paperforge/__main__.py`, `paperforge/__init__.py`.

**`paperforge/commands/`:**
- Purpose: One module per command surface, each exposing `run(args: argparse.Namespace) -> int`.
- Contains: Command adapters for `sync`, `ocr`, `status`, `repair`, `annotation`, `memory`, `embed`, `retrieve`, `search`, logs, dashboard, and runtime health.
- Key files: `paperforge/commands/__init__.py`, `paperforge/commands/sync.py`, `paperforge/commands/annotation.py`, `paperforge/commands/memory.py`.

**`paperforge/worker/`:**
- Purpose: Filesystem pipeline workflows and legacy worker compatibility.
- Contains: Sync, OCR, status, repair, asset index, asset state, base views, deep reading, vector DB support, retry/progress/util helpers.
- Key files: `paperforge/worker/sync.py`, `paperforge/worker/asset_index.py`, `paperforge/worker/ocr.py`, `paperforge/worker/status.py`, `paperforge/worker/_utils.py`.

**`paperforge/services/`:**
- Purpose: Higher-level orchestration modules for behavior migrating out of legacy workers.
- Contains: Sync lifecycle facade and skill deployment helpers.
- Key files: `paperforge/services/sync_service.py`, `paperforge/services/skill_deploy.py`.

**`paperforge/adapters/`:**
- Purpose: Normalize external domain formats at the edges.
- Contains: Better BibTeX loading, Zotero path conversion, Obsidian frontmatter helpers, collection handling.
- Key files: `paperforge/adapters/bbt.py`, `paperforge/adapters/zotero_paths.py`, `paperforge/adapters/obsidian_frontmatter.py`, `paperforge/adapters/collections.py`.

**`paperforge/annotation/`:**
- Purpose: PDF annotation import and local annotation database domain.
- Contains: `annotations.db` path/connection helpers, schema migration, Zotero read/normalize/import logic, domain exceptions.
- Key files: `paperforge/annotation/db.py`, `paperforge/annotation/schema.py`, `paperforge/annotation/importer.py`, `paperforge/annotation/zotero_probe.py`, `paperforge/annotation/zotero_normalize.py`.

**`paperforge/memory/`:**
- Purpose: PaperForge memory database and retrieval layer.
- Contains: `paperforge.db` schema, build/refresh/query APIs, FTS, permanent reading/project logs, vector runtime state.
- Key files: `paperforge/memory/builder.py`, `paperforge/memory/schema.py`, `paperforge/memory/db.py`, `paperforge/memory/query.py`, `paperforge/memory/permanent.py`.

**`paperforge/core/`:**
- Purpose: Shared low-level contracts and helpers safe to import across layers.
- Contains: Result envelopes, error codes, JSON IO, date utilities, state primitives.
- Key files: `paperforge/core/result.py`, `paperforge/core/errors.py`, `paperforge/core/io.py`, `paperforge/core/state.py`.

**`paperforge/plugin/`:**
- Purpose: Bundled Obsidian plugin.
- Contains: Runtime `main.js`, testable extracted JS functions, CSS, plugin manifest/version files, Node package config, Vitest tests.
- Key files: `paperforge/plugin/main.js`, `paperforge/plugin/src/testable.js`, `paperforge/plugin/manifest.json`, `paperforge/plugin/tests/annotation-overlay.test.mjs`.

**`paperforge/setup/`:**
- Purpose: Modular setup components used by `paperforge setup --modular`.
- Contains: Setup result model, checker, plan, config writer, vault initializer, runtime installer, agent installer.
- Key files: `paperforge/setup/plan.py`, `paperforge/setup/checker.py`, `paperforge/setup/config_writer.py`, `paperforge/setup/agent.py`.

**`paperforge/skills/`:**
- Purpose: Packaged PaperForge skill content deployed into supported agent platforms.
- Contains: `SKILL.md`, workflow docs, reference docs, scripts such as `pf_deep.py`.
- Key files: `paperforge/skills/paperforge/SKILL.md`, `paperforge/skills/paperforge/scripts/pf_deep.py`, `paperforge/skills/paperforge/workflows/deep-reading.md`.

**`tests/`:**
- Purpose: Python verification suite.
- Contains: General tests at root plus focused suites in `tests/unit/`, `tests/cli/`, `tests/integration/`, `tests/e2e/`, `tests/journey/`, `tests/chaos/`, `tests/audit/`.
- Key files: `tests/conftest.py`, `tests/cli/test_annotation_json_contracts.py`, `tests/unit/annotation/`, `tests/integration/test_memory_workflow.py`.

**`fixtures/`:**
- Purpose: Stable test inputs and generated sample vault data.
- Contains: Zotero JSON exports, OCR API response fixtures, PDFs, snapshots, methodology docs, vault builder.
- Key files: `fixtures/vault_builder.py`, `fixtures/zotero/*.json`, `fixtures/ocr/*.json`, `fixtures/pdf/*.pdf`, `fixtures/MANIFEST.json`.

**`docs/`:**
- Purpose: Human-facing documentation and maintainer notes.
- Contains: Architecture docs, command docs, migration notes, UX contract, images, superpowers plans/specs.
- Key files: `docs/ARCHITECTURE.md`, `docs/COMMANDS.md`, `docs/ux-contract.md`.

## Key File Locations

**Entry Points:**
- `paperforge/cli.py`: Main CLI parser and dispatcher.
- `paperforge/__main__.py`: `python -m paperforge` entry.
- `paperforge/setup_wizard.py`: Legacy/headless setup entry.
- `paperforge/plugin/main.js`: Obsidian plugin entry class.
- `paperforge/skills/paperforge/scripts/pf_deep.py`: Bundled agent deep-reading script entry.

**Configuration:**
- `pyproject.toml`: Packaging, dependencies, console script, pytest settings, ruff settings.
- `paperforge/config.py`: Runtime config resolution and path inventory.
- `paperforge.json`: Repository sample/default PaperForge vault config.
- `paperforge/schema/field_registry.yaml`: Field registry resource.
- `paperforge/plugin/package.json`: Plugin JS test/build dependencies and scripts.
- `paperforge/plugin/vitest.config.ts`: Plugin test config.

**Core Logic:**
- `paperforge/core/result.py`: `PFResult`/`PFError` JSON envelope.
- `paperforge/core/errors.py`: Stable error code enum.
- `paperforge/services/sync_service.py`: Sync orchestration facade.
- `paperforge/worker/asset_index.py`: Canonical asset index creation and atomic writes.
- `paperforge/worker/sync.py`: Legacy selection sync and migration wrappers.
- `paperforge/worker/ocr.py`: OCR workflow.
- `paperforge/memory/builder.py`: Builds `paperforge.db` from canonical index.
- `paperforge/annotation/importer.py`: Imports Zotero annotations into `annotations.db`.
- `paperforge/plugin/src/testable.js`: Pure plugin logic for runtime, annotations, dashboard view models.

**Testing:**
- `tests/conftest.py`: Shared Python fixtures.
- `tests/cli/`: CLI contract tests and snapshots.
- `tests/unit/`: Unit tests organized by package area.
- `tests/integration/`: Multi-component tests such as memory workflow.
- `tests/e2e/`: End-to-end vault/workflow tests.
- `tests/journey/`: User journey tests.
- `tests/chaos/`: Abnormal input/filesystem/network tests.
- `tests/audit/`: Consistency audit tests.
- `paperforge/plugin/tests/`: Vitest plugin tests.

## Naming Conventions

**Files:**
- Python modules use snake_case: `paperforge/commands/paper_status.py`, `paperforge/memory/state_snapshot.py`.
- Private support modules use a leading underscore: `paperforge/worker/_utils.py`, `paperforge/worker/_retry.py`, `paperforge/memory/_columns.py`.
- Tests use `test_*.py` for Python and `*.test.mjs` for plugin tests.
- Agent command docs use command names: `paperforge/command_files/pf-sync.md`, `command/pf-deep.md`.
- Packaged markdown workflows use kebab-case: `paperforge/skills/paperforge/workflows/deep-reading.md`.

**Directories:**
- Domain packages live directly under `paperforge/`: `annotation`, `memory`, `worker`, `services`, `adapters`, `setup`.
- Python test subtrees mirror package or boundary names: `tests/unit/annotation`, `tests/unit/services`, `tests/cli`.
- Plugin code is self-contained under `paperforge/plugin/`; testable pure JS lives in `paperforge/plugin/src/`.
- Fixtures are grouped by source/type: `fixtures/zotero`, `fixtures/ocr`, `fixtures/pdf`, `fixtures/snapshots`.

## Where to Add New Code

**New CLI Command:**
- Primary code: `paperforge/commands/<command_name>.py`
- Parser and dispatch: `paperforge/cli.py`
- Registry entry if dynamically used: `paperforge/commands/__init__.py`
- Tests: `tests/unit/commands/test_<command_name>.py` for command behavior and `tests/cli/test_<command_name>*.py` for subprocess/JSON contracts.

**New Sync Behavior:**
- Primary code: `paperforge/services/sync_service.py` or a new focused service in `paperforge/services/`.
- External parsing/normalization: `paperforge/adapters/`.
- Shared low-level helper: `paperforge/core/`.
- Avoid: adding new business logic to `paperforge/worker/sync.py`.

**New Worker Workflow:**
- Implementation: `paperforge/worker/<workflow>.py` when the behavior is filesystem pipeline work.
- Command adapter: `paperforge/commands/<workflow>.py`.
- Tests: focused unit tests under `tests/unit/` plus CLI/e2e tests when exposed to users.

**New Annotation Feature:**
- Storage/schema: `paperforge/annotation/schema.py` and `paperforge/annotation/db.py`.
- Import/normalization: `paperforge/annotation/importer.py` or `paperforge/annotation/zotero_normalize.py`.
- CLI surface: `paperforge/commands/annotation.py`.
- Plugin view model: `paperforge/plugin/src/testable.js`; runtime UI wiring in `paperforge/plugin/main.js`.
- Tests: `tests/unit/annotation/`, `tests/cli/test_annotation_*.py`, and `paperforge/plugin/tests/annotation-*.test.mjs`.

**New Memory/Search Feature:**
- Schema and DB access: `paperforge/memory/schema.py`, `paperforge/memory/db.py`.
- Build/refresh logic: `paperforge/memory/builder.py` or `paperforge/memory/refresh.py`.
- Query logic: `paperforge/memory/query.py`, `paperforge/memory/fts.py`, `paperforge/memory/vector_db.py`.
- Command surface: `paperforge/commands/memory.py`, `paperforge/commands/search.py`, `paperforge/commands/retrieve.py`.

**New Plugin UI Logic:**
- Pure/testable logic: `paperforge/plugin/src/testable.js`.
- Obsidian runtime integration: `paperforge/plugin/main.js`.
- Styles: `paperforge/plugin/styles.css`.
- Tests: `paperforge/plugin/tests/*.test.mjs`.
- Use CLI `--json` outputs rather than parsing human-readable command text.

**New Setup Capability:**
- Modular step: `paperforge/setup/<capability>.py`.
- Plan orchestration: `paperforge/setup/plan.py`.
- Legacy/headless compatibility only when necessary: `paperforge/setup_wizard.py`.
- Tests: `tests/unit/` or existing setup-related tests such as `tests/test_setup_wizard.py`.

**Utilities:**
- Cross-layer stable primitives: `paperforge/core/`.
- Worker-only helpers: `paperforge/worker/_utils.py`, preserving its leaf-module import constraint.
- External representation adapters: `paperforge/adapters/`.
- Do not put reusable behavior in command modules unless it is command-specific I/O.

## Special Directories

**`.planning/`:**
- Purpose: GSD planning, phase artifacts, research, and generated codebase maps.
- Generated: Yes
- Committed: Project-specific; treat as planning state and only edit assigned documents.

**`paperforge/plugin/node_modules/`:**
- Purpose: Installed Node dependencies for plugin development/test.
- Generated: Yes
- Committed: Present in working tree; do not inspect or edit for architecture mapping unless plugin dependency work specifically requires it.

**`paperforge/skills/paperforge/references/`:**
- Purpose: Bundled domain reference material for the PaperForge agent skill.
- Generated: No
- Committed: Yes

**`fixtures/`:**
- Purpose: Deterministic test data for offline/CI tests.
- Generated: Mixed; source fixtures are committed, some files are generated by helper scripts.
- Committed: Yes

**`tests/sandbox/`:**
- Purpose: Sandbox test vault and inspection helpers excluded from normal pytest collection by `pyproject.toml`.
- Generated: Yes
- Committed: Mixed; avoid depending on it for core unit tests.

---

*Structure analysis: 2026-07-02*
