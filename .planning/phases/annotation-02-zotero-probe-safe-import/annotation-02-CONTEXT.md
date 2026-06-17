# Annotation Phase 2 Context: Zotero Probe and Safe Import

## Phase Goal

Import PDF annotations from Zotero into PaperForge safely, using Zotero only as a read-only source and storing normalized annotation records in PaperForge-owned `annotations.db`.

In plain terms: this phase builds the safe "import channel" from Zotero highlights/comments into PaperForge. It should know how to read Zotero's annotation data, copy it into PaperForge's own database, and avoid damaging either Zotero data or unrelated PaperForge annotation rows.

## Requirements Covered

- ZOT-01: Import from a read-only copied `zotero.sqlite` snapshot, not by writing to or mutating the live Zotero database.
- ZOT-02: Paper-scoped import only reconciles annotations for the selected paper and never deletes or stales unrelated paper annotations.
- ZOT-03: Imported annotation identity includes source and library scope rather than relying on a bare Zotero key.
- ZOT-04: Zotero schema probing reports actionable errors for missing database files, unknown table layouts, missing columns, and unreadable/locked databases.
- ZOT-05: Zotero-sourced rows are marked read-only in PaperForge.
- SAFE-01: Zotero database paths are resolved through configuration or explicit inputs, not hardcoded user folders.
- SAFE-02: Zotero reads use temp-copy mode by default and clean up the copied snapshot.
- SAFE-04: No code path writes back to Zotero SQLite or directly mutates Zotero's live database.

## Discussion Decisions

- D-01: Phase 2 focuses on backend import/probe behavior only. CLI JSON commands, Obsidian overlay, annotation editor UI, and evidence/card integration remain out of scope for this phase.
- D-02: Paper-scoped import is the primary user-facing behavior for this phase. Lower-level code may be shaped so full-library import is possible later, but this phase must prove single-paper import first.
- D-03: Stale reconciliation must be scope-limited. When importing one paper, PaperForge may update, insert, or mark stale only Zotero-sourced rows inside that paper scope.
- D-04: Zotero access defaults to temp-copy mode. PaperForge copies `zotero.sqlite` to a temporary location, opens the copy read-only, imports data, and removes the temporary file afterward.
- D-05: Zotero database discovery should be configuration-first. The importer can accept an explicit `zotero.sqlite` path and can later be wired to config/CLI, but it must not hardcode a Windows, macOS, or Linux Zotero folder.
- D-06: Imported identity must include source boundaries: `source`, `source_library_id`, `source_parent_key`, `source_attachment_key`, and `source_annotation_key`. A Zotero annotation key alone is not enough.
- D-07: Zotero-sourced annotations are read-only in PaperForge. Later phases may create local editable copies, but imported source rows should preserve Zotero as the authority.
- D-08: Schema probing should fail with structured domain errors that later CLI code can turn into stable JSON and Chinese user-facing messages.
- D-09: Normalization should preserve research-useful fields: selected text, user comment, highlight color, page label/index, sort index, tags, position JSON, Zotero modified time, attachment key, parent item key, and library scope.

## Plain-Language Glossary

- **Probe:** First inspect Zotero's database shape and available annotation tables before importing. This is like checking the package label before unpacking.
- **Temp-copy mode:** Copy Zotero's database to a temporary file and read that copy. This protects the live Zotero database from locks, corruption, and accidental writes.
- **Paper-scoped import:** Import only annotations belonging to one paper/PDF attachment. This avoids one paper's sync accidentally touching another paper.
- **Stale reconciliation:** If an annotation existed in PaperForge before but is no longer present in the current Zotero import for the same paper, mark it as stale/soft-deleted instead of deleting data blindly.
- **Library scope:** Zotero can have personal libraries and group libraries. The same item key can appear in different libraries, so PaperForge must store which library a record came from.
- **Read-only source row:** A row imported from Zotero that PaperForge displays and exports but does not edit as if it were native PaperForge data.

## Existing Patterns To Follow

- Phase 1 created `paperforge.annotation.db` and `paperforge.annotation.schema`; Phase 2 should build on those modules rather than touching memory/index database code.
- `annotations.db` already has generic provenance fields such as `source` and `source_library_id`; keep those names generic instead of baking Zotero-specific names into the schema.
- `paperforge_paths(vault)` is the preferred pattern for configured PaperForge paths. Phase 2 should preserve config-aware path resolution and avoid absolute local defaults.
- Tests should stay targeted because the upstream baseline has unrelated failures. Prefer focused annotation importer/probe tests over broad full-suite runs.

## Scope Boundary

In scope:

- Zotero SQLite snapshot/open helpers.
- Zotero schema probe functions.
- Zotero annotation row normalization.
- Import/reconciliation service that writes normalized records to `annotations.db`.
- Paper-scoped stale handling.
- Read-only source marking for Zotero rows.
- Unit tests using minimal SQLite fixtures.

Out of scope:

- `paperforge annotation ...` CLI commands.
- Obsidian plugin UI.
- PDF overlay rendering.
- Editing annotations inside PaperForge.
- Writing annotation edits back into Zotero.
- Concept-card/deep-reading evidence integration.
- Full-library import as a polished user workflow.

## Expected User Value

After this phase, PaperForge should be able to safely ingest Zotero PDF highlights and comments into its own annotation store. A researcher should be able to trust that importing annotations for one paper will not damage Zotero and will not accidentally modify annotation state for other papers.

## Planning Notes For Next Phase

- Plan 1 should likely establish Zotero snapshot and probe modules with structured errors.
- Plan 2 should normalize Zotero annotation rows into PaperForge annotation records.
- Plan 3 should implement scoped import reconciliation into `annotations.db`.
- Plan 4 should add fixture-based tests for copy mode, schema errors, identity fields, read-only marking, and paper-scope isolation.
