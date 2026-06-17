# Phase 61 Context: Annotation Storage Foundation

## Phase Goal

Create the PaperForge-owned annotation database layer without coupling it to rebuildable memory/index databases.

## Requirements Covered

- DATA-01: User has an independent `annotations.db` created under the configured PaperForge index/system location, separate from rebuildable memory databases.
- DATA-02: Annotation schema stores source, library scope, parent paper key, attachment key, selected text, comment, color, page label/index, sort index, tags, position JSON, timestamps, and soft-delete state.
- DATA-03: Annotation schema has explicit schema-version metadata and migration entry points so future annotation versions can evolve without touching `paperforge.db`.
- DATA-04: Memory/index rebuild code does not drop, recreate, or mutate `annotations.db`.

## Decisions

- D-01: `annotations.db` is independent from `paperforge.db`; it is user evidence data, not rebuildable memory.
- D-02: Annotation path resolution must use `paperforge_paths(vault)` and colocate with `paperforge.db` under the configured `PaperForge/indexes` directory.
- D-03: Phase 61 does not implement Zotero probing, import reconciliation, CLI commands, plugin overlay, local editing, or Zotero write-back.
- D-04: The schema must include enough provenance for Phase 62 to safely identify Zotero-sourced rows by source and library scope.
- D-05: Rebuild isolation must be tested directly: creating/rebuilding memory must not delete or alter `annotations.db`.

## Existing Patterns To Follow

- `paperforge.memory.db.get_memory_db_path()` resolves DB paths through `paperforge_paths(vault)`.
- `paperforge.memory.db.get_connection()` creates parent directories, sets row factory, enables WAL and foreign keys for write connections.
- `paperforge.memory.schema.ensure_schema()` creates tables/indexes/triggers and commits.
- `paperforge.memory.schema.get_schema_version()` reads `meta.schema_version`, returning `0` when missing.
- `paperforge.memory.builder.build_from_index()` only touches `paperforge.db`; this is the function to regression-test for annotation DB isolation.

## Scope Boundary

In scope:

- `paperforge/annotation/__init__.py`
- `paperforge/annotation/db.py`
- `paperforge/annotation/schema.py`
- unit tests for path/connection/schema behavior
- a regression test that memory rebuild does not mutate `annotations.db`

Out of scope:

- `paperforge annotation ...` CLI
- Zotero SQLite table probing
- import/reconciliation logic
- annotation service CRUD/export
- Obsidian PDF overlay
- concept-card or deep-reading evidence integration

## Known Baseline Risk

The clean upstream worktree has unrelated baseline test failures around `ld_deep_script` vs `pf_deep_script` and missing `snapshot` fixture. Phase 61 verification should run targeted annotation/memory tests and record unrelated baseline failures separately.
