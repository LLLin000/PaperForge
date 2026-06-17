# Research Summary: annotation v0.1

**Date:** 2026-06-17
**Milestone:** annotation v0.1 - PDF Annotation Backend & CLI Foundation

## Finding

The remote `feat/pdf-annotation-layer` branch proves the feature direction is viable, but it should not be merged wholesale. The safe path is to port the backend and CLI ideas onto the current `upstream/master` base while deferring the high-risk Obsidian PDF overlay.

## Stack Additions

No new runtime dependency is required for v0.1.

Use:

- Python `sqlite3`
- PaperForge config/path resolution
- PaperForge CLI command architecture
- pytest fixtures for Zotero SQLite

Defer:

- Obsidian PDF overlay
- `sql-wasm.wasm`
- Zotero Web API client
- write-back credential storage

## Required v0.1 Capabilities

- Independent `annotations.db`
- Zotero SQLite read-only probe
- Safe scoped import into PaperForge
- `paperforge annotation import/list/status/export --json`
- Regression tests for schema, probe, import, CLI, and hardcoded paths

## Key Architecture Decisions

1. Annotation data lives outside rebuildable memory databases.
2. Zotero DB is read-only and copied before reading by default.
3. Imported row identity must include source and library scope, not just a bare Zotero key.
4. Stale deletion must be scoped to the current import scope.
5. Plugin overlay is a later milestone, not part of v0.1.

## Watch Out For

- The old importer can delete unrelated annotations during paper-scoped import.
- Bare Zotero keys can collide across libraries.
- Hardcoded vault paths will break user-configured vaults.
- Obsidian PDF overlay work will expand scope quickly and should remain out of v0.1.

## Recommended Roadmap Shape

- Phase 61: Annotation database foundation
- Phase 62: Zotero probe and safe import
- Phase 63: CLI JSON contracts
- Phase 64: Verification and acceptance gate
