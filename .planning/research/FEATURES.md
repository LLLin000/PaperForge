# Research: annotation v0.1 Features

**Date:** 2026-06-17
**Milestone:** annotation v0.1 - PDF Annotation Backend & CLI Foundation

## Table Stakes

v0.1 should make PaperForge able to answer:

1. Which Zotero PDF annotations exist for a paper?
2. Can those annotations be imported safely into PaperForge?
3. Can a user or plugin list/export them through stable CLI JSON?
4. Can this happen without corrupting Zotero or existing PaperForge data?

## In Scope

### Annotation Storage

- Create and migrate an independent `annotations.db`.
- Store imported Zotero annotations with enough metadata to preserve provenance.
- Support soft deletion for source annotations that disappear from the same import scope.
- Include schema metadata so future migrations are explicit.

### Zotero Read-Only Import

- Read `itemAnnotations` from Zotero SQLite.
- Join annotations to attachment and parent paper keys.
- Preserve selected text, comments, color, page label, sort index, tags, source modified time, and position JSON.
- Copy Zotero DB before reading unless the user opts into direct read.

### CLI MVP

- `paperforge annotation import --json`
- `paperforge annotation list --json`
- `paperforge annotation status --json`
- `paperforge annotation export --json`

### Safety Behavior

- A paper-scoped import must not delete or modify annotations for other papers.
- Zotero-sourced annotations are read-only in v0.1.
- The annotation database must not be touched by memory rebuilds.
- Errors must be actionable, especially missing Zotero DB, unknown schema, locked DB, and missing PaperForge config.

## Out of Scope

- Obsidian PDF overlay rendering
- Creating/editing/deleting annotations from the PDF UI
- Writing annotations back to Zotero
- Zotero Web API sync
- Conflict resolution UI
- EPUB or web annotations
- Full concept-card or deep-reading evidence integration

## Differentiator for PaperForge

The feature is not just "show highlights." It is a traceability layer: imported PDF highlights become stable local evidence objects that future deep-reading, note, and concept-card workflows can cite.
