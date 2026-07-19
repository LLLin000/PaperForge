# PaperForge PDF Annotation Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only Zotero annotation import pipeline, persist normalized annotations in a dedicated PaperForge database, surface them through CLI JSON contracts, and render/edit them in Obsidian's native PDF viewer via overlay patching.

**Architecture:** The work is split into five sequential packages. Package A adds a dedicated annotation database and schema lifecycle. Package B implements read-only Zotero SQLite probing and import/update behavior. Package C exposes annotation commands through the CLI with stable JSON envelopes. Package D extends the current plain `paperforge/plugin/main.js` plugin with subprocess-backed annotation loading and viewer overlay patching. Package E prepares the future write-back lane without implementing Web API push yet.

**Tech Stack:** Python 3.10+, SQLite/WAL/FTS5, argparse CLI, Obsidian plugin CommonJS (`main.js`), Node child_process, Vitest, pytest

---

## File Map

### New Python Annotation Files

- `paperforge/annotation/__init__.py` — annotation package marker and narrow public exports
- `paperforge/annotation/db.py` — `annotations.db` path resolution and connection helpers
- `paperforge/annotation/schema.py` — annotation schema DDL, versioning, migrations, FTS triggers
- `paperforge/annotation/probe.py` — read-only Zotero SQLite access and normalization helpers
- `paperforge/annotation/importer.py` — import/upsert/reconciliation logic from Zotero rows to PaperForge rows
- `paperforge/annotation/service.py` — CRUD/search/export operations against `annotations.db`

### New / Modified CLI Files

- `paperforge/commands/annotation.py` — new command family implementation
- `paperforge/cli.py` — register `annotation` subcommands and flags
- `paperforge/core/result.py` — reuse existing result envelope only if a small helper addition is needed
- `paperforge/config.py` — only if Zotero data dir resolution needs a shared helper

### Plugin Files

- `paperforge/plugin/main.js` — add annotation subprocess bridge, viewer patch lifecycle, overlay UI wiring
- `paperforge/plugin/src/testable.js` — extract pure helper functions for argument building, annotation payload parsing, and coordinate helpers where possible
- `paperforge/plugin/styles.css` — overlay, popover, readonly-lock, and action styles
- `paperforge/plugin/package.json` — add `monkey-around` only if needed for patching helper ergonomics

### New / Modified Tests

- `fixtures/zotero/test_annotations.sqlite` — minimal Zotero SQLite fixture for importer/integration coverage
- `tests/unit/annotation/test_schema.py` — new schema creation/version tests
- `tests/unit/annotation/test_probe.py` — read-only SQLite normalization tests
- `tests/unit/annotation/test_importer.py` — import/update/delete reconciliation tests
- `tests/unit/annotation/test_service.py` — create/patch/delete/list/export behavior tests
- `tests/cli/test_annotation_commands.py` — CLI envelope and argument validation tests
- `tests/integration/test_annotation_import_workflow.py` — fixture-driven import and rebuild-survival tests
- `paperforge/plugin/tests/runtime.test.mjs` — extend with annotation runtime path/config helpers if needed
- `paperforge/plugin/tests/commands.test.mjs` — subprocess argument construction for annotation commands
- `paperforge/plugin/tests/errors.test.mjs` — plugin-side error handling for annotation subprocess and patch failures

### Existing Reference Files To Read During Execution

- `paperforge/memory/db.py` — existing SQLite connection patterns
- `paperforge/memory/schema.py` — versioning and trigger style reference
- `paperforge/pdf_resolver.py` — PDF path resolution rules
- `paperforge/plugin/main.js` — current plugin architecture and runtime helpers
- `paperforge/plugin/src/testable.js` — current pure helper extraction pattern
- `tests/unit/memory/test_schema.py` — schema testing style
- `tests/cli/test_json_contracts.py` — JSON contract assertions pattern

---

## Package A: Dedicated Annotation Database

### Task A1: Add Annotation DB Path and Connection Helpers

**Files:**
- Create: `paperforge/annotation/__init__.py`
- Create: `paperforge/annotation/db.py`
- Test: `tests/unit/annotation/test_schema.py`

- [ ] **Step 1: Write the failing tests for DB path and connection behavior**

Cover:

- `annotations.db` resolves under `System/PaperForge/indexes/`
- read/write connection enables WAL and foreign keys
- read-only connection uses SQLite URI `mode=ro`

- [ ] **Step 2: Run the new targeted tests to verify failure**

Run: `python -m pytest tests/unit/annotation/test_schema.py -v --tb=short`

Expected: FAIL because annotation DB helpers do not exist yet.

- [ ] **Step 3: Implement minimal path and connection helpers**

Follow the `paperforge/memory/db.py` style:

- `get_annotations_db_path(vault: Path) -> Path`
- `get_annotations_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection`

- [ ] **Step 4: Re-run the targeted tests**

Run: `python -m pytest tests/unit/annotation/test_schema.py -v --tb=short`

Expected: PASS for the new DB helper assertions.

- [ ] **Step 5: Commit**

```bash
git add paperforge/annotation/__init__.py paperforge/annotation/db.py tests/unit/annotation/test_schema.py
git commit -m "feat: add annotation db helpers"
```

### Task A2: Add Annotation Schema and Version Lifecycle

**Files:**
- Create: `paperforge/annotation/schema.py`
- Modify: `tests/unit/annotation/test_schema.py`

- [ ] **Step 1: Add failing schema lifecycle tests**

Test:

- schema bootstrap creates `meta`, `annotations`, `annotations_fts`, `sync_queue`
- schema version is stored as `1`
- `ensure_schema()` is idempotent

- [ ] **Step 2: Run the targeted schema tests**

Run: `python -m pytest tests/unit/annotation/test_schema.py -v --tb=short`

Expected: FAIL because tables and version logic do not exist.

- [ ] **Step 3: Implement the minimal schema module**

Include:

- `ANNOTATIONS_SCHEMA_VERSION = 1`
- DDL matching the columns, indexes, and FTS requirements defined in `docs/superpowers/specs/2026-05-20-pdf-annotation-layer-design.md` Section 8
- FTS triggers
- `ensure_schema(conn)`
- `get_schema_version(conn)`

- [ ] **Step 4: Re-run the schema tests**

Run: `python -m pytest tests/unit/annotation/test_schema.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/annotation/schema.py tests/unit/annotation/test_schema.py
git commit -m "feat: add annotation schema"
```

---

## Package B: Read-Only Zotero SQLite Probe and Import

### Task B1: Implement Read-Only Zotero Annotation Probe

**Files:**
- Create: `paperforge/annotation/probe.py`
- Create: `tests/unit/annotation/test_probe.py`
- Reference: `experiments/zotero_annotation_probe.py`

- [ ] **Step 1: Write failing tests for probe normalization**

Cover:

- annotation type integer → string mapping
- `position` JSON parsing
- tag aggregation
- read-only connection open path
- invalid schema error handling

- [ ] **Step 2: Run the probe tests to verify failure**

Run: `python -m pytest tests/unit/annotation/test_probe.py -v --tb=short`

Expected: FAIL because the probe module does not exist.

- [ ] **Step 3: Implement minimal probe behavior**

Add:

- `copy_db_to_temp()`
- `open_readonly()`
- `fetch_annotations()`
- `fetch_annotation_tags()`
- `normalize_zotero_annotation_row()`

Use parameterized SQL only.

Copy-to-temp must be the default behavior. A future `--no-copy` CLI flag is the explicit escape hatch.

- [ ] **Step 4: Re-run the probe tests**

Run: `python -m pytest tests/unit/annotation/test_probe.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/annotation/probe.py tests/unit/annotation/test_probe.py
git commit -m "feat: add zotero annotation probe"
```

### Task B1b: Add Fixture-Driven Zotero Import Coverage

**Files:**
- Create: `fixtures/zotero/test_annotations.sqlite`
- Create: `tests/integration/test_annotation_import_workflow.py`

- [ ] **Step 1: Write the failing fixture-driven import test**

Cover one end-to-end import from a real SQLite fixture containing at least:

- highlight with multi-rect position
- note annotation
- underline annotation
- tags
- non-ASCII text

- [ ] **Step 2: Run the focused integration test**

Run: `python -m pytest tests/integration/test_annotation_import_workflow.py -v --tb=short`

Expected: FAIL because the fixture and end-to-end import path are not wired yet.

- [ ] **Step 3: Build the minimal SQLite fixture and test harness**

Use the real Zotero schema subset needed by the importer so the test exercises actual SQL joins instead of mocks.

- [ ] **Step 4: Re-run the focused integration test**

Run: `python -m pytest tests/integration/test_annotation_import_workflow.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fixtures/zotero/test_annotations.sqlite tests/integration/test_annotation_import_workflow.py
git commit -m "test: add fixture-driven annotation import coverage"
```

### Task B2: Implement Import/Reconciliation Logic

**Files:**
- Create: `paperforge/annotation/importer.py`
- Create: `tests/unit/annotation/test_importer.py`
- Modify: `paperforge/annotation/schema.py` only if an index/helper is missing

- [ ] **Step 1: Write failing importer tests**

Cover:

- first import inserts new rows with `source='zotero_db'` and `sync_state='zotero_synced'`
- re-import with unchanged source is a no-op
- re-import with changed source updates payload and timestamps
- missing source annotation soft-deletes stale row if not locally modified
- locally modified stale row becomes `conflict` instead of blind delete

- [ ] **Step 2: Run the importer tests**

Run: `python -m pytest tests/unit/annotation/test_importer.py -v --tb=short`

Expected: FAIL because the importer does not exist.

- [ ] **Step 3: Implement minimal reconciliation logic**

Add:

- stable upsert by `(source, zotero_key)`
- source version + modified time tracking
- soft-delete rules
- conflict marking rules

- [ ] **Step 4: Re-run the importer tests**

Run: `python -m pytest tests/unit/annotation/test_importer.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/annotation/importer.py tests/unit/annotation/test_importer.py
git commit -m "feat: add annotation import reconciliation"
```

### Task B3: Implement Local Annotation CRUD/Search/Export Service

**Files:**
- Create: `paperforge/annotation/service.py`
- Create: `tests/unit/annotation/test_service.py`

- [ ] **Step 1: Write failing service tests**

Cover:

- create local annotation
- patch local comment/color
- soft delete local annotation
- list by paper/page
- export JSON
- export Markdown
- reject patching imported readonly rows unless an explicit future override exists

- [ ] **Step 2: Run the service tests**

Run: `python -m pytest tests/unit/annotation/test_service.py -v --tb=short`

Expected: FAIL because the service module does not exist.

- [ ] **Step 3: Implement the minimal service layer**

Expose:

- `create_annotation(...)`
- `patch_annotation(...)`
- `delete_annotation(...)`
- `list_annotations(...)`
- `export_annotations_json(...)`
- `export_annotations_markdown(...)`

- [ ] **Step 4: Re-run the service tests**

Run: `python -m pytest tests/unit/annotation/test_service.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/annotation/service.py tests/unit/annotation/test_service.py
git commit -m "feat: add annotation service"
```

---

## Package C: CLI Surface and JSON Contracts

### Task C1: Add `paperforge annotation` Parser Surface

**Files:**
- Modify: `paperforge/cli.py`
- Create: `paperforge/commands/annotation.py`
- Create: `tests/cli/test_annotation_commands.py`

- [ ] **Step 1: Write failing CLI parser and envelope tests**

Cover:

- subcommands: `import`, `list`, `create`, `patch`, `delete`, `export`, `status`
- required args and mutually exclusive flags
- `--json` envelope structure

- [ ] **Step 2: Run the CLI tests**

Run: `python -m pytest tests/cli/test_annotation_commands.py -v --tb=short`

Expected: FAIL because the parser and command module do not exist.

- [ ] **Step 3: Implement minimal parser + dispatch**

Add the new top-level `annotation` subparser in `paperforge/cli.py` and implement the command module that delegates to the new annotation service/importer.

Treat this CLI argument and JSON envelope contract as frozen before plugin Package D2 begins.

- [ ] **Step 4: Re-run the CLI tests**

Run: `python -m pytest tests/cli/test_annotation_commands.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/cli.py paperforge/commands/annotation.py tests/cli/test_annotation_commands.py
git commit -m "feat: add annotation cli"
```

### Task C2: Add Targeted End-to-End JSON Contract Tests

**Files:**
- Modify: `tests/cli/test_json_contracts.py`
- Modify: `tests/test_e2e_cli.py` or create a small focused annotation E2E test if cleaner

- [ ] **Step 1: Write failing JSON contract assertions for annotation commands**

Cover:

- `annotation status --json`
- `annotation list ... --json`
- `annotation create ... --json`
- error envelope when Zotero DB is missing

- [ ] **Step 2: Run the focused JSON contract tests**

Run: `python -m pytest tests/cli/test_json_contracts.py tests/test_e2e_cli.py -v --tb=short`

Expected: FAIL on missing contract coverage or incorrect envelope shape.

- [ ] **Step 3: Implement the minimal envelope fixes**

Keep the command outputs aligned with existing `PFResult`-style expectations where practical.

- [ ] **Step 4: Re-run the focused JSON contract tests**

Run: `python -m pytest tests/cli/test_json_contracts.py tests/test_e2e_cli.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/cli/test_json_contracts.py tests/test_e2e_cli.py paperforge/commands/annotation.py
git commit -m "test: cover annotation json contracts"
```

### Task C3: Prove Annotation Persistence Survives Memory Rebuild

**Files:**
- Modify: `tests/integration/test_annotation_import_workflow.py`

- [ ] **Step 1: Add the failing rebuild-survival test**

Cover:

- import annotations from the SQLite fixture
- run `paperforge memory build`
- run annotation list again
- assert imported annotations still exist unchanged in `annotations.db`

- [ ] **Step 2: Run the focused integration test file**

Run: `python -m pytest tests/integration/test_annotation_import_workflow.py -v --tb=short`

Expected: FAIL if any code path incorrectly couples `annotations.db` to memory rebuild lifecycle.

- [ ] **Step 3: Fix lifecycle boundaries if needed**

The expected fix should be minimal: ensure annotation DB code is fully separate from `paperforge.memory.*` rebuild paths.

- [ ] **Step 4: Re-run the focused integration test file**

Run: `python -m pytest tests/integration/test_annotation_import_workflow.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_annotation_import_workflow.py
git commit -m "test: verify annotation persistence across memory rebuild"
```

---

## Package D: Obsidian Plugin Overlay and Local Editing

### Task D1: Extend Plugin Testable Helpers for Annotation Runtime

**Files:**
- Modify: `paperforge/plugin/src/testable.js`
- Modify: `paperforge/plugin/tests/commands.test.mjs`
- Modify: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Write failing plugin helper tests**

Cover:

- annotation command argument builders
- parsing of CLI JSON envelopes
- readonly/local annotation classification
- safe fallback when annotation subprocess fails

- [ ] **Step 2: Run the focused plugin tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs tests/errors.test.mjs`

Expected: FAIL because the helper functions do not exist.

- [ ] **Step 3: Add pure helper functions to `src/testable.js`**

Add only pure logic here, for example:

- `buildAnnotationListArgs()`
- `buildAnnotationCreateArgs()`
- `parseAnnotationResult()`
- `isReadonlyAnnotation()`

- [ ] **Step 4: Re-run the plugin tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs tests/errors.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/testable.js paperforge/plugin/tests/commands.test.mjs paperforge/plugin/tests/errors.test.mjs
git commit -m "feat: add annotation plugin helpers"
```

### Task D2: Add Annotation Subprocess Bridge to the Plugin

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/tests/runtime.test.mjs`

- [ ] **Step 1: Write failing runtime tests for annotation bridge behavior**

Cover:

- plugin resolves Python executable and calls `paperforge annotation list`
- plugin handles JSON parse failures safely
- plugin degrades cleanly when CLI returns error

- [ ] **Step 2: Run the focused runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs tests/errors.test.mjs`

Expected: FAIL because the bridge does not exist.

- [ ] **Step 3: Implement minimal annotation bridge functions in `main.js`**

Add small functions rather than a big framework:

- `runAnnotationCommand(...)`
- `fetchAnnotationsForPaper(...)`
- `createLocalAnnotation(...)`
- `patchLocalAnnotation(...)`
- `deleteLocalAnnotation(...)`

Fetch all annotations for the active paper once on document open and cache them in memory grouped by `page_index`. Do not spawn subprocesses on every page render event.

- [ ] **Step 4: Re-run the focused runtime tests**

Run: `cd paperforge/plugin && npx vitest run tests/runtime.test.mjs tests/errors.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/tests/runtime.test.mjs paperforge/plugin/tests/errors.test.mjs
git commit -m "feat: add annotation plugin bridge"
```

### Task D3: Add Native PDF Viewer Patch Lifecycle

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/package.json` only if `monkey-around` is needed
- Modify: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Write failing tests for patch setup and soft-failure behavior**

Cover:

- plugin does not crash when PDF internals are unavailable
- patch init exits early outside desktop / unsupported state
- patch failure surfaces a controlled warning instead of breaking startup

- [ ] **Step 2: Run the focused patch-failure tests**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs`

Expected: FAIL because no annotation patch lifecycle exists.

- [ ] **Step 3: Implement minimal patch registration**

Inside `main.js`, add a narrow patch layer that:

- detects active `pdf` leaves
- resolves internal viewer prototypes/classes for the native PDF view and uses the PDF.js event bus events called out in the spec (`textlayerrendered`, `annotationlayerrendered`, `pagerendered`, `scalechanged`)
- installs patched `load` / `loadFile` / cleanup behavior
- bails out safely if internals are missing

Keep the patching additive and local. `paperforge/plugin/main.js` is already monolithic, so avoid introducing another large in-file subsystem unless the logic cannot be expressed as narrow helper functions.

- [ ] **Step 4: Re-run the patch-failure tests**

Run: `cd paperforge/plugin && npx vitest run tests/errors.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/package.json paperforge/plugin/tests/errors.test.mjs
git commit -m "feat: add pdf overlay patch lifecycle"
```

### Task D4: Render Overlays for Imported Annotations

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/src/testable.js`
- Modify: `paperforge/plugin/tests/commands.test.mjs`

- [ ] **Step 1: Write failing tests for coordinate conversion and render payload shaping**

Cover:

- page grouping by `page_index`
- rect normalization to overlay percentages
- readonly annotation style classification

- [ ] **Step 2: Run the focused plugin tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs tests/runtime.test.mjs`

Expected: FAIL because conversion/render helpers are incomplete.

- [ ] **Step 3: Implement minimal render helpers and overlay styles**

In `main.js`:

- build per-page overlay containers
- render highlight/underline/note rects
- attach hover/click listeners

In `styles.css`:

- add overlay, rect, popover, readonly-lock styles

Put pure math/string helpers in `src/testable.js` when possible.

- [ ] **Step 4: Re-run the focused plugin tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs tests/runtime.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css paperforge/plugin/src/testable.js paperforge/plugin/tests/commands.test.mjs paperforge/plugin/tests/runtime.test.mjs
git commit -m "feat: render annotation overlays"
```

### Task D5: Add Local Annotation Create/Edit/Delete UI Flow

**Files:**
- Modify: `paperforge/plugin/main.js`
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/tests/commands.test.mjs`
- Modify: `paperforge/plugin/tests/errors.test.mjs`

- [ ] **Step 1: Write failing tests for local annotation command flow**

Cover:

- selection payload becomes `annotation create` CLI args
- popover edit action becomes `annotation patch`
- delete action becomes `annotation delete`
- readonly rows never expose edit actions

- [ ] **Step 2: Run the focused plugin tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs tests/errors.test.mjs`

Expected: FAIL because local annotation UI flow is not wired.

- [ ] **Step 3: Implement the minimal local action flow**

Add to `main.js`:

- selection capture
- floating create affordance or context action
- popover with edit/delete buttons for local annotations only
- immediate overlay refresh after successful subprocess call

- [ ] **Step 4: Re-run the focused plugin tests**

Run: `cd paperforge/plugin && npx vitest run tests/commands.test.mjs tests/errors.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css paperforge/plugin/tests/commands.test.mjs paperforge/plugin/tests/errors.test.mjs
git commit -m "feat: add local annotation editing"
```

---

## Package E: Future Write-Back Readiness

### Task E1: Add Explicit Pending-Push and Queue Semantics Without API Push

**Files:**
- Modify: `paperforge/annotation/schema.py`
- Modify: `paperforge/annotation/service.py`
- Modify: `tests/unit/annotation/test_service.py`

- [ ] **Step 1: Write failing tests for queue-ready local edits**

Cover:

- local edits can mark rows as `pending_push`
- `sync_queue` receives create/update/delete payloads only when write-back mode is explicitly enabled later
- V1 default behavior remains local-only without silently pushing

- [ ] **Step 2: Run the focused service tests**

Run: `python -m pytest tests/unit/annotation/test_service.py -v --tb=short`

Expected: FAIL if the service cannot express future queue semantics.

- [ ] **Step 3: Implement the minimal readiness hooks**

Do not implement Web API logic yet. Only ensure the schema/service can represent future push state without a schema rewrite.

- [ ] **Step 4: Re-run the focused service tests**

Run: `python -m pytest tests/unit/annotation/test_service.py -v --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/annotation/schema.py paperforge/annotation/service.py tests/unit/annotation/test_service.py
git commit -m "feat: prepare annotation push states"
```

---

## Full Verification Slice

- [ ] **Step 1: Run annotation Python test slice**

Run:

```bash
python -m pytest tests/unit/annotation/ tests/integration/test_annotation_import_workflow.py tests/cli/test_annotation_commands.py tests/cli/test_json_contracts.py -v --tb=short
```

Expected: PASS.

- [ ] **Step 2: Run plugin test slice**

Run:

```bash
cd paperforge/plugin && npx vitest run tests/runtime.test.mjs tests/commands.test.mjs tests/errors.test.mjs
```

Expected: PASS.

- [ ] **Step 3: Run broader PaperForge regression slice**

Run:

```bash
python -m pytest tests/unit/memory/test_schema.py tests/test_config.py tests/test_e2e_cli.py -v --tb=short
```

Expected: PASS.

- [ ] **Step 4: Run the standard project regression commands from the repo guide**

Run:

```bash
python -m pytest tests/unit/ tests/cli/ -v --tb=short
```

Run:

```bash
cd paperforge/plugin && npx vitest run
```

Expected: PASS.

- [ ] **Step 5: Record completion checkpoint**

Expected state:

- `annotations.db` exists and is schema-managed
- Zotero SQLite import is read-only and fixture-tested
- `paperforge annotation ...` commands are live with JSON contracts
- plugin can fetch and render overlays in the native PDF view
- local annotation create/edit/delete is supported
- write-back path is designed in schema/service state, but not implemented yet
